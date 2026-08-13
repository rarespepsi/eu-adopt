"""Telefon partener: fără unicitate; mobil SAU fix; SMS doar cu mobil."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from home.models import UserProfile
from home.tests.test_carte_21_135 import _ro_mobile, _uniq
from home.views import _signup_partner_phone_error, _signup_pending_needs_sms

User = get_user_model()


class PartnerPhonePolicyTests(TestCase):
    def test_partner_phone_requires_mobile_or_landline(self):
        self.assertIn("mobil", _signup_partner_phone_error("", "", "", "").lower())
        self.assertEqual(
            _signup_partner_phone_error("0722123456", "", "", ""),
            "",
        )
        self.assertEqual(
            _signup_partner_phone_error("", "0256 212345", "0256", "212345"),
            "",
        )
        self.assertIn(
            "prefix",
            _signup_partner_phone_error("", "", "0256", "").lower(),
        )

    def test_needs_sms_only_with_mobile(self):
        self.assertTrue(_signup_pending_needs_sms({"role": "pf", "telefon": ""}))
        self.assertTrue(
            _signup_pending_needs_sms({"role": "org", "telefon": "0722123456"})
        )
        self.assertFalse(
            _signup_pending_needs_sms(
                {"role": "org", "telefon": "", "telefon_fix": "0256 212345"}
            )
        )

    def test_same_mobile_allowed_on_two_profiles(self):
        u1 = User.objects.create_user("p1_phone", "p1@t.local", "ParolaTest12")
        u2 = User.objects.create_user("p2_phone", "p2@t.local", "ParolaTest12")
        UserProfile.objects.create(user=u1, phone="+40 722123456")
        UserProfile.objects.create(user=u2, phone="+40 722123456")
        self.assertEqual(
            UserProfile.objects.filter(phone__icontains="722123456").count(),
            2,
        )

    def test_org_landline_only_skips_sms_goes_check_email(self):
        u = _uniq()
        r = Client().post(
            reverse("signup_organizatie"),
            {
                "denumire": "Org Fix",
                "denumire_societate": "SRL Fix",
                "cui": f"RO{u[:8]}",
                "cui_cu_ro": "da",
                "pers_contact": "Ion",
                "email": f"orgfix_{u}@carte-test.local",
                "telefon": "",
                "telefon_fix_prefix": "0264",
                "telefon_fix_nr": "123456",
                "judet": "Cluj",
                "oras": "Cluj-Napoca",
                "adresa_firma": "Str. Memorandumului 28, Cluj-Napoca",
                "parola1": "ParolaOrg12",
                "parola2": "ParolaOrg12",
                "accept_termeni_org": "on",
                "accept_gdpr_org": "on",
                "email_opt_in_org": "on",
                "is_public_shelter": "no",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_pf_check_email"), r.url or "")
        self.assertNotIn(reverse("signup_verificare_sms"), r.url or "")
        user = User.objects.get(email=f"orgfix_{u}@carte-test.local")
        prof = UserProfile.objects.get(user=user)
        self.assertEqual((prof.phone or "").strip(), "")
        self.assertIn("0264", prof.phone_landline or "")

    def test_org_mobile_still_goes_sms(self):
        u = _uniq()
        r = Client().post(
            reverse("signup_organizatie"),
            {
                "denumire": "Org Mob",
                "denumire_societate": "SRL Mob",
                "cui": f"RO{u[:8]}",
                "cui_cu_ro": "da",
                "pers_contact": "Ion",
                "email": f"orgmob_{u}@carte-test.local",
                "telefon": _ro_mobile(u, "744"),
                "judet": "Cluj",
                "oras": "Cluj-Napoca",
                "adresa_firma": "Str. Memorandumului 28, Cluj-Napoca",
                "parola1": "ParolaOrg12",
                "parola2": "ParolaOrg12",
                "accept_termeni_org": "on",
                "accept_gdpr_org": "on",
                "email_opt_in_org": "on",
                "is_public_shelter": "no",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_verificare_sms"), r.url or "")
