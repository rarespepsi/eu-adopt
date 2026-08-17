"""
Mod PRE-LAUNCH (EUADOPT_PRELAUNCH_MODE): acces anonim restricționat.
Rulează: python manage.py test home.tests.test_prelaunch
"""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import AnimalListing, StaffOnboardingLead

User = get_user_model()


@override_settings(PRELAUNCH_MODE=False)
class PrelaunchDisabledTests(TestCase):
    def test_anonymous_can_view_home(self):
        c = Client()
        r = c.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_anonymous_can_view_signup(self):
        c = Client()
        r = c.get(reverse("signup_choose_type"))
        self.assertEqual(r.status_code, 200)


@override_settings(PRELAUNCH_MODE=True, POPULATION_ONBOARDING_ENABLED=False)
class PrelaunchEnabledTests(TestCase):
    def setUp(self):
        u = uuid.uuid4().hex[:10]
        self.user = User.objects.create_user(
            username=f"prelaunch_{u}",
            email=f"prelaunch_{u}@test.local",
            password="Prelaunch_Pass12",
        )
        self.user.is_active = True
        self.user.save()

    def test_anonymous_only_home_public(self):
        """HOME + harta Campanii anonime; PT / Servicii / Shop cer login."""
        c = Client()
        self.assertEqual(c.get(reverse("home")).status_code, 200)
        r_camp = c.get(reverse("publicitate_campanii_ro"))
        self.assertEqual(r_camp.status_code, 200)
        self.assertContains(r_camp, "Campanii gratuite de sterilizare")
        r_judet = c.get(reverse("publicitate_campanii_judet", kwargs={"judet_slug": "neamt"}))
        self.assertEqual(r_judet.status_code, 200)
        for name in ("pets_all", "servicii", "shop", "transport"):
            r = c.get(reverse(name))
            self.assertEqual(r.status_code, 302, msg=name)
            self.assertIn("/login/", r.url or "", msg=name)

    def test_anonymous_pet_ficha_accessible(self):
        listing = AnimalListing.objects.create(
            owner=self.user,
            name="Rex",
            species="dog",
            is_published=True,
        )
        c = Client()
        r = c.get(reverse("pets_single", args=[listing.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Rex")
        self.assertContains(r, "VREAU SĂ ADOPT")

    def test_anonymous_pets_p2_more_still_blocked(self):
        c = Client()
        r = c.get("/pets/p2-more/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_anonymous_signup_choose_type_allowed(self):
        c = Client()
        r = c.get(reverse("signup_choose_type"))
        self.assertEqual(r.status_code, 200)

    def test_anonymous_signup_pf_allowed(self):
        c = Client()
        r = c.get(reverse("signup_pf"))
        self.assertEqual(r.status_code, 200)

    def test_login_page_accessible(self):
        c = Client()
        r = c.get(reverse("login"))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"PRE-LAUNCH", r.content)

    def test_login_page_has_no_site_navbar(self):
        """Intra: fără A0 / hamburger — doar formular login (+ panouri pre-lansare pe desktop)."""
        c = Client()
        r = c.get(reverse("login"))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'id="A0"', r.content)
        self.assertNotIn(b"a0-hamburger", r.content)
        self.assertNotIn(b'id="menu_wrap"', r.content)

    def test_signup_pf_post_with_invite_in_session_allowed(self):
        """POST formular PF fără ?inv= în URL, dar cu token în sesiune (după GET cu inv)."""
        lead = StaffOnboardingLead.objects.create(
            email=f"pf_inv_{uuid.uuid4().hex[:8]}@test.local",
            display_name="Test PF Inv",
            account_kind=StaffOnboardingLead.KIND_PF,
            status=StaffOnboardingLead.ST_READY,
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
            invite_email_last_sent_at=timezone.now(),
        )
        token = lead.consent_invite_token
        c = Client()
        r_get = c.get(f"{reverse('signup_pf')}?inv={token}")
        self.assertEqual(r_get.status_code, 200)
        r_post = c.post(
            reverse("signup_pf"),
            {
                "first_name": "Ana",
                "last_name": "Test",
                "email": lead.email,
                "phone_country": "+40",
                "phone": "712345678",
                "judet": "Neamț",
                "oras": "Piatra-Neamț",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
                "accept_termeni": "on",
                "accept_gdpr": "on",
            },
        )
        self.assertEqual(r_post.status_code, 302)
        self.assertIn(reverse("signup_verificare_sms"), r_post.url)
        self.assertNotIn("/login/", r_post.url)

    def test_login_shows_signup_link_on_ro_prelaunch(self):
        """Pe .ro, Creează cont e vizibil și în prelaunch (nu doar invitați email)."""
        c = Client()
        r = c.get(reverse("login"))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'class="login-links"', r.content)
        self.assertContains(r, "Creează cont")
        self.assertContains(r, reverse("signup_choose_type"))

    def test_forgot_password_accessible(self):
        c = Client()
        r = c.get(reverse("forgot_password"))
        self.assertEqual(r.status_code, 200)

    def test_activation_status_accessible(self):
        c = Client()
        r = c.get(reverse("signup_check_activation_status"))
        self.assertEqual(r.status_code, 200)

    def test_authenticated_user_can_view_home(self):
        c = Client()
        c.login(username=self.user.username, password="Prelaunch_Pass12")
        r = c.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_logout_redirects_to_login(self):
        c = Client()
        c.login(username=self.user.username, password="Prelaunch_Pass12")
        r = c.get(reverse("logout"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)
        # HOME rămâne public; PT cere login
        self.assertEqual(c.get(reverse("home")).status_code, 200)
        r_pt = c.get(reverse("pets_all"))
        self.assertEqual(r_pt.status_code, 302)
        self.assertIn("/login/", r_pt.url)


@override_settings(PRELAUNCH_MODE=True)
class PrelaunchFirstHintI18nTests(SimpleTestCase):
    def setUp(self):
        from home.eu_ui_labels import _load_i18n_packs

        _load_i18n_packs.cache_clear()

    def _hint(self, url_name: str, *, host_lang: str | None):
        from home.prelaunch_soft_lock import prelaunch_first_hint_for_url_name

        req = RequestFactory().get("/")
        if host_lang:
            req.eu_site_active = True
            req.eu_site_lang = host_lang
        else:
            req.eu_site_active = False
        return prelaunch_first_hint_for_url_name(url_name, request=req)

    def test_pt_hint_follows_site_language(self):
        self.assertIn("Find a friend", self._hint("pets_all", host_lang="en"))
        self.assertIn("Finde einen Freund", self._hint("pets_all", host_lang="de"))
        self.assertIn("Encuentra un amigo", self._hint("pets_all", host_lang="es"))
        self.assertIn("Trouver un ami", self._hint("pets_all", host_lang="fr"))
        self.assertIn("răsfoiește", self._hint("pets_all", host_lang=None))
        self.assertNotIn("răsfoiește", self._hint("pets_all", host_lang="de"))

    def test_login_prelaunch_panels_follow_site_language(self):
        from home.eu_ui_labels import eu_or_ro

        req = RequestFactory().get("/login/")
        req.eu_site_active = True
        req.eu_site_lang = "de"
        self.assertIn("Tierheimen", eu_or_ro(req, "login_pre_p1", "RO"))
        req.eu_site_lang = "es"
        self.assertIn("refugios", eu_or_ro(req, "login_pre_p1", "RO"))
        req.eu_site_active = False
        self.assertIn("adăposturi", eu_or_ro(req, "login_pre_p1", "EU-Adopt este o platformă dedicată adopțiilor responsabile și colaborării dintre adăposturi, asociații, cabinete veterinare, magazine, transportatori și alte servicii dedicate animalelor."))
