"""Serializers for the Learning Center API."""

from rest_framework import serializers

from apps.learning.models import (
    LessonProgress,
    Tutorial,
    TutorialCategory,
    TutorialLesson,
    TutorialProgress,
    TutorialQuiz,
    TutorialQuizOption,
)


class TutorialCategorySerializer(serializers.ModelSerializer):
    """Category serializer with count of active tutorials."""

    tutorials_count = serializers.SerializerMethodField()

    class Meta:
        model = TutorialCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "display_order",
            "is_active",
            "tutorials_count",
            "created_at",
            "updated_at",
        ]

    def get_tutorials_count(self, obj) -> int:
        return obj.tutorials.filter(is_published=True).count()


class QuizOptionPublicSerializer(serializers.ModelSerializer):
    """Public quiz option serializer.

    CRITICAL SECURITY REQUIREMENT:
    Never expose is_correct or explanation before answer submission.
    """

    class Meta:
        model = TutorialQuizOption
        fields = [
            "id",
            "option_text",
            "display_order",
        ]


class TutorialQuizPublicSerializer(serializers.ModelSerializer):
    """Public quiz question serializer without answers/explanations."""

    options = QuizOptionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = TutorialQuiz
        fields = [
            "id",
            "question",
            "display_order",
            "options",
        ]


class TutorialLessonListSerializer(serializers.ModelSerializer):
    """Lesson outline item within a tutorial."""

    is_completed = serializers.SerializerMethodField()
    has_quiz = serializers.SerializerMethodField()

    class Meta:
        model = TutorialLesson
        fields = [
            "id",
            "title",
            "slug",
            "display_order",
            "estimated_minutes",
            "is_published",
            "has_quiz",
            "is_completed",
        ]

    def get_has_quiz(self, obj) -> bool:
        return obj.quizzes.exists()

    def get_is_completed(self, obj) -> bool:
        user = self.context.get("request").user if self.context.get("request") else None
        if not user or not user.is_authenticated:
            return False
        completed_lessons = self.context.get("completed_lesson_ids")
        if completed_lessons is not None:
            return obj.id in completed_lessons
        return LessonProgress.objects.filter(user=user, lesson=obj, is_completed=True).exists()


class TutorialLessonDetailSerializer(serializers.ModelSerializer):
    """Detailed view for an individual lesson including prev/next links and completion status."""

    tutorial_title = serializers.CharField(source="tutorial.title", read_only=True)
    tutorial_slug = serializers.CharField(source="tutorial.slug", read_only=True)
    is_completed = serializers.SerializerMethodField()
    has_quiz = serializers.SerializerMethodField()
    quizzes_count = serializers.SerializerMethodField()
    previous_lesson = serializers.SerializerMethodField()
    next_lesson = serializers.SerializerMethodField()

    class Meta:
        model = TutorialLesson
        fields = [
            "id",
            "tutorial_title",
            "tutorial_slug",
            "title",
            "slug",
            "content",
            "cover_image",
            "display_order",
            "estimated_minutes",
            "is_published",
            "has_quiz",
            "quizzes_count",
            "is_completed",
            "previous_lesson",
            "next_lesson",
            "created_at",
            "updated_at",
        ]

    def get_has_quiz(self, obj) -> bool:
        return obj.quizzes.exists()

    def get_quizzes_count(self, obj) -> int:
        return obj.quizzes.count()

    def get_is_completed(self, obj) -> bool:
        user = self.context.get("request").user if self.context.get("request") else None
        if not user or not user.is_authenticated:
            return False
        return LessonProgress.objects.filter(user=user, lesson=obj, is_completed=True).exists()

    def get_previous_lesson(self, obj):
        prev = (
            TutorialLesson.objects.filter(
                tutorial=obj.tutorial,
                is_published=True,
                display_order__lt=obj.display_order,
            )
            .order_by("-display_order")
            .first()
        )
        if prev:
            return {"title": prev.title, "slug": prev.slug}
        return None

    def get_next_lesson(self, obj):
        next_l = (
            TutorialLesson.objects.filter(
                tutorial=obj.tutorial,
                is_published=True,
                display_order__gt=obj.display_order,
            )
            .order_by("display_order")
            .first()
        )
        if next_l:
            return {"title": next_l.title, "slug": next_l.slug}
        return None


class TutorialListSerializer(serializers.ModelSerializer):
    """List serializer for tutorials with category details and progress."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_icon = serializers.CharField(source="category.icon", read_only=True)
    total_lessons = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = Tutorial
        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "cover_image",
            "difficulty",
            "estimated_minutes",
            "display_order",
            "is_featured",
            "is_published",
            "category_name",
            "category_slug",
            "category_icon",
            "total_lessons",
            "user_progress",
            "created_at",
            "updated_at",
        ]

    def get_total_lessons(self, obj) -> int:
        return obj.lessons.filter(is_published=True).count()

    def get_user_progress(self, obj):
        user = self.context.get("request").user if self.context.get("request") else None
        if not user or not user.is_authenticated:
            return None
        progress = TutorialProgress.objects.filter(user=user, tutorial=obj).first()
        if not progress:
            return {
                "progress_percentage": 0.0,
                "is_completed": False,
                "last_accessed_lesson_slug": None,
            }
        return {
            "progress_percentage": float(progress.progress_percentage),
            "is_completed": progress.is_completed,
            "last_accessed_lesson_slug": (
                progress.last_accessed_lesson.slug if progress.last_accessed_lesson else None
            ),
        }


class TutorialDetailSerializer(TutorialListSerializer):
    """Detailed tutorial view including its ordered curriculum of lessons."""

    lessons = serializers.SerializerMethodField()

    class Meta(TutorialListSerializer.Meta):
        fields = TutorialListSerializer.Meta.fields + [
            "content",
            "lessons",
        ]

    def get_lessons(self, obj):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        completed_ids = set()
        if user:
            completed_ids = set(
                LessonProgress.objects.filter(
                    user=user,
                    lesson__tutorial=obj,
                    is_completed=True,
                ).values_list("lesson_id", flat=True)
            )

        context = {
            "request": request,
            "completed_lesson_ids": completed_ids,
        }

        lessons = obj.lessons.filter(is_published=True).order_by("display_order", "id")
        return TutorialLessonListSerializer(lessons, many=True, context=context).data


class TutorialProgressSerializer(serializers.ModelSerializer):
    """Progress record serializer for authenticated users."""

    tutorial_title = serializers.CharField(source="tutorial.title", read_only=True)
    tutorial_slug = serializers.CharField(source="tutorial.slug", read_only=True)
    tutorial_difficulty = serializers.CharField(source="tutorial.difficulty", read_only=True)
    category_name = serializers.CharField(source="tutorial.category.name", read_only=True)
    last_accessed_lesson_title = serializers.CharField(
        source="last_accessed_lesson.title", read_only=True, default=None
    )
    last_accessed_lesson_slug = serializers.CharField(
        source="last_accessed_lesson.slug", read_only=True, default=None
    )

    class Meta:
        model = TutorialProgress
        fields = [
            "id",
            "tutorial_title",
            "tutorial_slug",
            "tutorial_difficulty",
            "category_name",
            "progress_percentage",
            "is_completed",
            "last_accessed_lesson_title",
            "last_accessed_lesson_slug",
            "started_at",
            "last_accessed_at",
            "completed_at",
        ]


class QuizSubmissionItemSerializer(serializers.Serializer):
    """A single question submission."""

    quiz_id = serializers.IntegerField(required=True)
    selected_option_id = serializers.IntegerField(required=True)


class QuizSubmissionRequestSerializer(serializers.Serializer):
    """Payload submitted when grading a quiz."""

    answers = QuizSubmissionItemSerializer(many=True, required=True)
