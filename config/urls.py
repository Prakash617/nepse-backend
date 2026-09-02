from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/market/", include("apps.market.urls")),
    path("api/v1/securities/", include("apps.securities.urls")),
    path("api/v1/sectors/", include("apps.sectors.urls")),
    path("api/v1/indices/", include("apps.indices.urls")),
    path("api/v1/fundamentals/", include("apps.fundamentals.urls")),
    path("api/v1/corporate-actions/", include("apps.corporate_actions.urls")),
    path("api/v1/watchlists/", include("apps.watchlist.urls")),
    path("api/v1/alerts/", include("apps.alerts.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
