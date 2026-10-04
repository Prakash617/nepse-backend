"""Custom authentication classes for DRF."""

from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """SessionAuthentication without CSRF enforcement for decoupled API clients."""

    def enforce_csrf(self, request):
        return  # Skip CSRF check for API requests
