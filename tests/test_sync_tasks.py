"""Tests for Celery tasks (thin wrappers)."""
from unittest.mock import MagicMock, patch

import pytest

from apps.common.sync import SyncResult


@pytest.mark.django_db
class TestCeleryTasks:
    @patch("apps.sectors.tasks.NepseClient")
    @patch("apps.sectors.tasks.sync_sectors")
    def test_sync_sectors_task(self, mock_sync, mock_client_cls):
        from apps.sectors.tasks import sync_sectors_task

        mock_client = MagicMock()
        mock_client.get_sectors.return_value = [{"id": 1, "name": "Banks"}]
        mock_client_cls.return_value = mock_client
        mock_sync.return_value = SyncResult(created=1)

        result = sync_sectors_task()
        assert result["created"] == 1
        mock_client.get_sectors.assert_called_once()

    @patch("apps.securities.tasks.NepseClient")
    @patch("apps.securities.tasks.sync_securities")
    def test_sync_securities_task(self, mock_sync, mock_client_cls):
        from apps.securities.tasks import sync_securities_task

        mock_client = MagicMock()
        mock_client.get_securities.return_value = []
        mock_client_cls.return_value = mock_client
        mock_sync.return_value = SyncResult(created=0)

        result = sync_securities_task()
        assert result["created"] == 0

    @patch("apps.prices.tasks.NepseClient")
    @patch("apps.prices.tasks.sync_daily_prices")
    def test_sync_daily_prices_task(self, mock_sync, mock_client_cls):
        from apps.prices.tasks import sync_daily_prices_task

        mock_client = MagicMock()
        mock_client.get_today_prices.return_value = []
        mock_client_cls.return_value = mock_client
        mock_sync.return_value = SyncResult(created=5, updated=10)

        result = sync_daily_prices_task()
        assert result["created"] == 5
        assert result["updated"] == 10

    @patch("apps.prices.tasks.NepseClient")
    @patch("apps.prices.tasks.sync_intraday_prices")
    def test_sync_intraday_prices_task(self, mock_sync, mock_client_cls):
        from apps.prices.tasks import sync_intraday_prices_task

        mock_client = MagicMock()
        mock_client.get_live_trades.return_value = []
        mock_client_cls.return_value = mock_client
        mock_sync.return_value = SyncResult(created=3)

        result = sync_intraday_prices_task()
        assert result["created"] == 3

    @patch("apps.indices.tasks.NepseClient")
    @patch("apps.indices.tasks.sync_indices")
    def test_sync_indices_task(self, mock_sync, mock_client_cls):
        from apps.indices.tasks import sync_indices_task

        mock_client = MagicMock()
        mock_client.get_indices.return_value = []
        mock_client.get_sector_indices.return_value = []
        mock_client_cls.return_value = mock_client
        mock_sync.return_value = SyncResult(created=2)

        result = sync_indices_task()
        assert result["created"] == 2

    @patch("apps.indices.tasks.NepseClient")
    @patch("apps.indices.tasks.sync_index_snapshots")
    def test_sync_index_snapshots_task(self, mock_sync, mock_client_cls):
        from apps.indices.tasks import sync_index_snapshots_task

        mock_client = MagicMock()
        mock_client.get_index_history.return_value = []
        mock_client_cls.return_value = mock_client
        mock_sync.return_value = SyncResult(created=10)

        result = sync_index_snapshots_task(58, "2025-01-01", "2025-01-31")
        assert result["created"] == 10
        mock_client.get_index_history.assert_called_once_with(58, "2025-01-01", "2025-01-31")

    @patch("apps.market.tasks.NepseClient")
    @patch("apps.market.tasks.sync_market_snapshot")
    def test_sync_market_snapshot_task(self, mock_sync, mock_client_cls):
        from apps.market.tasks import sync_market_snapshot_task

        mock_client = MagicMock()
        mock_client.get_market_summary.return_value = {"close": "2000.00"}
        mock_client_cls.return_value = mock_client
        mock_sync.return_value = SyncResult(created=1)

        result = sync_market_snapshot_task()
        assert result["created"] == 1
