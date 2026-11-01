"""API views for the Learning Center."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.learning.models import (
    LessonProgress,
    Tutorial,
    TutorialCategory,
    TutorialLesson,
    TutorialProgress,
)
from apps.learning.permissions import IsAdminOrReadOnly
from apps.learning.serializers import (
    QuizSubmissionRequestSerializer,
    TutorialCategorySerializer,
    TutorialDetailSerializer,
    TutorialLessonDetailSerializer,
    TutorialLessonListSerializer,
    TutorialListSerializer,
    TutorialProgressSerializer,
    TutorialQuizPublicSerializer,
)
from apps.learning.services.progress import (
    grade_quiz,
    record_lesson_access,
    update_lesson_completion,
)


class CategoryListView(generics.ListAPIView):
    """List all active tutorial categories."""

    serializer_class = TutorialCategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return TutorialCategory.objects.filter(is_active=True).order_by("display_order", "name")


class TutorialListView(generics.ListAPIView):
    """List published educational tutorials with filtering and search."""

    serializer_class = TutorialListSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("category", str, description="Filter by category slug"),
            OpenApiParameter("difficulty", str, description="Filter by difficulty: beginner, intermediate, advanced"),
            OpenApiParameter("is_featured", bool, description="Filter only featured tutorials"),
            OpenApiParameter("search", str, description="Search term in title or description"),
        ]
    )
    def get_queryset(self):
        qs = Tutorial.objects.select_related("category").prefetch_related("lessons")

        # Non-staff only see published tutorials
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_published=True, category__is_active=True)

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)

        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty=difficulty.lower())

        is_featured = self.request.query_params.get("is_featured")
        if is_featured is not None:
            val = is_featured.lower() in ("true", "1")
            qs = qs.filter(is_featured=val)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(short_description__icontains=search)
                | Q(content__icontains=search)
            )

        return qs.order_by("display_order", "-created_at")


class TutorialDetailView(generics.RetrieveAPIView):
    """Retrieve full details for a tutorial including its curriculum lessons."""

    serializer_class = TutorialDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Tutorial.objects.select_related("category").prefetch_related("lessons")
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_published=True, category__is_active=True)
        return qs


class TutorialLessonListView(generics.ListAPIView):
    """List all published lessons for a specific tutorial."""

    serializer_class = TutorialLessonListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        tutorial = get_object_or_404(
            Tutorial,
            slug=slug,
            is_published=True,
        )
        return tutorial.lessons.filter(is_published=True).order_by("display_order", "id")


class LessonDetailView(generics.RetrieveAPIView):
    """Retrieve a single lesson by its slug."""

    serializer_class = TutorialLessonDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    lookup_url_kwarg = "lesson_slug"

    def get_queryset(self):
        qs = TutorialLesson.objects.select_related("tutorial")
        if not (self.request.user and self.request.user.is_staff):
            qs = qs.filter(is_published=True, tutorial__is_published=True)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Automatically track last accessed lesson if user is authenticated
        if request.user.is_authenticated:
            record_lesson_access(request.user, instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserProgressListView(generics.ListAPIView):
    """List all tutorial progress entries for the currently authenticated user."""

    serializer_class = TutorialProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            TutorialProgress.objects.filter(user=self.request.user)
            .select_related("tutorial", "tutorial__category", "last_accessed_lesson")
            .order_by("-last_accessed_at")
        )


class TutorialProgressDetailView(APIView):
    """Retrieve a user's progress for a specific tutorial, including list of completed lessons."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug: str):
        tutorial = get_object_or_404(Tutorial, slug=slug, is_published=True)
        progress = TutorialProgress.objects.filter(user=request.user, tutorial=tutorial).first()

        completed_lesson_slugs = list(
            LessonProgress.objects.filter(
                user=request.user,
                lesson__tutorial=tutorial,
                is_completed=True,
            ).values_list("lesson__slug", flat=True)
        )

        total_lessons = tutorial.lessons.filter(is_published=True).count()
        progress_percentage = (
            float(progress.progress_percentage)
            if progress
            else (
                round((len(completed_lesson_slugs) / total_lessons * 100), 2)
                if total_lessons > 0
                else 0.0
            )
        )

        return Response({
            "tutorial_slug": tutorial.slug,
            "tutorial_title": tutorial.title,
            "total_lessons": total_lessons,
            "completed_lessons_count": len(completed_lesson_slugs),
            "completed_lesson_slugs": completed_lesson_slugs,
            "progress_percentage": progress_percentage,
            "is_completed": progress.is_completed if progress else (progress_percentage >= 100.0),
            "last_accessed_lesson_slug": (
                progress.last_accessed_lesson.slug
                if progress and progress.last_accessed_lesson
                else None
            ),
        })


class LessonCompleteView(APIView):
    """Mark a lesson as completed or toggle completion status for the authenticated user."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lesson_slug: str):
        lesson = get_object_or_404(
            TutorialLesson.objects.select_related("tutorial"),
            slug=lesson_slug,
            is_published=True,
        )

        # Allow explicitly passing is_completed: true/false in request body (defaults to True)
        is_completed = request.data.get("is_completed", True)
        if isinstance(is_completed, str):
            is_completed = is_completed.lower() in ("true", "1")

        lesson_progress, tutorial_progress = update_lesson_completion(
            user=request.user,
            lesson=lesson,
            is_completed=bool(is_completed),
        )

        return Response({
            "message": "Lesson status updated successfully",
            "lesson_slug": lesson.slug,
            "is_completed": lesson_progress.is_completed,
            "completed_at": lesson_progress.completed_at,
            "tutorial_slug": lesson.tutorial.slug,
            "tutorial_progress_percentage": float(tutorial_progress.progress_percentage),
            "tutorial_is_completed": tutorial_progress.is_completed,
        })


class LessonQuizView(APIView):
    """Retrieve quiz questions and options for a lesson.

    Omits correct answers and explanations.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, lesson_slug: str):
        lesson = get_object_or_404(
            TutorialLesson,
            slug=lesson_slug,
            is_published=True,
        )
        quizzes = lesson.quizzes.prefetch_related("options").all().order_by("display_order", "id")
        serializer = TutorialQuizPublicSerializer(quizzes, many=True)
        return Response({
            "lesson_slug": lesson.slug,
            "lesson_title": lesson.title,
            "quizzes": serializer.data,
        })


class LessonQuizSubmitView(APIView):
    """Grade submitted quiz answers for a lesson.

    Returns the graded score, correct answers, and explanations.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=QuizSubmissionRequestSerializer)
    def post(self, request, lesson_slug: str):
        lesson = get_object_or_404(
            TutorialLesson.objects.select_related("tutorial"),
            slug=lesson_slug,
            is_published=True,
        )

        serializer = QuizSubmissionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answers = serializer.validated_data.get("answers", [])
        result = grade_quiz(lesson, answers)

        # If user is authenticated and passed, optionally mark completed if auto_complete requested
        auto_complete = request.data.get("auto_complete", False)
        if request.user.is_authenticated and result["passed"] and auto_complete:
            update_lesson_completion(request.user, lesson, is_completed=True)
            result["lesson_marked_complete"] = True

        return Response(result, status=status.HTTP_200_OK)
