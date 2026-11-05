"""Service layer for learning progress tracking and quiz scoring."""

from decimal import Decimal
from typing import Any

from django.utils import timezone

from apps.learning.models import (
    LessonProgress,
    Tutorial,
    TutorialLesson,
    TutorialProgress,
)


def get_or_create_tutorial_progress(user, tutorial: Tutorial) -> TutorialProgress:
    """Retrieve or initialize tutorial progress for a user."""
    progress, _ = TutorialProgress.objects.get_or_create(
        user=user,
        tutorial=tutorial,
    )
    return progress


def record_lesson_access(user, lesson: TutorialLesson) -> TutorialProgress | None:
    """Records that the user accessed this lesson."""
    if not user.is_authenticated:
        return None

    progress, _ = TutorialProgress.objects.get_or_create(
        user=user,
        tutorial=lesson.tutorial,
    )
    progress.last_accessed_lesson = lesson
    progress.last_accessed_at = timezone.now()
    progress.save(update_fields=["last_accessed_lesson", "last_accessed_at"])
    return progress


def update_lesson_completion(
    user, lesson: TutorialLesson, is_completed: bool = True
) -> tuple[LessonProgress, TutorialProgress]:
    """Marks a lesson completed or incomplete, then recalculates tutorial progress."""
    now = timezone.now()

    lesson_progress, _ = LessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson,
    )
    lesson_progress.is_completed = is_completed
    lesson_progress.completed_at = now if is_completed else None
    lesson_progress.save()

    tutorial = lesson.tutorial
    total_published = tutorial.lessons.filter(is_published=True).count()

    completed_published_count = LessonProgress.objects.filter(
        user=user,
        lesson__tutorial=tutorial,
        lesson__is_published=True,
        is_completed=True,
    ).count()

    if total_published > 0:
        pct = round(
            (Decimal(completed_published_count) / Decimal(total_published)) * Decimal("100.00"),
            2,
        )
    else:
        pct = Decimal("0.00")

    pct = min(pct, Decimal("100.00"))

    tut_progress, _ = TutorialProgress.objects.get_or_create(
        user=user,
        tutorial=tutorial,
    )
    tut_progress.last_accessed_lesson = lesson
    tut_progress.progress_percentage = pct
    if pct >= Decimal("100.00"):
        tut_progress.is_completed = True
        if not tut_progress.completed_at:
            tut_progress.completed_at = now
    else:
        tut_progress.is_completed = False
        tut_progress.completed_at = None

    tut_progress.last_accessed_at = now
    tut_progress.save()

    return lesson_progress, tut_progress


def grade_quiz(lesson: TutorialLesson, submissions: list[dict[str, Any]]) -> dict[str, Any]:
    """Grades submitted quiz answers for a lesson.

    Submissions format:
    [
        {"quiz_id": <int>, "selected_option_id": <int>}
    ]
    """
    quizzes = lesson.quizzes.prefetch_related("options").all()

    results = []
    correct_count = 0

    submission_dict = {
        item.get("quiz_id"): item.get("selected_option_id") for item in submissions
    }

    for quiz in quizzes:
        selected_option_id = submission_dict.get(quiz.id)
        selected_option = None
        correct_option = None

        for opt in quiz.options.all():
            if opt.is_correct:
                correct_option = opt
            if opt.id == selected_option_id:
                selected_option = opt

        is_correct = bool(selected_option and selected_option.is_correct)
        if is_correct:
            correct_count += 1

        results.append({
            "quiz_id": quiz.id,
            "question": quiz.question,
            "selected_option_id": selected_option_id,
            "selected_option_text": selected_option.option_text if selected_option else None,
            "correct_option_id": correct_option.id if correct_option else None,
            "correct_option_text": correct_option.option_text if correct_option else "",
            "is_correct": is_correct,
            "explanation": quiz.explanation or (correct_option.explanation if correct_option else ""),
        })

    total = len(quizzes)
    score_pct = round((correct_count / total * 100), 1) if total > 0 else 0.0
    passed = score_pct >= 70.0

    return {
        "lesson_id": lesson.id,
        "lesson_slug": lesson.slug,
        "total_questions": total,
        "correct_answers": correct_count,
        "score_percentage": score_pct,
        "passed": passed,
        "results": results,
    }
