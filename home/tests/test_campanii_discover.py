"""Teste descoperire campanii sterilizare (mock search — fără rețea)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from home.campanii_discover import (
    CampanieCandidate,
    build_queries,
    discover_for_judet,
    empty_campanii_judete,
    is_junk_campaign_url,
    parse_campaign_dates,
    write_candidates_csv,
)
from home.campanii_discover_publish import classify_candidate, upsert_candidates
from home.campanii_ro import CampaniiJudet
from home.models import CampanieDiscoverHit, CampanieSterilizare
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import date, timedelta

User = get_user_model()


class CampaniiDiscoverTests(TestCase):
    def test_build_queries_include_smeura(self):
        j = CampaniiJudet(name="Ilfov", slug="ilfov", code="IF", main_cities=("Buftea",))
        qs = build_queries(j, include_smeura=True)
        self.assertTrue(any("site:smeura.com" in q for q in qs))
        self.assertTrue(any("Ilfov" in q for q in qs))

    def test_junk_and_dates(self):
        self.assertTrue(is_junk_campaign_url("https://smeura.com/"))
        self.assertFalse(is_junk_campaign_url("https://smeura.com/event/livadaarad/"))
        self.assertTrue(is_junk_campaign_url("https://www.litoralulromanesc.ro/hotel_x.htm"))
        dates = parse_campaign_dates("Aug 14, 2026 · Primăria Sebeș campanie sterilizare")
        self.assertIn(date(2026, 8, 14), dates)

    def test_classify_and_upsert(self):
        cand = CampanieCandidate(
            judet="Sibiu",
            judet_slug="sibiu",
            judet_code="SB",
            title="Campanie sterilizare gratuită Sibiu din 3 august 2026",
            url="https://example-news.ro/sterilizare-sibiu-2026",
            snippet="Începând cu 3 august 2026, în limita fondurilor disponibile.",
            source="ddg",
            query="q",
            guessed_dates="03.08.2026",
            image_url="https://example-news.ro/afis.jpg",
        )
        meta = classify_candidate(cand, min_date=date(2026, 8, 1), today=date(2026, 9, 14))
        self.assertEqual(meta["status"], CampanieDiscoverHit.STATUS_NEW)
        ups = upsert_candidates([cand], min_date=date(2026, 8, 1), fetch_images=False)
        self.assertEqual(ups["created"], 1)
        hit = CampanieDiscoverHit.objects.get()
        self.assertEqual(hit.status, CampanieDiscoverHit.STATUS_NEW)
        self.assertTrue(hit.date_start)

    def test_empty_judete_excludes_visible_campaign(self):
        user = User.objects.create_user("camp_disc", "c@test.local", "x")
        photo = SimpleUploadedFile("c.jpg", b"\xff\xd8\xff\xd9", content_type="image/jpeg")
        CampanieSterilizare.objects.create(
            user=user,
            judet="Ilfov",
            judet_slug="ilfov",
            localitate="Buftea",
            species_dogs=True,
            species_cats=False,
            date_start=date.today(),
            date_end=date.today() + timedelta(days=5),
            photo=photo,
        )
        empty = empty_campanii_judete()
        slugs = {j.slug for j in empty}
        self.assertNotIn("ilfov", slugs)
        self.assertGreaterEqual(len(empty), 1)

    @patch("home.campanii_discover._web_search")
    def test_discover_for_judet_filters(self, mock_search):
        mock_search.return_value = [
            {
                "title": "Campanie sterilizare gratuită Buftea",
                "body": "Sterilizare câini și pisici în Ilfov, septembrie 2026.",
                "href": "https://example-news.ro/sterilizare-ilfov",
                "source": "ddg",
            },
            {
                "title": "Rețetă de prăjitură",
                "body": "Fără legătură",
                "href": "https://example-news.ro/prajitura",
                "source": "ddg",
            },
            {
                "title": "Sterilizare pe eu-adopt",
                "body": "campanie",
                "href": "https://eu-adopt.ro/publicitate/campanii/ilfov/",
                "source": "ddg",
            },
        ]
        j = CampaniiJudet(name="Ilfov", slug="ilfov", code="IF", main_cities=("Buftea",))
        rows = discover_for_judet(j, sleep_s=0, include_smeura=False, fetch_images=False)
        self.assertEqual(len(rows), 1)
        self.assertIn("sterilizare-ilfov", rows[0].url)

    def test_write_csv(self):
        rows = [
            CampanieCandidate(
                judet="Ilfov",
                judet_slug="ilfov",
                judet_code="IF",
                title="Test",
                url="https://example.ro/x",
                snippet="s",
                source="ddg",
                query="q",
            )
        ]
        path = Path(f"database/exports/_test_campanii_discover_{timezone.now():%H%M%S}.csv")
        write_candidates_csv(path, rows)
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("example.ro/x", text)
        path.unlink(missing_ok=True)

    @patch("home.campanii_discover.discover_empty_judete")
    def test_management_command(self, mock_disc):
        mock_disc.return_value = [
            CampanieCandidate(
                judet="Ilfov",
                judet_slug="ilfov",
                judet_code="IF",
                title="Campanie X",
                url="https://example.ro/camp",
                snippet="sterilizare",
                source="ddg",
                query="q",
            )
        ]
        out = Path("database/exports/_test_cmd_campanii_discover.csv")
        call_command(
            "discover_campanii_sterilizare",
            "--judet",
            "ilfov",
            "--out",
            str(out),
        )
        self.assertTrue(out.is_file())
        out.unlink(missing_ok=True)
