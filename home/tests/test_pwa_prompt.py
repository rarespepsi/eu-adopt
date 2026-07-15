"""PWA: cookie după login + anunț App pe benzile EU *.3."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.donatii_constants import EUADOPT_PWA_STRIP_MSG
from home.pwa import PWA_LOGIN_PULSE_COOKIE
from home.views import (
    PUB_STRIP_SEQ_P1,
    PUB_STRIP_SEQ_S1,
    _enrich_pub_strip_sequence,
    _strip_cells_donatii_pt_or_servicii,
)

User = get_user_model()


class PwaLoginPulseTests(TestCase):
    def setUp(self):
        u = uuid.uuid4().hex[:8]
        self.user = User.objects.create_user(
            username=f"pwa_{u}",
            email=f"pwa_{u}@test.local",
            password="Secret12ab",
        )
        self.user.is_active = True
        self.user.save()

    @override_settings(
        PRELAUNCH_MODE=False,
        POPULATION_ONBOARDING_ENABLED=False,
    )
    def test_login_sets_pwa_pulse_cookie(self):
        c = Client()
        r = c.post("/login/", {"login": self.user.username, "password": "Secret12ab"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.cookies.get(PWA_LOGIN_PULSE_COOKIE).value, "1")


class PwaStripAnnouncementTests(TestCase):
    def test_pt_strip_eu_dot3_has_app_message(self):
        cells = _strip_cells_donatii_pt_or_servicii(
            "pt", _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P1)
        )
        pwa_cells = [c for c in cells if c.get("code") == "EUP1.3"]
        self.assertEqual(len(pwa_cells), 1)
        self.assertTrue(pwa_cells[0].get("eu_pwa_strip"))
        self.assertIn("MOBIL", pwa_cells[0].get("eu_pwa_strip_msg") or "")
        self.assertEqual(pwa_cells[0].get("eu_pwa_strip_msg"), EUADOPT_PWA_STRIP_MSG)

    def test_servicii_strip_eu_dot3_has_app_message(self):
        cells = _strip_cells_donatii_pt_or_servicii(
            "servicii", _enrich_pub_strip_sequence("servicii", PUB_STRIP_SEQ_S1)
        )
        pwa_cells = [c for c in cells if c.get("code") == "EUS1.3"]
        self.assertEqual(len(pwa_cells), 1)
        self.assertTrue(pwa_cells[0].get("eu_pwa_strip"))
