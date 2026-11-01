"""Django Admin configuration for the Learning Center."""

from django.contrib import admin
from django.utils.html import format_html
from apps.learning.models import (
    LessonProgress,
    Tutorial,
    TutorialCategory,
    TutorialLesson,
    TutorialProgress,
    TutorialQuiz,
    TutorialQuizOption,
)


class TutorialLessonInline(admin.StackedInline):
    model = TutorialLesson
    extra = 1
    fields = [
        "title",
        "slug",
        "display_order",
        "estimated_minutes",
        "is_published",
        "content",
        "cover_image",
    ]
    prepopulated_fields = {"slug": ("title",)}
    show_change_link = True


class TutorialQuizOptionInline(admin.TabularInline):
    model = TutorialQuizOption
    extra = 4
    fields = ["display_order", "option_text", "is_correct", "explanation"]


@admin.register(TutorialCategory)
class TutorialCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon", "display_order", "is_active", "tutorial_count"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["display_order", "name"]

    def tutorial_count(self, obj):
        return obj.tutorials.count()

    tutorial_count.short_description = "Tutorials"


@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "difficulty",
        "estimated_minutes",
        "display_order",
        "is_published",
        "is_featured",
        "lessons_count",
        "created_at",
    ]
    list_filter = ["category", "difficulty", "is_published", "is_featured"]
    search_fields = ["title", "slug", "short_description", "content"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TutorialLessonInline]
    list_editable = ["display_order", "is_published", "is_featured"]
    ordering = ["display_order", "-created_at"]

    def lessons_count(self, obj):
        return obj.lessons.count()

    lessons_count.short_description = "Lessons"


@admin.register(TutorialLesson)
class TutorialLessonAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "tutorial",
        "display_order",
        "estimated_minutes",
        "is_published",
        "quizzes_count",
        "updated_at",
    ]
    list_filter = ["tutorial__category", "tutorial", "is_published"]
    search_fields = ["title", "slug", "content", "tutorial__title"]
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ["display_order", "is_published"]
    ordering = ["tutorial", "display_order", "id"]

    def quizzes_count(self, obj):
        return obj.quizzes.count()

    quizzes_count.short_description = "Quizzes"


@admin.register(TutorialQuiz)
class TutorialQuizAdmin(admin.ModelAdmin):
    list_display = ["question_preview", "lesson", "display_order", "options_count"]
    list_filter = ["lesson__tutorial", "lesson"]
    search_fields = ["question", "explanation", "lesson__title"]
    inlines = [TutorialQuizOptionInline]
    ordering = ["lesson", "display_order", "id"]

    def question_preview(self, obj):
        return obj.question[:80] + ("..." if len(obj.question) > 80 else "")

    question_preview.short_description = "Question"

    def options_count(self, obj):
        return obj.options.count()

    options_count.short_description = "Options"


@admin.register(TutorialProgress)
class TutorialProgressAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "tutorial",
        "progress_percentage_bar",
        "is_completed",
        "last_accessed_lesson",
        "last_accessed_at",
    ]
    list_filter = ["is_completed", "tutorial"]
    search_fields = ["user__username", "user__email", "tutorial__title"]
    readonly_fields = ["started_at", "last_accessed_at", "completed_at"]
    ordering = ["-last_accessed_at"]

    def progress_percentage_bar(self, obj):
        return f"{obj.progress_percentage}%"

    progress_percentage_bar.short_description = "Progress"


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "lesson", "is_completed", "completed_at"]
    list_filter = ["is_completed", "lesson__tutorial"]
    search_fields = ["user__username", "lesson__title"]
    readonly_fields = ["completed_at"]
    ordering = ["-completed_at"]
