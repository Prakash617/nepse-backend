"""Tests for alert API endpoints."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.alerts.models import Alert
from apps.securities.models import Security

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
class TestAlertListCreate:
    def test_requires_auth(self, api_client):
        response = api_client.get("/api/v1/alerts/")
        assert response.status_code == 403

    def test_list_empty(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/alerts/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_create_alert(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            "/api/v1/alerts/",
            {
                "security": security.pk,
                "condition": "price_above",
                "threshold": "1000.00",
            },
        )
        assert response.status_code == 201
        assert response.data["security_symbol"] == "TEST"
        assert response.data["condition"] == "price_above"
        assert Alert.objects.filter(user=user).count() == 1

    def test_create_multiple_alerts_same_security(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        api_client.post(
            "/api/v1/alerts/",
            {"security": security.pk, "condition": "price_above", "threshold": "1000.00"},
        )
        response = api_client.post(
            "/api/v1/alerts/",
            {"security": security.pk, "condition": "price_below", "threshold": "500.00"},
        )
        assert response.status_code == 201
        assert Alert.objects.filter(user=user).count() == 2

    def test_list_only_own_alerts(self, api_client, user, other_user, security):
        api_client.force_authenticate(user=user)
        api_client.post(
            "/api/v1/alerts/",
            {"security": security.pk, "condition": "price_above", "threshold": "1000.00"},
        )
        api_client.force_authenticate(user=other_user)
        api_client.post(
            "/api/v1/alerts/",
            {"security": security.pk, "condition": "price_below", "threshold": "500.00"},
        )
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/alerts/")
        assert len(response.data["results"]) == 1

    def test_filter_by_condition(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        api_client.post(
            "/api/v1/alerts/",
            {"security": security.pk, "condition": "price_above", "threshold": "1000.00"},
        )
        api_client.post(
            "/api/v1/alerts/",
            {"security": security.pk, "condition": "price_below", "threshold": "500.00"},
        )
        response = api_client.get("/api/v1/alerts/", {"condition": "price_above"})
        assert len(response.data["results"]) == 1

    def test_filter_by_is_active(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        inactive_alert = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=1000, is_active=False,
        )
        active_alert = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_BELOW, threshold=500, is_active=True,
        )
        response = api_client.get("/api/v1/alerts/", {"is_active": "false"})
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == inactive_alert.pk
        response = api_client.get("/api/v1/alerts/", {"is_active": "true"})
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == active_alert.pk


@pytest.mark.django_db
class TestAlertDetail:
    def test_retrieve_alert(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        alert = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=1000,
        )
        response = api_client.get(f"/api/v1/alerts/{alert.pk}/")
        assert response.status_code == 200
        assert response.data["security_symbol"] == "TEST"
        assert response.data["threshold"] == "1000.00"

    def test_update_alert(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        alert = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=1000,
        )
        response = api_client.patch(
            f"/api/v1/alerts/{alert.pk}/", {"threshold": "1200.00"}
        )
        assert response.status_code == 200
        alert.refresh_from_db()
        assert alert.threshold == 1200

    def test_delete_alert(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        alert = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=1000,
        )
        response = api_client.delete(f"/api/v1/alerts/{alert.pk}/")
        assert response.status_code == 204
        assert Alert.objects.count() == 0

    def test_cannot_access_other_users_alert(self, api_client, user, other_user, security):
        alert = Alert.objects.create(
            user=other_user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=1000,
        )
        api_client.force_authenticate(user=user)
        response = api_client.get(f"/api/v1/alerts/{alert.pk}/")
        assert response.status_code == 404

    def test_toggle_is_active(self, api_client, user, security):
        api_client.force_authenticate(user=user)
        alert = Alert.objects.create(
            user=user, security=security,
            condition=Alert.ConditionType.PRICE_ABOVE, threshold=1000, is_active=True,
        )
        response = api_client.patch(f"/api/v1/alerts/{alert.pk}/", {"is_active": False})
        assert response.status_code == 200
        alert.refresh_from_db()
        assert alert.is_active is False
