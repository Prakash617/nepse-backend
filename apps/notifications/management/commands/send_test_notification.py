"""Management command to send a test real-time notification to a user."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.securities.models import Security

User = get_user_model()


class Command(BaseCommand):
    help = "Send a real-time test notification to a user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="Username to receive notification (defaults to first user in database).",
        )
        parser.add_argument(
            "--symbol",
            type=str,
            default="NABIL",
            help="Stock symbol for the alert (default: NABIL).",
        )
        parser.add_argument(
            "--title",
            type=str,
            default="Target Price Reached",
            help="Notification title.",
        )
        parser.add_argument(
            "--message",
            type=str,
            default="NABIL reached your target price of Rs. 540.00",
            help="Notification message.",
        )

    def handle(self, *args, **options):
        username = options.get("username")
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                raise CommandError(f"User '{username}' not found.")
        else:
            user = User.objects.first()
            if not user:
                raise CommandError("No users found in database. Please register/create a user first.")

        symbol = options["symbol"].upper()
        security = Security.objects.filter(symbol=symbol).first()

        notification = NotificationService.create(
            user=user,
            notification_type=Notification.NotificationType.PRICE_ALERT,
            title=f"{symbol}: {options['title']}",
            message=options["message"],
            security=security,
            data={
                "symbol": symbol,
                "price": "540.00",
                "target": "500.00",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created and dispatched notification #{notification.id} to user '{user.username}' for {symbol}!"
            )
        )
