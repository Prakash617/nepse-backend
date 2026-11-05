"""URL routing for the Learning Center app."""

from django.urls import path

from apps.learning import views

app_name = "learning"

urlpatterns = [
    # Categories
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    # Tutorials
    path("tutorials/", views.TutorialListView.as_view(), name="tutorial-list"),
    path("tutorials/<slug:slug>/", views.TutorialDetailView.as_view(), name="tutorial-detail"),
    path(
        "tutorials/<slug:slug>/lessons/",
        views.TutorialLessonListView.as_view(),
        name="tutorial-lesson-list",
    ),
    path(
        "tutorials/<slug:slug>/progress/",
        views.TutorialProgressDetailView.as_view(),
        name="tutorial-progress-detail",
    ),
    # Individual Lessons
    path("lessons/<slug:lesson_slug>/", views.LessonDetailView.as_view(), name="lesson-detail"),
    path(
        "lessons/<slug:lesson_slug>/complete/",
        views.LessonCompleteView.as_view(),
        name="lesson-complete",
    ),
    path("lessons/<slug:lesson_slug>/quiz/", views.LessonQuizView.as_view(), name="lesson-quiz"),
    path(
        "lessons/<slug:lesson_slug>/quiz/submit/",
        views.LessonQuizSubmitView.as_view(),
        name="lesson-quiz-submit",
    ),
    # User overall learning progress
    path("progress/", views.UserProgressListView.as_view(), name="user-progress-list"),
]
