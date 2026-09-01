"""Tests for Sector model."""
import pytest
from django.db import IntegrityError

from apps.sectors.models import Sector


@pytest.mark.django_db
class TestSectorModel:
    def test_create_sector(self):
        sector = Sector.objects.create(
            nepse_id=1,
            name="Commercial Banks",
            display_name="Commercial Banks",
        )
        assert sector.pk is not None
        assert sector.nepse_id == 1
        assert sector.name == "Commercial Banks"
        assert sector.display_name == "Commercial Banks"
        assert sector.created_at is not None
        assert sector.updated_at is not None

    def test_str_representation(self):
        sector = Sector.objects.create(nepse_id=1, name="Commercial Banks")
        assert str(sector) == "Commercial Banks"

    def test_nepse_id_unique(self):
        Sector.objects.create(nepse_id=1, name="Banks")
        with pytest.raises(IntegrityError):
            Sector.objects.create(nepse_id=1, name="Other Banks")

    def test_name_unique(self):
        Sector.objects.create(nepse_id=1, name="Banks")
        with pytest.raises(IntegrityError):
            Sector.objects.create(nepse_id=2, name="Banks")

    def test_display_name_blank_default(self):
        sector = Sector.objects.create(nepse_id=1, name="Banks")
        assert sector.display_name == ""

    def test_ordering(self):
        Sector.objects.create(nepse_id=2, name="Z Sector")
        Sector.objects.create(nepse_id=1, name="A Sector")
        sectors = list(Sector.objects.values_list("name", flat=True))
        assert sectors == ["A Sector", "Z Sector"]

    def test_verbose_name(self):
        assert Sector._meta.verbose_name == "Sector"
        assert Sector._meta.verbose_name_plural == "Sectors"
