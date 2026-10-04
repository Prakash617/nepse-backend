"""Market API views."""

from datetime import date

from django.core.cache import cache
from django.db.models import Max, Q
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market.models import MarketSnapshot
from apps.market.serializers import MarketStatusSerializer, MarketSummarySerializer
from apps.market.services import get_current_market_status
from apps.prices.models import DailyPrice


def _get_latest_trading_date() -> date | None:
    """Get the latest available trading date from stored data."""
    result = DailyPrice.objects.aggregate(latest=Max("trading_date"))
    return result["latest"]


class MarketSummaryView(APIView):
    """Return the latest market snapshot."""

    def get(self, request: Request) -> Response:
        latest_date = _get_latest_trading_date()
        if latest_date is None:
            return Response({"detail": "No market data available."}, status=200)

        cache_key = f"market_summary_{latest_date}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        try:
            snapshot = MarketSnapshot.objects.get(trading_date=latest_date)
        except MarketSnapshot.DoesNotExist:
            return Response({"detail": "No market snapshot available."}, status=200)

        serializer = MarketSummarySerializer(snapshot)
        cache.set(cache_key, serializer.data, timeout=300)
        return Response(serializer.data)


class MarketGainersView(APIView):
    """Return top gainers based on percentage_change."""

    def get(self, request: Request) -> Response:
        latest_date = _get_latest_trading_date()
        if latest_date is None:
            return Response({"results": []})

        limit = self._get_limit(request)
        cache_key = f"market_gainers_{latest_date}_{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        prices = (
            DailyPrice.objects.filter(
                trading_date=latest_date,
                percentage_change__isnull=False,
                percentage_change__gt=0,
            )
            .filter(Q(close__isnull=False) | Q(ltp__isnull=False))
            .select_related("security")
            .order_by("-percentage_change")[:limit]
        )

        results = [
            {
                "symbol": p.security.symbol,
                "close": str(p.close or p.ltp),
                "percentage_change": str(p.percentage_change),
                "volume": p.volume,
                "turnover": str(p.turnover) if p.turnover else None,
            }
            for p in prices
        ]

        cache.set(cache_key, {"results": results}, timeout=300)
        return Response({"results": results})

    def _get_limit(self, request: Request) -> int:
        try:
            limit = int(request.query_params.get("limit", 20))
            return min(limit, 100)
        except (ValueError, TypeError):
            return 20


class MarketLosersView(APIView):
    """Return top losers based on percentage_change."""

    def get(self, request: Request) -> Response:
        latest_date = _get_latest_trading_date()
        if latest_date is None:
            return Response({"results": []})

        limit = self._get_limit(request)
        cache_key = f"market_losers_{latest_date}_{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        prices = (
            DailyPrice.objects.filter(
                trading_date=latest_date,
                percentage_change__isnull=False,
                percentage_change__lt=0,
            )
            .filter(Q(close__isnull=False) | Q(ltp__isnull=False))
            .select_related("security")
            .order_by("percentage_change")[:limit]
        )

        results = [
            {
                "symbol": p.security.symbol,
                "close": str(p.close or p.ltp),
                "percentage_change": str(p.percentage_change),
                "volume": p.volume,
                "turnover": str(p.turnover) if p.turnover else None,
            }
            for p in prices
        ]

        cache.set(cache_key, {"results": results}, timeout=300)
        return Response({"results": results})

    def _get_limit(self, request: Request) -> int:
        try:
            limit = int(request.query_params.get("limit", 20))
            return min(limit, 100)
        except (ValueError, TypeError):
            return 20


class MarketTurnoverView(APIView):
    """Return top stocks by turnover."""

    def get(self, request: Request) -> Response:
        latest_date = _get_latest_trading_date()
        if latest_date is None:
            return Response({"results": []})

        limit = self._get_limit(request)
        cache_key = f"market_turnover_{latest_date}_{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        prices = (
            DailyPrice.objects.filter(
                trading_date=latest_date,
                turnover__isnull=False,
            )
            .select_related("security")
            .order_by("-turnover")[:limit]
        )

        results = [
            {
                "symbol": p.security.symbol,
                "close": str(p.close) if p.close else None,
                "percentage_change": str(p.percentage_change) if p.percentage_change else None,
                "volume": p.volume,
                "turnover": str(p.turnover),
            }
            for p in prices
        ]

        cache.set(cache_key, {"results": results}, timeout=300)
        return Response({"results": results})

    def _get_limit(self, request: Request) -> int:
        try:
            limit = int(request.query_params.get("limit", 20))
            return min(limit, 100)
        except (ValueError, TypeError):
            return 20


class MarketVolumeView(APIView):
    """Return top stocks by volume."""

    def get(self, request: Request) -> Response:
        latest_date = _get_latest_trading_date()
        if latest_date is None:
            return Response({"results": []})

        limit = self._get_limit(request)
        cache_key = f"market_volume_{latest_date}_{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        prices = (
            DailyPrice.objects.filter(
                trading_date=latest_date,
                volume__isnull=False,
            )
            .select_related("security")
            .order_by("-volume")[:limit]
        )

        results = [
            {
                "symbol": p.security.symbol,
                "close": str(p.close) if p.close else None,
                "percentage_change": str(p.percentage_change) if p.percentage_change else None,
                "volume": p.volume,
                "turnover": str(p.turnover) if p.turnover else None,
            }
            for p in prices
        ]

        cache.set(cache_key, {"results": results}, timeout=300)
        return Response({"results": results})

    def _get_limit(self, request: Request) -> int:
        try:
            limit = int(request.query_params.get("limit", 20))
            return min(limit, 100)
        except (ValueError, TypeError):
            return 20


class MarketStatusView(APIView):
    """Return the current NEPSE market status (LIVE / CLOSED)."""

    def get(self, request: Request) -> Response:
        cache_key = "nepse_market_status"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = get_current_market_status()
        cache.set(cache_key, data, timeout=30)
        return Response(data)

