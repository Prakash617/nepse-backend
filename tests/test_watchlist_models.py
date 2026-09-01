"""Tests for watchlist models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.securities.models import Security
from apps.watchlist.models import Watchlist, WatchlistItem

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def security():
    return Security.objects.create(
        nepse_id=100, symbol="TEST", company_name="Test Company"
    )


@pytest.mark.django_db
class TestWatchlist:
    def test_create_watchlist(self, user):
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        assert wl.pk is not None
        assert wl.user == user
        assert wl.name == "My Watchlist"
        assert str(wl) == "testuser - My Watchlist"

    def test_unique_together_user_name(self, user):
        Watchlist.objects.create(user=user, name="My Watchlist")
        with pytest.raises(IntegrityError):
            Watchlist.objects.create(user=user, name="My Watchlist")

    def test_different_users_same_name(self):
        user1 = User.objects.create_user(username="user1", password="pass1")
        user2 = User.objects.create_user(username="user2", password="pass2")
        Watchlist.objects.create(user=user1, name="Watchlist")
        wl2 = Watchlist.objects.create(user=user2, name="Watchlist")
        assert wl2.pk is not None

    def test_ordering(self, user):
        wl1 = Watchlist.objects.create(user=user, name="First")
        wl2 = Watchlist.objects.create(user=user, name="Second")
        watchlists = list(Watchlist.objects.filter(user=user))
        assert watchlists[0] == wl2
        assert watchlists[1] == wl1


@pytest.mark.django_db
class TestWatchlistItem:
    def test_add_security_to_watchlist(self, user, security):
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        item = WatchlistItem.objects.create(
            watchlist=wl, security=security, note="Interesting stock"
        )
        assert item.pk is not None
        assert item.watchlist == wl
        assert item.security == security
        assert item.note == "Interesting stock"
        expected = f"My Watchlist - {security.symbol}"
        assert str(item) == expected

    def test_unique_together_watchlist_security(self, user, security):
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        WatchlistItem.objects.create(watchlist=wl, security=security)
        with pytest.raises(IntegrityError):
            WatchlistItem.objects.create(watchlist=wl, security=security)

    def test_same_security_different_watchlists(self, user, security):
        wl1 = Watchlist.objects.create(user=user, name="Watchlist 1")
        wl2 = Watchlist.objects.create(user=user, name="Watchlist 2")
        WatchlistItem.objects.create(watchlist=wl1, security=security)
        item2 = WatchlistItem.objects.create(watchlist=wl2, security=security)
        assert item2.pk is not None

    def test_cascade_delete(self, user, security):
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        WatchlistItem.objects.create(watchlist=wl, security=security)
        wl.delete()
        assert WatchlistItem.objects.count() == 0

    def test_note_optional(self, user, security):
        wl = Watchlist.objects.create(user=user, name="My Watchlist")
        item = WatchlistItem.objects.create(watchlist=wl, security=security)
        assert item.note == ""
