"""Sector API views."""

from django.db.models import Count, Q
from rest_framework import generics

from apps.sectors.models import Sector
from apps.sectors.serializers import SectorListSerializer


class SectorListView(generics.ListAPIView):
    queryset = Sector.objects.annotate(
        _security_count=Count("securities"),
        _equity_count=Count("securities", filter=Q(securities__security_type__iexact="Equity")),
    ).order_by("name")
    serializer_class = SectorListSerializer
    pagination_class = None
