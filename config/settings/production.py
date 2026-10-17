import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Production security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() == "true"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

# Production hosts and CSRF origins from env
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if os.environ.get("DJANGO_ALLOWED_HOSTS") else ["*"]
CSRF_TRUSTED_ORIGINS = (
    os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if os.environ.get("CSRF_TRUSTED_ORIGINS")
    else [
        "https://nepse-alert.vercel.app",
        "http://132.226.211.176",
        "http://localhost:3000",
    ]
)
CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL_ORIGINS", "false").lower() == "true"
CORS_ALLOWED_ORIGINS = (
    [origin.strip() for origin in os.environ.get("CORS_ALLOWED_ORIGINS").split(",") if origin.strip()]
    if os.environ.get("CORS_ALLOWED_ORIGINS")
    else [
        "https://nepse-alert.vercel.app",
        "https://nepse-alert-lime.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
)
CORS_ALLOW_CREDENTIALS = True

# Production database — require explicit env vars
DATABASES["default"]["NAME"] = os.environ.get("POSTGRES_DB", "nepse_platform")  # noqa: F405
DATABASES["default"]["USER"] = os.environ.get("POSTGRES_USER", "nepse")  # noqa: F405
DATABASES["default"]["PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "")  # noqa: F405
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "localhost")  # noqa: F405
DATABASES["default"]["PORT"] = os.environ.get("POSTGRES_PORT", "5432")  # noqa: F405
