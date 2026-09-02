"""Authentication middleware for WebSocket connections."""

from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.utils import timezone

User = get_user_model()


@database_sync_to_async
def get_user_from_session_key(session_key: str):
    """Retrieve the user associated with a Django session key."""
    try:
        session = Session.objects.get(session_key=session_key, expire_date__gt=timezone.now())
        session_data = session.get_decoded()
        user_id = session_data.get("_auth_user_id")
        if user_id:
            return User.objects.get(pk=user_id)
    except Exception:
        pass
    return AnonymousUser()


class SessionAuthMiddleware(BaseMiddleware):
    """Custom middleware to authenticate WebSocket connections via cookie or sessionid query param."""

    async def __call__(self, scope, receive, send):
        # If user is already authenticated by standard AuthMiddlewareStack, keep it
        user = scope.get("user")
        if user and user.is_authenticated:
            return await super().__call__(scope, receive, send)

        # Check cookies first
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode("utf-8")
        session_key = None

        if cookie_header:
            from http.cookies import SimpleCookie

            cookie = SimpleCookie()
            cookie.load(cookie_header)
            if "sessionid" in cookie:
                session_key = cookie["sessionid"].value

        # Check query string as fallback
        if not session_key and "query_string" in scope:
            query_string = scope.get("query_string", b"").decode("utf-8")
            params = parse_qs(query_string)
            if "sessionid" in params:
                session_key = params["sessionid"][0]

        if session_key:
            scope["user"] = await get_user_from_session_key(session_key)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
