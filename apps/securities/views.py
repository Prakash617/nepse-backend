"""Security API views."""

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.exceptions import NotFound

from apps.prices.models import DailyPrice, IntradayPrice
from apps.prices.serializers import DailyPriceSerializer, IntradayPriceSerializer
from apps.securities.models import Security
from apps.securities.serializers import SecurityDetailSerializer, SecurityListSerializer


class SecurityListView(generics.ListAPIView):
    serializer_class = SecurityListSerializer

    def get_queryset(self) -> QuerySet:
        qs = Security.objects.select_related("sector").all()

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(symbol__icontains=search)

        sector = self.request.query_params.get("sector")
        if sector:
            qs = qs.filter(sector__name__icontains=sector)

        security_type = self.request.query_params.get("security_type")
        if security_type:
            qs = qs.filter(security_type__iexact=security_type)

        ordering = self.request.query_params.get("ordering", "symbol")
        allowed_orderings = {"symbol", "company_name", "security_type", "listing_date"}
        if ordering.lstrip("-") in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("symbol")

        return qs


class SecurityDetailView(generics.RetrieveAPIView):
    queryset = Security.objects.select_related("sector").all()
    serializer_class = SecurityDetailSerializer
    lookup_field = "symbol"
    lookup_url_kwarg = "symbol"

    def get_object(self) -> Security:
        queryset = self.filter_queryset(self.get_queryset())
        symbol = self.kwargs[self.lookup_url_kwarg]
        obj = queryset.filter(symbol__iexact=symbol).first()
        if obj is None:
            raise NotFound("Security not found.")
        self.check_object_permissions(self.request, obj)
        return obj


class SecurityHistoryView(generics.ListAPIView):
    serializer_class = DailyPriceSerializer
    lookup_field = "symbol"
    queryset = DailyPrice.objects.none()

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return DailyPrice.objects.none()
        symbol = self.kwargs["symbol"]
        qs = DailyPrice.objects.filter(
            security__symbol__iexact=symbol,
        ).select_related("security")

        start_date = self.request.query_params.get("start")
        if start_date:
            qs = qs.filter(trading_date__gte=start_date)

        end_date = self.request.query_params.get("end")
        if end_date:
            qs = qs.filter(trading_date__lte=end_date)

        qs = qs.order_by("trading_date")
        return qs


class SecurityIntradayView(generics.ListAPIView):
    serializer_class = IntradayPriceSerializer
    lookup_field = "symbol"
    queryset = IntradayPrice.objects.none()

    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return IntradayPrice.objects.none()
        symbol = self.kwargs["symbol"]
        return IntradayPrice.objects.filter(
            security__symbol__iexact=symbol,
        ).select_related("security").order_by("-timestamp")
