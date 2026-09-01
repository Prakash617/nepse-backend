"""All Celery tasks — imported by celery autodiscover.

Each import makes the tasks available for registration.
"""

from tasks.fundamentals import (  # noqa: F401
    sync_company_profiles_task,
    sync_financial_reports_task,
)
from tasks.notifications import evaluate_alerts_task  # noqa: F401
