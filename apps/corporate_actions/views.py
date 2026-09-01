"""Corporate Actions API views."""

from django.db.models import QuerySet
from rest_framework import generics

from apps.corporate_actions.models import BonusShare, Dividend
from apps.corporate_actions.serializers import BonusShareSerializer, DividendSerializer


class DividendListView(generics.ListAPIView):
    queryset = Dividend.objects.select_related("security").all()
    serializer_class = DividendSerializer

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()

        symbol = self.request.query_params.get("security__symbol")
        if symbol:
            qs = qs.filter(security__symbol__iexact=symbol)

        fiscal_year = self.request.query_params.get("fiscal_year")
        if fiscal_year:
            qs = qs.filter(fiscal_year=fiscal_year)

        return qs.order_by("-fiscal_year", "security__symbol")


class DividendDetailView(generics.RetrieveAPIView):
    queryset = Dividend.objects.select_related("security").all()
    serializer_class = DividendSerializer


class BonusShareListView(generics.ListAPIView):
    queryset = BonusShare.objects.select_related("security").all()
    serializer_class = BonusShareSerializer

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()

        symbol = self.request.query_params.get("security__symbol")
        if symbol:
            qs = qs.filter(security__symbol__iexact=symbol)

        fiscal_year = self.request.query_params.get("fiscal_year")
        if fiscal_year:
            qs = qs.filter(fiscal_year=fiscal_year)

        return qs.order_by("-fiscal_year", "security__symbol")


class BonusShareDetailView(generics.RetrieveAPIView):
    queryset = BonusShare.objects.select_related("security").all()
    serializer_class = BonusShareSerializer
