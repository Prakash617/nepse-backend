"""Models for the NEPSE Learning Center application.

Supports modular stock-market educational tutorials, lessons, quizzes,
and user-specific progress tracking.
"""

from decimal import Decimal
from django.conf import settings
from django.db import models


class TutorialCategory(models.Model):
    """Categorisation for tutorials (e.g., Technical Analysis, Fundamental Analysis)."""

    name = models.CharField(max_length=150, unique=True, help_text="Category name")
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    description = models.TextField(blank=True, default="", help_text="Category summary")
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Icon identifier (e.g., Lucide icon name: CandlestickChart, BarChart3, LineChart)",
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Tutorial Category"
        verbose_name_plural = "Tutorial Categories"

    def __str__(self) -> str:
        return self.name


class Tutorial(models.Model):
    """A multi-lesson educational course or guide."""

    DIFFICULTY_BEGINNER = "beginner"
    DIFFICULTY_INTERMEDIATE = "intermediate"
    DIFFICULTY_ADVANCED = "advanced"

    DIFFICULTY_CHOICES = [
        (DIFFICULTY_BEGINNER, "Beginner"),
        (DIFFICULTY_INTERMEDIATE, "Intermediate"),
        (DIFFICULTY_ADVANCED, "Advanced"),
    ]

    category = models.ForeignKey(
        TutorialCategory,
        on_delete=models.PROTECT,
        related_name="tutorials",
        help_text="Category this tutorial belongs to",
    )
    title = models.CharField(max_length=255, help_text="Title of the tutorial")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    short_description = models.TextField(
        blank=True,
        default="",
        help_text="Brief summary shown on listing cards",
    )
    content = models.TextField(
        blank=True,
        default="",
        help_text="Detailed tutorial introduction / overview in Markdown format",
    )
    cover_image = models.FileField(
        upload_to="learning/tutorials/",
        blank=True,
        null=True,
        help_text="Cover banner image or illustration",
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_BEGINNER,
        db_index=True,
    )
    estimated_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Estimated completion time in minutes",
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "created_at"]
        verbose_name = "Tutorial"
        verbose_name_plural = "Tutorials"

    def __str__(self) -> str:
        return self.title

    @property
    def published_lessons_count(self) -> int:
        return self.lessons.filter(is_published=True).count()


class TutorialLesson(models.Model):
    """An individual lesson within a tutorial."""

    tutorial = models.ForeignKey(
        Tutorial,
        on_delete=models.CASCADE,
        related_name="lessons",
        help_text="Parent tutorial",
    )
    title = models.CharField(max_length=255, help_text="Lesson title")
    slug = models.SlugField(max_length=255, db_index=True)
    content = models.TextField(
        help_text="Full educational content in Markdown, with support for embedded SVG illustrations or charts",
    )
    cover_image = models.FileField(
        upload_to="learning/lessons/",
        blank=True,
        null=True,
        help_text="Optional lesson header or illustration",
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    estimated_minutes = models.PositiveIntegerField(
        default=5,
        help_text="Estimated reading time in minutes",
    )
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "id"]
        unique_together = [("tutorial", "slug")]
        verbose_name = "Tutorial Lesson"
        verbose_name_plural = "Tutorial Lessons"

    def __str__(self) -> str:
        return f"{self.tutorial.title} - {self.display_order}. {self.title}"


class TutorialProgress(models.Model):
    """Tracks a user's overall progress across a specific tutorial."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutorial_progresses",
        db_index=True,
    )
    tutorial = models.ForeignKey(
        Tutorial,
        on_delete=models.CASCADE,
        related_name="user_progresses",
        db_index=True,
    )
    last_accessed_lesson = models.ForeignKey(
        TutorialLesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentage of published lessons completed (0.00 to 100.00)",
    )
    is_completed = models.BooleanField(default=False, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "tutorial")]
        ordering = ["-last_accessed_at"]
        verbose_name = "Tutorial Progress"
        verbose_name_plural = "Tutorial Progresses"

    def __str__(self) -> str:
        return f"{self.user} - {self.tutorial.title} ({self.progress_percentage}%)"


class LessonProgress(models.Model):
    """Tracks whether an individual user has completed a specific lesson."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progresses",
        db_index=True,
    )
    lesson = models.ForeignKey(
        TutorialLesson,
        on_delete=models.CASCADE,
        related_name="user_progresses",
        db_index=True,
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "lesson")]
        verbose_name = "Lesson Progress"
        verbose_name_plural = "Lesson Progresses"

    def __str__(self) -> str:
        status = "Completed" if self.is_completed else "Incomplete"
        return f"{self.user} - {self.lesson.title} ({status})"


class TutorialQuiz(models.Model):
    """Interactive quiz attached to a lesson to test comprehension."""

    lesson = models.ForeignKey(
        TutorialLesson,
        on_delete=models.CASCADE,
        related_name="quizzes",
        help_text="Lesson this quiz question reinforces",
    )
    question = models.TextField(help_text="Question text")
    explanation = models.TextField(
        blank=True,
        default="",
        help_text="Detailed explanation displayed after submission",
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Lesson Quiz Question"
        verbose_name_plural = "Lesson Quiz Questions"

    def __str__(self) -> str:
        return f"Q{self.display_order}: {self.question[:60]}"


class TutorialQuizOption(models.Model):
    """Multiple choice option for a TutorialQuiz."""

    quiz = models.ForeignKey(
        TutorialQuiz,
        on_delete=models.CASCADE,
        related_name="options",
        help_text="Parent question",
    )
    option_text = models.CharField(max_length=500, help_text="Option label/answer text")
    is_correct = models.BooleanField(
        default=False,
        help_text="Whether this is the correct answer. NEVER exposed in public read APIs.",
    )
    explanation = models.TextField(
        blank=True,
        default="",
        help_text="Optional per-option explanation",
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Quiz Option"
        verbose_name_plural = "Quiz Options"

    def __str__(self) -> str:
        marker = "✓" if self.is_correct else "✗"
        return f"{marker} {self.option_text[:40]}"
