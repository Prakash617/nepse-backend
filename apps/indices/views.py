"""Index API views."""

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.indices.serializers import IndexSnapshotSerializer, MarketIndexSerializer


class IndexHistoryPagination(PageNumberPagination):
    page_size = 5000
    page_size_query_param = "page_size"
    max_page_size = 10000


class MarketIndexListView(generics.ListAPIView):
    queryset = MarketIndex.objects.all()
    serializer_class = MarketIndexSerializer
    pagination_class = None


class MarketIndexDetailView(generics.RetrieveAPIView):
    queryset = MarketIndex.objects.all()
    serializer_class = MarketIndexSerializer
    lookup_field = "nepse_id"


class IndexHistoryView(generics.ListAPIView):
    serializer_class = IndexSnapshotSerializer
    queryset = IndexSnapshot.objects.none()
    pagination_class = IndexHistoryPagination

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return IndexSnapshot.objects.none()
        nepse_id = self.kwargs["nepse_id"]
        qs = IndexSnapshot.objects.filter(
            index__nepse_id=nepse_id,
        ).select_related("index")

        start_date = self.request.query_params.get("start")
        if start_date:
            qs = qs.filter(trading_date__gte=start_date)

        end_date = self.request.query_params.get("end")
        if end_date:
            qs = qs.filter(trading_date__lte=end_date)

        qs = qs.order_by("trading_date")
        return qs


class IndexIntradayView(generics.GenericAPIView):
    """Return intraday quote, session tick curve, and market breadth for an index."""

    def get(self, request, nepse_id: int | None = None) -> Response:
        target_id = nepse_id or int(request.query_params.get("nepse_id", 58))
        from apps.indices.services import get_index_intraday_data
        data = get_index_intraday_data(target_id)
        return Response(data)
