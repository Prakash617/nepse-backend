"""User authentication API."""

import logging

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.authentication import CsrfExemptSessionAuthentication

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([AllowAny])
def register_view(request: Request) -> Response:
    """Register a new user."""
    username = request.data.get("username", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")
    password2 = request.data.get("password2", "")

    if not username or not password:
        return Response(
            {"error": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != password2:
        return Response(
            {"error": "Passwords do not match."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(password)
    except ValidationError as e:
        return Response(
            {"error": " ".join(e.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username, email=email, password=password
    )
    login(request, user)
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    """Log in a user."""
    username = request.data.get("username", "")
    password = request.data.get("password", "")

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"error": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )


@api_view(["POST", "GET"])
@authentication_classes([CsrfExemptSessionAuthentication, BasicAuthentication])
@permission_classes([AllowAny])
def logout_view(request: Request) -> Response:
    """Log out the current user."""
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request: Request) -> Response:
    """Get the current user's profile."""
    user = request.user
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )
