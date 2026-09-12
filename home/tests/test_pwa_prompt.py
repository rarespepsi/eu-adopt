"""PWA: cookie după login + anunț App pe benzile EU *.3."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.pwa import PWA_LOGIN_PULSE_COOKIE
from home.views import (
    EU_STRIP_THANKS_LABEL,
    EU_STRIP_THANKS_MSG,
    PUB_STRIP_SEQ_P1,
    PUB_STRIP_SEQ_P3,
    PUB_STRIP_SEQ_S1,
    PUB_STRIP_SEQ_S7,
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


class CollaboratoriStripThanksTests(TestCase):
    def test_pt_strip_eu_cells_say_thanks(self):
        cells = _strip_cells_donatii_pt_or_servicii(
            "pt", _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P1)
        )
        eu = [c for c in cells if c.get("kind") == "eu"]
        self.assertEqual(len(eu), 4)
        for cell in eu:
            self.assertTrue(cell.get("eu_thanks_strip"), cell.get("code"))
            self.assertEqual(cell.get("eu_thanks_label"), EU_STRIP_THANKS_LABEL)
            self.assertEqual(cell.get("eu_thanks_msg"), EU_STRIP_THANKS_MSG)
            self.assertFalse(cell.get("eu_pwa_strip"))
            self.assertFalse(cell.get("eu_sms_strip_href"))

    def test_pt_p3_and_servicii_eu_cells_say_thanks(self):
        cases = (
            ("pt", PUB_STRIP_SEQ_P3, 4),
            ("servicii", PUB_STRIP_SEQ_S1, 4),
            ("servicii", PUB_STRIP_SEQ_S7, 4),
        )
        for section, seq, n_eu in cases:
            cells = _strip_cells_donatii_pt_or_servicii(section, _enrich_pub_strip_sequence(section, seq))
            eu = [c for c in cells if c.get("kind") == "eu"]
            self.assertEqual(len(eu), n_eu, section)
            self.assertTrue(all(c.get("eu_thanks_strip") for c in eu), section)
