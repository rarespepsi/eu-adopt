"""
Smoke / regresii pentru „Alege pe hartă” (Google Maps Places).

Nu apelează Google real: verifică sursa template + HTML randat,
ca să prindem din nou tipurile Places invalide (establishment+geocode)
care opresc tot JS-ul înainte de legarea butonului de hartă.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.test import Client, TestCase, override_settings
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGNUP_MAPS_SCRIPT = (
    REPO_ROOT / "templates" / "anunturi" / "includes" / "signup_adresa_google_maps_script.html"
)
TRANSPORT_HTML = REPO_ROOT / "templates" / "anunturi" / "transport.html"

# Pattern interzis: tipuri Places mixte (Table 2 + Table 3) — INVALID_REQUEST la Google.
_FORBIDDEN_MIXED_TYPES = re.compile(
    r"types\s*:\s*\[\s*['\"]establishment['\"]\s*,\s*['\"]geocode['\"]\s*\]"
    r"|types\s*:\s*\[\s*['\"]geocode['\"]\s*,\s*['\"]establishment['\"]\s*\]",
    re.IGNORECASE,
)


class GoogleMapsPickerSourceTests(TestCase):
    def test_signup_maps_script_has_no_mixed_places_types(self):
        src = SIGNUP_MAPS_SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(SIGNUP_MAPS_SCRIPT.is_file())
        self.assertIsNone(
            _FORBIDDEN_MIXED_TYPES.search(src),
            "signup maps: nu folosi types establishment+geocode împreună",
        )
        self.assertIn("safeAutocomplete", src)
        self.assertIn("document.body.appendChild(mapModal)", src)
        self.assertIn("componentRestrictions", src)

    def test_transport_maps_script_has_no_mixed_places_types(self):
        src = TRANSPORT_HTML.read_text(encoding="utf-8")
        self.assertTrue(TRANSPORT_HTML.is_file())
        self.assertIsNone(
            _FORBIDDEN_MIXED_TYPES.search(src),
            "transport maps: nu folosi types establishment+geocode împreună",
        )
        self.assertIn("safeAutocomplete", src)
        self.assertIn("document.body.appendChild(transportMapModal)", src)
        self.assertIn("selectedCountryCode", src)
        self.assertIn("setComponentRestrictions", src)


@override_settings(
    EUADOPT_GOOGLE_MAPS_API_KEY="AIzaSyTestKeyForMapsPickerRegression000",
    GOOGLE_MAPS_API_KEY="AIzaSyTestKeyForMapsPickerRegression000",
    PRELAUNCH_MODE=False,
)
class GoogleMapsPickerRenderTests(TestCase):
    def test_colaborator_signup_renders_map_pick_and_safe_script(self):
        c = Client()
        resp = c.get(reverse("signup_colaborator"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8", errors="replace")
        self.assertIn('id="signup_col_map_pick"', html)
        self.assertIn('id="signup_col_map_modal"', html)
        self.assertIn("safeAutocomplete", html)
        self.assertIn("document.body.appendChild(mapModal)", html)
        self.assertIsNone(_FORBIDDEN_MIXED_TYPES.search(html))
        self.assertIn("maps.googleapis.com/maps/api/js", html)

    def test_organizatie_signup_renders_map_pick(self):
        c = Client()
        resp = c.get(reverse("signup_organizatie"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8", errors="replace")
        self.assertIn('id="signup_org_map_pick"', html)
        self.assertIn('id="signup_org_map_modal"', html)
        self.assertIn("safeAutocomplete", html)
        self.assertIsNone(_FORBIDDEN_MIXED_TYPES.search(html))

    def test_transport_renders_map_pick_and_safe_script(self):
        c = Client()
        resp = c.get(reverse("transport"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8", errors="replace")
        self.assertIn('id="plecare_map_pick"', html)
        self.assertIn('id="sosire_map_pick"', html)
        self.assertIn('id="transportMapModal"', html)
        self.assertIn("safeAutocomplete", html)
        self.assertIn("document.body.appendChild(transportMapModal)", html)
        self.assertIn("selectedCountryCode", html)
        self.assertIsNone(_FORBIDDEN_MIXED_TYPES.search(html))

    @override_settings(
        EUADOPT_EU_PRODUCT_SKIN=True,
        EUADOPT_NON_RO_STAFF_ONLY=False,
        PRELAUNCH_MODE=False,
        EUADOPT_GOOGLE_MAPS_API_KEY="AIzaSyTestKeyForMapsPickerRegression000",
        GOOGLE_MAPS_API_KEY="AIzaSyTestKeyForMapsPickerRegression000",
    )
    def test_eu_transport_has_destination_country_and_country_aware_maps(self):
        c = Client(HTTP_HOST="euadopt.com")
        resp = c.get(reverse("transport"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8", errors="replace")
        self.assertIn('id="tw-country"', html)
        self.assertIn("selectedCountryCode", html)
        self.assertIn("setComponentRestrictions", html)
        self.assertIn("DESTINATION COUNTRY", html)
