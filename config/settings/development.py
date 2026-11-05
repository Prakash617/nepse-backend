import os
from typing import Any, cast

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Development database (override with env vars if using external PostgreSQL)
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "localhost")  # noqa: F405
DATABASES["default"]["PORT"] = os.environ.get("POSTGRES_PORT", "5432")  # noqa: F405

# More permissive throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "10000/hour",
    "user": "10000/hour",
}

# Verbose logging in development
cast(dict[str, Any], LOGGING)["root"]["level"] = "DEBUG"  # noqa: F405
