"""Tests for Security model."""
import datetime
import decimal

import pytest
from django.db import IntegrityError

from apps.sectors.models import Sector
from apps.securities.models import Security


@pytest.mark.django_db
class TestSecurityModel:
    def _make_sector(self, **kwargs):
        defaults = {"nepse_id": 1, "name": "Commercial Banks"}
        defaults.update(kwargs)
        return Sector.objects.create(**defaults)

    def test_create_security(self):
        sector = self._make_sector()
        security = Security.objects.create(
            nepse_id=58,
            symbol="NABIL",
            company_name="Nabil Bank Limited",
            sector=sector,
            security_type="Ordinary Share",
            listing_date=datetime.date(2002, 1, 1),
            paid_up_value=decimal.Decimal("100.00"),
            face_value=decimal.Decimal("100.00"),
        )
        assert security.pk is not None
        assert security.nepse_id == 58
        assert security.symbol == "NABIL"
        assert security.company_name == "Nabil Bank Limited"
        assert security.sector == sector
        assert security.security_type == "Ordinary Share"
        assert security.listing_date == datetime.date(2002, 1, 1)
        assert security.paid_up_value == decimal.Decimal("100.00")
        assert security.face_value == decimal.Decimal("100.00")

    def test_str_representation(self):
        sector = self._make_sector()
        security = Security.objects.create(
            nepse_id=58,
            symbol="NABIL",
            company_name="Nabil Bank Limited",
            sector=sector,
        )
        assert str(security) == "NABIL - Nabil Bank Limited"

    def test_symbol_unique(self):
        sector = self._make_sector()
        Security.objects.create(
            nepse_id=58, symbol="NABIL", company_name="Nabil Bank", sector=sector
        )
        with pytest.raises(IntegrityError):
            Security.objects.create(
                nepse_id=59, symbol="NABIL", company_name="Other", sector=sector
            )

    def test_nepse_id_unique(self):
        sector = self._make_sector()
        Security.objects.create(
            nepse_id=58, symbol="NABIL", company_name="Nabil Bank", sector=sector
        )
        with pytest.raises(IntegrityError):
            Security.objects.create(
                nepse_id=58, symbol="NABIL2", company_name="Other", sector=sector
            )

    def test_sector_nullable(self):
        security = Security.objects.create(
            nepse_id=58, symbol="NABIL", company_name="Nabil Bank", sector=None
        )
        assert security.sector is None

    def test_optional_fields_nullable(self):
        security = Security.objects.create(
            nepse_id=58,
            symbol="NABIL",
            company_name="Nabil Bank",
            listing_date=None,
            paid_up_value=None,
            face_value=None,
        )
        assert security.listing_date is None
        assert security.paid_up_value is None
        assert security.face_value is None

    def test_security_type_blank_default(self):
        security = Security.objects.create(
            nepse_id=58, symbol="NABIL", company_name="Nabil Bank"
        )
        assert security.security_type == ""

    def test_ordering(self):
        sector = self._make_sector()
        Security.objects.create(nepse_id=2, symbol="ZSEC", company_name="Z", sector=sector)
        Security.objects.create(nepse_id=1, symbol="ASEC", company_name="A", sector=sector)
        symbols = list(Security.objects.values_list("symbol", flat=True))
        assert symbols == ["ASEC", "ZSEC"]

    def test_sector_relationship(self):
        sector = self._make_sector()
        Security.objects.create(nepse_id=1, symbol="A", company_name="A", sector=sector)
        Security.objects.create(nepse_id=2, symbol="B", company_name="B", sector=sector)
        assert sector.securities.count() == 2

    def test_sector_set_null_on_delete(self):
        sector = self._make_sector()
        Security.objects.create(nepse_id=1, symbol="A", company_name="A", sector=sector)
        sector.delete()
        security = Security.objects.get(nepse_id=1)
        assert security.sector is None
