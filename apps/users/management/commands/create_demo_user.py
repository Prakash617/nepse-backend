"""Management command to create or reset the demo account."""

from django.core.management.base import BaseCommand

from apps.securities.models import Security
from apps.users.models import User
from apps.watchlist.models import Watchlist, WatchlistItem


class Command(BaseCommand):
    help = "Create or reset the demo user account (demo / DemoUser@123)."

    def handle(self, *args, **options):
        username = "demo"
        password = "DemoUser@123"
        email = "demo@nepse.com"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": "Demo", "last_name": "User"},
        )
        user.set_password(password)
        user.save()

        # Create or update default watchlist
        wl, _ = Watchlist.objects.get_or_create(
            user=user,
            name="My Portfolio",
            defaults={"description": "Demo stock portfolio"},
        )

        sample_symbols = ["NABIL", "HDL", "NICA", "SHIVM", "CHCL"]
        added_count = 0
        for sym in sample_symbols:
            sec = Security.objects.filter(symbol=sym).first()
            if sec:
                _, item_created = WatchlistItem.objects.get_or_create(
                    watchlist=wl, security=sec
                )
                if item_created:
                    added_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully prepared demo user '{username}' (password: '{password}') with {wl.items.count()} watchlist items."
            )
        )
