"""Smoke tests to verify Django starts correctly."""
import django


def test_django_setup() -> None:
    """Verify Django can be set up."""
    django.setup()
    from django.conf import settings
    assert settings.ROOT_URLCONF == "config.urls"


def test_database_config() -> None:
    """Verify database configuration exists."""
    from django.conf import settings
    assert "default" in settings.DATABASES
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


def test_cache_config() -> None:
    """Verify Redis cache configuration exists."""
    from django.conf import settings
    assert "default" in settings.CACHES
    assert "redis" in settings.CACHES["default"]["BACKEND"].lower()


def test_celery_config() -> None:
    """Verify Celery configuration exists."""
    from django.conf import settings
    assert hasattr(settings, "CELERY_BROKER_URL")
    assert hasattr(settings, "CELERY_RESULT_BACKEND")


def test_installed_apps() -> None:
    """Verify all expected apps are installed."""
    from django.conf import settings
    expected_apps = [
        "apps.users",
        "apps.market",
        "apps.securities",
        "apps.prices",
        "apps.indices",
        "apps.sectors",
        "apps.fundamentals",
        "apps.corporate_actions",
        "apps.ipo",
        "apps.news",
        "apps.watchlist",
        "apps.alerts",
        "apps.notifications",
    ]
    for app in expected_apps:
        assert app in settings.INSTALLED_APPS, f"{app} not in INSTALLED_APPS"


def test_rest_framework_config() -> None:
    """Verify DRF configuration exists."""
    from django.conf import settings
    assert hasattr(settings, "REST_FRAMEWORK")
    assert "DEFAULT_SCHEMA_CLASS" in settings.REST_FRAMEWORK


def test_time_zone() -> None:
    """Verify Nepal timezone is configured."""
    from django.conf import settings
    assert settings.TIME_ZONE == "Asia/Kathmandu"


def test_middleware() -> None:
    """Verify security middleware is present."""
    from django.conf import settings
    assert "django.middleware.security.SecurityMiddleware" in settings.MIDDLEWARE
    assert "django.contrib.auth.middleware.AuthenticationMiddleware" in settings.MIDDLEWARE
