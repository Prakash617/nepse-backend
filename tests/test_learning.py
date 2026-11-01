"""Tests for Learning Center models, APIs, progress tracking, and quiz scoring."""

from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.learning.models import (
    LessonProgress,
    Tutorial,
    TutorialCategory,
    TutorialLesson,
    TutorialProgress,
    TutorialQuiz,
    TutorialQuizOption,
)
from apps.learning.services.progress import update_lesson_completion

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(username="learner1", password="securepass123")


@pytest.fixture
def other_user():
    return User.objects.create_user(username="learner2", password="securepass123")


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="staffadmin", password="securepass123", is_staff=True
    )


@pytest.fixture
def category():
    return TutorialCategory.objects.create(
        name="Technical Analysis",
        slug="technical-analysis",
        description="Learn chart reading and price action",
        icon="TrendingUp",
        display_order=1,
        is_active=True,
    )


@pytest.fixture
def inactive_category():
    return TutorialCategory.objects.create(
        name="Archived Course",
        slug="archived-course",
        display_order=99,
        is_active=False,
    )


@pytest.fixture
def sample_tutorial(category):
    tut = Tutorial.objects.create(
        category=category,
        title="Understanding Candlestick Charts",
        slug="understanding-candlestick-charts",
        short_description="Master candlestick fundamentals on NEPSE.",
        content="Welcome to the candlestick guide.",
        difficulty=Tutorial.DIFFICULTY_BEGINNER,
        estimated_minutes=45,
        display_order=1,
        is_featured=True,
        is_published=True,
    )
    # Create 3 lessons
    l1 = TutorialLesson.objects.create(
        tutorial=tut,
        title="Introduction to Candlestick Charts",
        slug="introduction-to-candlestick-charts",
        content="# Intro\nWelcome.",
        display_order=1,
        estimated_minutes=5,
        is_published=True,
    )
    l2 = TutorialLesson.objects.create(
        tutorial=tut,
        title="Understanding OHLC",
        slug="understanding-ohlc",
        content="# OHLC\nOpen, High, Low, Close.",
        display_order=2,
        estimated_minutes=5,
        is_published=True,
    )
    l3 = TutorialLesson.objects.create(
        tutorial=tut,
        title="Unpublished Draft Lesson",
        slug="draft-lesson",
        content="# Draft",
        display_order=3,
        estimated_minutes=5,
        is_published=False,
    )
    l4 = TutorialLesson.objects.create(
        tutorial=tut,
        title="Hammer Pattern",
        slug="hammer-pattern",
        content="# Hammer Pattern\nReversal structure.",
        display_order=4,
        estimated_minutes=5,
        is_published=True,
    )

    # Attach a quiz to lesson 2
    q1 = TutorialQuiz.objects.create(
        lesson=l2,
        question="What does OHLC stand for?",
        explanation="OHLC stands for Open, High, Low, Close.",
        display_order=1,
    )
    TutorialQuizOption.objects.create(
        quiz=q1,
        option_text="Open, High, Low, Close",
        is_correct=True,
        explanation="Correct definition.",
        display_order=1,
    )
    TutorialQuizOption.objects.create(
        quiz=q1,
        option_text="Order, Hold, Leverage, Cancel",
        is_correct=False,
        explanation="Incorrect.",
        display_order=2,
    )

    return tut


@pytest.mark.django_db
class TestTutorialCategoryAPI:
    def test_list_active_categories(self, api_client, category, inactive_category):
        response = api_client.get("/api/v1/learning/categories/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        slugs = [c["slug"] for c in data]
        assert "technical-analysis" in slugs
        assert "archived-course" not in slugs


@pytest.mark.django_db
class TestTutorialListAndDetailAPI:
    def test_list_published_tutorials(self, api_client, sample_tutorial, category):
        # Create an unpublished tutorial
        Tutorial.objects.create(
            category=category,
            title="Draft Hidden Course",
            slug="draft-hidden-course",
            is_published=False,
        )

        response = api_client.get("/api/v1/learning/tutorials/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        results = data.get("results", data)
        slugs = [t["slug"] for t in results]
        assert "understanding-candlestick-charts" in slugs
        assert "draft-hidden-course" not in slugs

    def test_filter_by_difficulty_and_category(self, api_client, sample_tutorial):
        # Filter matching
        resp1 = api_client.get(
            "/api/v1/learning/tutorials/?category=technical-analysis&difficulty=beginner"
        )
        assert resp1.status_code == status.HTTP_200_OK
        results = resp1.json().get("results", resp1.json())
        assert len(results) == 1

        # Filter non-matching
        resp2 = api_client.get("/api/v1/learning/tutorials/?difficulty=advanced")
        assert resp2.status_code == status.HTTP_200_OK
        results2 = resp2.json().get("results", resp2.json())
        assert len(results2) == 0

    def test_tutorial_detail_with_lessons(self, api_client, sample_tutorial):
        response = api_client.get(f"/api/v1/learning/tutorials/{sample_tutorial.slug}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == sample_tutorial.slug
        assert "lessons" in data
        # Should only list published lessons (3 out of 4)
        lesson_slugs = [l["slug"] for l in data["lessons"]]
        assert "introduction-to-candlestick-charts" in lesson_slugs
        assert "understanding-ohlc" in lesson_slugs
        assert "hammer-pattern" in lesson_slugs
        assert "draft-lesson" not in lesson_slugs


@pytest.mark.django_db
class TestLessonDetailAndNavigationAPI:
    def test_lesson_detail_navigation(self, api_client, sample_tutorial):
        response = api_client.get("/api/v1/learning/lessons/understanding-ohlc/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Understanding OHLC"
        assert data["previous_lesson"] is not None
        assert data["previous_lesson"]["slug"] == "introduction-to-candlestick-charts"
        assert data["next_lesson"] is not None
        assert data["next_lesson"]["slug"] == "hammer-pattern"

    def test_unpublished_lesson_404_for_anonymous(self, api_client, sample_tutorial):
        response = api_client.get("/api/v1/learning/lessons/draft-lesson/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestProgressTrackingAPI:
    def test_progress_endpoints_require_authentication(self, api_client):
        res1 = api_client.get("/api/v1/learning/progress/")
        assert res1.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        res2 = api_client.post("/api/v1/learning/lessons/understanding-ohlc/complete/")
        assert res2.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_mark_lesson_completed_and_progress_calculation(
        self, api_client, user, sample_tutorial
    ):
        api_client.force_authenticate(user=user)

        # Mark 1 of 3 published lessons complete
        resp = api_client.post(
            "/api/v1/learning/lessons/introduction-to-candlestick-charts/complete/",
            {"is_completed": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["is_completed"] is True
        # 1/3 = 33.33%
        assert data["tutorial_progress_percentage"] == 33.33
        assert data["tutorial_is_completed"] is False

        # Mark 2nd lesson complete
        resp2 = api_client.post(
            "/api/v1/learning/lessons/understanding-ohlc/complete/",
            {"is_completed": True},
            format="json",
        )
        assert resp2.status_code == status.HTTP_200_OK
        data2 = resp2.json()
        # 2/3 = 66.67%
        assert data2["tutorial_progress_percentage"] == 66.67
        assert data2["tutorial_is_completed"] is False

        # Mark 3rd published lesson complete -> 100%
        resp3 = api_client.post(
            "/api/v1/learning/lessons/hammer-pattern/complete/",
            {"is_completed": True},
            format="json",
        )
        assert resp3.status_code == status.HTTP_200_OK
        data3 = resp3.json()
        assert data3["tutorial_progress_percentage"] == 100.0
        assert data3["tutorial_is_completed"] is True

        # Check tutorial progress endpoint
        tut_prog_resp = api_client.get(
            f"/api/v1/learning/tutorials/{sample_tutorial.slug}/progress/"
        )
        assert tut_prog_resp.status_code == status.HTTP_200_OK
        tut_prog_data = tut_prog_resp.json()
        assert tut_prog_data["progress_percentage"] == 100.0
        assert tut_prog_data["is_completed"] is True
        assert len(tut_prog_data["completed_lesson_slugs"]) == 3

    def test_duplicate_progress_prevention(self, user, sample_tutorial):
        lesson = sample_tutorial.lessons.first()
        # Mark complete twice
        update_lesson_completion(user, lesson, is_completed=True)
        update_lesson_completion(user, lesson, is_completed=True)

        assert LessonProgress.objects.filter(user=user, lesson=lesson).count() == 1
        assert TutorialProgress.objects.filter(user=user, tutorial=sample_tutorial).count() == 1


@pytest.mark.django_db
class TestQuizSecurityAndGrading:
    def test_quiz_options_never_expose_correct_answers_to_public(
        self, api_client, sample_tutorial
    ):
        """CRITICAL SECURITY TEST: Ensure answers/explanations are concealed before submit."""
        response = api_client.get("/api/v1/learning/lessons/understanding-ohlc/quiz/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        quizzes = data["quizzes"]
        assert len(quizzes) > 0

        for quiz in quizzes:
            for option in quiz["options"]:
                # Neither is_correct nor explanation should be present in option payload
                assert "is_correct" not in option
                assert "explanation" not in option

    def test_submit_quiz_scoring(self, api_client, sample_tutorial):
        lesson = sample_tutorial.lessons.get(slug="understanding-ohlc")
        quiz = lesson.quizzes.first()
        correct_opt = quiz.options.filter(is_correct=True).first()
        incorrect_opt = quiz.options.filter(is_correct=False).first()

        # Submit correct answer
        resp_correct = api_client.post(
            f"/api/v1/learning/lessons/{lesson.slug}/quiz/submit/",
            {"answers": [{"quiz_id": quiz.id, "selected_option_id": correct_opt.id}]},
            format="json",
        )
        assert resp_correct.status_code == status.HTTP_200_OK
        res_data = resp_correct.json()
        assert res_data["total_questions"] == 1
        assert res_data["correct_answers"] == 1
        assert res_data["score_percentage"] == 100.0
        assert res_data["passed"] is True
        assert res_data["results"][0]["is_correct"] is True

        # Submit incorrect answer
        resp_wrong = api_client.post(
            f"/api/v1/learning/lessons/{lesson.slug}/quiz/submit/",
            {"answers": [{"quiz_id": quiz.id, "selected_option_id": incorrect_opt.id}]},
            format="json",
        )
        assert resp_wrong.status_code == status.HTTP_200_OK
        res_wrong_data = resp_wrong.json()
        assert res_wrong_data["correct_answers"] == 0
        assert res_wrong_data["score_percentage"] == 0.0
        assert res_wrong_data["passed"] is False
        assert res_wrong_data["results"][0]["is_correct"] is False
        # Explanations and correct options are now revealed after grading
        assert res_wrong_data["results"][0]["correct_option_id"] == correct_opt.id
