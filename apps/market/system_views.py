"""System specifications and telemetry API views."""

from django.db import connection
from django.db.utils import OperationalError
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market.system_service import (
    get_sync_execution_logs,
    get_system_specs,
    trigger_feed_sync,
)


class HealthCheckView(APIView):
    """Liveness/readiness probe used by deployment automation and uptime monitors."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Health check",
        description="Returns 200 when the API can reach PostgreSQL, 503 otherwise.",
        responses={
            200: OpenApiResponse(description="Service and database are healthy"),
            503: OpenApiResponse(description="A required dependency is unavailable"),
        },
    )
    def get(self, request: Request) -> Response:
        try:
            connection.ensure_connection()
        except OperationalError:
            return Response(
                {"status": "error", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})


class SystemSpecsView(APIView):
    """Provide system specifications, telemetry, and data fetching schedules."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get system specifications & sync schedules",
        description=(
            "Returns detailed telemetry on data fetching intervals (intraday prices, "
            "market summary, indices, alerts evaluation, EOD candles), market trading "
            "schedule, infrastructure latencies (PostgreSQL, Redis), Telegram bot telemetry, "
            "and recent sync execution logs."
        ),
        responses={200: OpenApiResponse(description="System specs and fetch schedule data")},
    )
    def get(self, request: Request) -> Response:
        data = get_system_specs()
        return Response(data)


class SystemSyncTriggerView(APIView):
    """Trigger immediate synchronization of a data feed."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Trigger immediate synchronization of a specific data feed",
        description="Executes manual on-demand data sync for intraday_prices, market_summary, market_indices, alerts_engine, daily_prices, or all.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "feed_id": {
                        "type": "string",
                        "enum": ["intraday_prices", "market_summary", "market_indices", "alerts_engine", "daily_prices", "all"],
                        "default": "intraday_prices",
                    }
                },
                "required": ["feed_id"],
            }
        },
        responses={200: OpenApiResponse(description="Sync execution result and metrics")},
    )
    def post(self, request: Request) -> Response:
        feed_id = request.data.get("feed_id", "intraday_prices")
        result = trigger_feed_sync(feed_id)
        http_status = status.HTTP_200_OK if result["status"] == "SUCCESS" else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)


class SystemSyncHistoryView(APIView):
    """Retrieve recent task execution logs."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get recent sync execution history logs",
        responses={200: OpenApiResponse(description="List of recent task executions")},
    )
    def get(self, request: Request) -> Response:
        limit = int(request.query_params.get("limit", 20))
        logs = get_sync_execution_logs(limit=limit)
        return Response(logs)
