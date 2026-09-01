"""Common sync utilities shared across all sync services."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Structured result returned by every sync service.

    Provides clear visibility into what happened during synchronization.
    Usable by management commands, Celery tasks, monitoring, and dashboards.
    """

    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_processed(self) -> int:
        return self.created + self.updated + self.skipped + self.failed

    def __str__(self) -> str:
        parts = [
            f"Created: {self.created}",
            f"Updated: {self.updated}",
            f"Skipped: {self.skipped}",
            f"Failed: {self.failed}",
        ]
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        return ", ".join(parts)
