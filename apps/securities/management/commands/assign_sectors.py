"""Management command to assign sectors to securities from NEPSE ticker info."""

import logging
import time

from django.core.management.base import BaseCommand

from apps.sectors.models import Sector
from apps.securities.models import Security
from integrations.nepse import NepseClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Assign sectors to securities by fetching ticker info from NEPSE."

    def handle(self, *args, **options):
        client = NepseClient()
        securities = Security.objects.filter(sector__isnull=True)
        total = securities.count()
        self.stdout.write(f"Processing {total} securities without sectors...")

        # Build sector lookup by description
        sector_map = {}
        for s in Sector.objects.all():
            sector_map[s.name.lower().strip()] = s
            if s.display_name:
                sector_map[s.display_name.lower().strip()] = s

        updated = 0
        failed = 0
        for i, sec in enumerate(securities):
            try:
                data = client.get_ticker_info(sec.symbol)
                company = data.get("company", {}) if isinstance(data, dict) else {}
                company_id = company.get("companyId", {}) if isinstance(company, dict) else {}
                sector_master = company_id.get("sectorMaster", {}) if isinstance(company_id, dict) else {}
                sector_desc = sector_master.get("sectorDescription", "") if isinstance(sector_master, dict) else ""

                if sector_desc:
                    normalized = sector_desc.lower().strip()
                    sector_obj = sector_map.get(normalized)
                    if sector_obj:
                        sec.sector = sector_obj
                        sec.save(update_fields=["sector"])
                        updated += 1
                    else:
                        self.stdout.write(f"  Unknown sector '{sector_desc}' for {sec.symbol}")
                        failed += 1
                else:
                    failed += 1

                if (i + 1) % 50 == 0:
                    self.stdout.write(f"  Progress: {i + 1}/{total} (updated: {updated})")
                time.sleep(0.1)  # Rate limit
            except Exception as e:
                logger.warning("Failed to get ticker info for %s: %s", sec.symbol, e)
                failed += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done: updated={updated}, failed={failed}, total={total}"
        ))
