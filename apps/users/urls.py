"""User auth URL routes."""

from django.urls import path

from apps.users.views import login_view, logout_view, me_view, register_view

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("me/", me_view, name="me"),
]
