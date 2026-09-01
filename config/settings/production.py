import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Production security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() == "true"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Production hosts from env
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if os.environ.get("DJANGO_ALLOWED_HOSTS") else []

# Production database — require explicit env vars
DATABASES["default"]["NAME"] = os.environ.get("POSTGRES_DB", "nepse_platform")  # noqa: F405
DATABASES["default"]["USER"] = os.environ.get("POSTGRES_USER", "nepse")  # noqa: F405
DATABASES["default"]["PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "")  # noqa: F405
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "localhost")  # noqa: F405
DATABASES["default"]["PORT"] = os.environ.get("POSTGRES_PORT", "5432")  # noqa: F405
