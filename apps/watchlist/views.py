"""Watchlist API views.

All endpoints require authentication. Users can only access their own watchlists.
"""

from django.db import IntegrityError
from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.watchlist.models import Watchlist, WatchlistItem
from apps.watchlist.serializers import (
    WatchlistItemSerializer,
    WatchlistListSerializer,
    WatchlistSerializer,
)


class WatchlistListCreateView(generics.ListCreateAPIView):
    """List user's watchlists or create a new one."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return WatchlistSerializer
        return WatchlistListSerializer

    def get_queryset(self) -> QuerySet:
        return Watchlist.objects.filter(user=self.request.user).prefetch_related("items")

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError as err:
            from rest_framework.serializers import ValidationError

            raise ValidationError({"name": "A watchlist with this name already exists."}) from err


class WatchlistDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a watchlist."""

    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        return Watchlist.objects.filter(user=self.request.user).prefetch_related("items")


class WatchlistItemCreateView(generics.CreateAPIView):
    """Add a security to a watchlist."""

    serializer_class = WatchlistItemSerializer
    permission_classes = [IsAuthenticated]

    def get_watchlist(self) -> Watchlist:
        try:
            return Watchlist.objects.get(
                pk=self.kwargs["pk"],
                user=self.request.user,
            )
        except Watchlist.DoesNotExist as err:
            raise NotFound("Watchlist not found.") from err

    def perform_create(self, serializer):
        watchlist = self.get_watchlist()
        try:
            serializer.save(watchlist=watchlist)
        except IntegrityError as err:
            from rest_framework.serializers import ValidationError

            raise ValidationError({"security": "This security is already in the watchlist."}) from err


class WatchlistItemDeleteView(APIView):
    """Remove a security from a watchlist."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk: int, item_pk: int) -> Response:
        try:
            item = WatchlistItem.objects.get(
                pk=item_pk,
                watchlist__pk=pk,
                watchlist__user=request.user,
            )
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except WatchlistItem.DoesNotExist:
            return Response(
                {"detail": "Watchlist item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
