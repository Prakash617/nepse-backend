"""Tests for watchlist API endpoints."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.securities.models import Security
from apps.watchlist.models import Watchlist, WatchlistItem

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def other_user():
    return User.objects.create_user(username="otheruser", password="otherpass123")


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100, symbol="TEST", company_name="Test Company"
    )


@pytest.fixture
def security2():
    return Security.objects.create(
        nepse_id=101, symbol="TEST2", company_name="Test Company 2"
    )


@pytest.mark.django_db
class TestWatchlistListCreate:
    def test_requires_auth(self, api_client):
        response = api_client.get("/api/v1/watchlists/")
        assert response.status_code == 403

    def test_list_empty(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/watchlists/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_create_watchlist(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            "/api/v1/watchlists/",
            {"name": "My Watchlist", "description": "Tech stocks"},
        )
        assert response.status_code == 201
        assert response.data["name"] == "My Watchlist"
        assert Watchlist.objects.filter(user=user).count() == 1

    def test_create_watchlist_duplicate_name(self, api_client, user):
        api_client.force_authenticate(user=user)
        api_client.post("/api/v1/watchlists/", {"name": "My Watchlist"})
        response = api_client.post("/api/v1/watchlists/", {"name": "My Watchlist"})
        assert response.status_code == 400

    def test_list_only_own_watchlists(self, api_client, user, other_user):
        api_client.force_authenticate(user=user)
        api_client.post("/api/v1/watchlists/", {"name": "My Watchlist"})
        api_client.force_authenticate(user=other_user)
        api_client.post("/api/v1/watchlists/", {"name": "Other Watchlist"})
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/watchlists/")
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "My Watchlist"


@pytest.mark.django_db
class TestWatchlistDetail:
    def test_retrieve_watchlist(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        WatchlistItem.objects.create(watchlist=wl, security=security)
        response = api_client.get(f"/api/v1/watchlists/{wl.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "My Watchlist"
        assert len(response.data["items"]) == 1
        assert response.data["items"][0]["security_symbol"] == "TEST"

    def test_update_watchlist(self, api_client, user):
        api_client.force_authenticate(user=user)
        wl = Watchlist.objects.create(user=user, name="Old Name")
        response = api_client.patch(f"/api/v1/watchlists/{wl.pk}/", {"name": "New Name"})
        assert response.status_code == 200
        wl.refresh_from_db()
        assert wl.name == "New Name"

    def test_delete_watchlist(self, api_client, user):
        api_client.force_authenticate(user=user)
        wl = Watchlist.objects.create(user=user, name="To Delete")
        response = api_client.delete(f"/api/v1/watchlists/{wl.pk}/")
        assert response.status_code == 204
        assert Watchlist.objects.count() == 0

    def test_cannot_access_other_users_watchlist(self, api_client, user, other_user):
        wl = Watchlist.objects.create(user=other_user, name="Other's Watchlist")
        api_client.force_authenticate(user=user)
        response = api_client.get(f"/api/v1/watchlists/{wl.pk}/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestWatchlistItems:
    def test_add_item(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        response = api_client.post(
            f"/api/v1/watchlists/{wl.pk}/items/",
            {"security": security.pk, "note": "Track this"},
        )
        assert response.status_code == 201
        assert WatchlistItem.objects.filter(watchlist=wl).count() == 1

    def test_add_duplicate_item(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        api_client.post(f"/api/v1/watchlists/{wl.pk}/items/", {"security": security.pk})
        response = api_client.post(
            f"/api/v1/watchlists/{wl.pk}/items/", {"security": security.pk}
        )
        assert response.status_code == 400

    def test_delete_item(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        item = WatchlistItem.objects.create(watchlist=wl, security=security)
        response = api_client.delete(f"/api/v1/watchlists/{wl.pk}/items/{item.pk}/")
        assert response.status_code == 204
        assert WatchlistItem.objects.count() == 0

    def test_cannot_add_to_other_users_watchlist(self, api_client, user, other_user, security):
        wl = Watchlist.objects.create(user=other_user, name="Other's Watchlist")
        api_client.force_authenticate(user=user)
        response = api_client.post(f"/api/v1/watchlists/{wl.pk}/items/", {"security": security.pk})
        assert response.status_code == 404

    def test_watchlist_detail_includes_items(self, api_client, user, security, security2):
        api_client.force_authenticate(user=user)
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        WatchlistItem.objects.create(watchlist=wl, security=security)
        WatchlistItem.objects.create(watchlist=wl, security=security2)
        response = api_client.get(f"/api/v1/watchlists/{wl.pk}/")
        assert response.data["item_count"] == 2
        assert len(response.data["items"]) == 2
