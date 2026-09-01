"""Management command to evaluate alerts and create notifications."""

import logging

from django.core.management.base import BaseCommand

from apps.notifications.services import evaluate_alerts

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Evaluate all active alerts and create notifications for triggered ones."

    def handle(self, *args, **options):
        self.stdout.write("Evaluating alerts...")

        result = evaluate_alerts()

        self.stdout.write(self.style.SUCCESS(
            f"Alert evaluation complete:\n"
            f"  Evaluated: {result['evaluated']}\n"
            f"  Triggered: {result['triggered']}\n"
            f"  Skipped: {result['skipped']}\n"
            f"  Errors: {result['errors']}"
        ))
