"""
Carte puncte 21–29 (signup), 115–126 (Reclama), 127–128 (admin/media), 129–135 (transversal).
"""

import uuid
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.signing import SignatureExpired
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import AnimalListing, PromoA2Order

User = get_user_model()


def _uniq():
    return uuid.uuid4().hex[:10]


class Carte21VerifyEmailEdgeCasesTests(TestCase):
    """21: link activare lipsă / invalid / expirat → redirect alegere tip cu query."""

    def test_21_no_token_redirects_link_invalid(self):
        r = Client().get(reverse("signup_verify_email"))
        self.assertEqual(r.status_code, 302)
        url = r.url or ""
        self.assertIn(reverse("signup_choose_type").rstrip("/"), url.replace("http://testserver", ""))
        self.assertIn("link_invalid", url)

    def test_21_bad_token_redirects_link_invalid(self):
        r = Client().get(reverse("signup_verify_email"), {"token": "not-valid-base64"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("link_invalid", r.url or "")

    def test_21_expired_token_redirects_link_expirat(self):
        with mock.patch(
            "django.core.signing.TimestampSigner.unsign",
            side_effect=SignatureExpired("expired"),
        ):
            r = Client().get(reverse("signup_verify_email"), {"token": "dummy"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("link_expirat", r.url or "")


class Carte22_25OrganizatieTests(TestCase):
    """22–25: pagină ONG — GET + validări + POST valid → SMS."""

    def test_22_signup_org_get_200(self):
        r = Client().get(reverse("signup_organizatie"))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("denumire", body.lower())
        self.assertIn("cui", body.lower())

    def test_23_legal_checkboxes_required(self):
        u = _uniq()
        r = Client().post(
            reverse("signup_organizatie"),
            {
                "denumire": "Org X",
                "denumire_societate": "SRL X",
                "cui": f"RO{u[:8]}",
                "cui_cu_ro": "da",
                "pers_contact": "Ion",
                "email": f"org_{u}@carte-test.local",
                "telefon": f"+40741{u[:7].zfill(7)}",
                "judet": "Cluj",
                "oras": "Cluj-Napoca",
                "adresa_firma": "Str. Memorandumului 28, Cluj-Napoca",
                "parola1": "ParolaOrg12",
                "parola2": "ParolaOrg12",
                "is_public_shelter": "yes",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("termenii", r.content.decode("utf-8").lower())

    def test_24_public_shelter_choice_required(self):
        u = _uniq()
        r = Client().post(
            reverse("signup_organizatie"),
            {
                "denumire": "Org Y",
                "denumire_societate": "SRL Y",
                "cui": f"RO{u[:8]}",
                "cui_cu_ro": "da",
                "pers_contact": "Ion",
                "email": f"org2_{u}@carte-test.local",
                "telefon": f"+40742{u[:7].zfill(7)}",
                "judet": "Cluj",
                "oras": "Cluj-Napoca",
                "adresa_firma": "Str. Memorandumului 28, Cluj-Napoca",
                "parola1": "ParolaOrg12",
                "parola2": "ParolaOrg12",
                "accept_termeni_org": "on",
                "accept_gdpr_org": "on",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("adăpost public", r.content.decode("utf-8").lower())

    def test_25_valid_post_redirects_sms(self):
        u = _uniq()
        r = Client().post(
            reverse("signup_organizatie"),
            {
                "denumire": "Org OK",
                "denumire_societate": "SRL OK",
                "cui": f"RO{u[:8]}",
                "cui_cu_ro": "da",
                "pers_contact": "Ion",
                "email": f"orgok_{u}@carte-test.local",
                "telefon": f"+40743{u[:7].zfill(7)}",
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


class Carte26_29ColaboratorGetTests(TestCase):
    """26–29: colaborator — GET formular + ?tip=transport (casetă capacitate)."""

    def test_26_28_collab_get_200(self):
        r = Client().get(reverse("signup_colaborator"))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("tip_partener", body.lower())
        self.assertIn("denumire", body.lower())

    def test_27_29_transport_tip_shows_capacity_block(self):
        r = Client().get(reverse("signup_colaborator"), {"tip": "transport"})
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        self.assertIn("Capacitate transport", body)
        self.assertIn("id_max_caini", body)
        self.assertIn("transport_national", body)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class Carte115_126ReclamaStaffTests(TestCase):
    """115–125: rute Reclama staff GET 200; 126 export rezumat promo."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username=f"st_{_uniq()}",
            email=f"st_{_uniq()}@carte-test.local",
            password="StaffCarte12!",
            is_staff=True,
            is_superuser=False,
        )

    def test_115_125_reclama_sections_200(self):
        c = Client()
        c.login(username=self.staff.username, password="StaffCarte12!")
        names = [
            "reclama_staff",
            "reclama_pt",
            "reclama_servicii",
            "reclama_transport",
            "reclama_shop",
            "reclama_mypet",
            "reclama_magazinul_meu",
            "reclama_i_love",
            "reclama_termeni",
            "reclama_contact",
            "reclama_mesaje",
        ]
        for name in names:
            r = c.get(reverse(name))
            self.assertEqual(r.status_code, 200, msg=name)

    def test_126_promo_export_redirects_staff(self):
        owner = User.objects.create_user(
            username=f"own_{_uniq()}",
            email=f"own_{_uniq()}@carte-test.local",
            password="OwnCarte12!",
        )
        pet = AnimalListing.objects.create(
            owner=owner,
            name="PromoPet",
            species="dog",
            is_published=True,
        )
        order = PromoA2Order.objects.create(
            pet=pet,
            payer_user=owner,
            payer_email=owner.email,
            status=PromoA2Order.STATUS_PAID,
            start_date=timezone.localdate(),
            starts_at=timezone.now(),
            ends_at=timezone.now() + timezone.timedelta(hours=6),
        )
        c = Client()
        c.login(username=self.staff.username, password="StaffCarte12!")
        r = c.post(reverse("reclama_promo_export_summary_now", args=[order.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("reclama_staff"), r.url or "")


class Carte127_128AdminMediaTests(TestCase):
    """127: Django admin accesibil staff; 128: rută media fără 500."""

    def test_127_admin_index_staff_200(self):
        u = User.objects.create_user(
            username=f"su_{_uniq()}",
            email=f"su_{_uniq()}@carte-test.local",
            password="AdminCarte12!",
            is_staff=True,
            is_superuser=True,
        )
        c = Client()
        c.login(username=u.username, password="AdminCarte12!")
        r = c.get("/admin/")
        self.assertEqual(r.status_code, 200)

    def test_128_media_path_no_server_error(self):
        r = Client().get("/media/__carte_probe__/missing.bin")
        self.assertLess(r.status_code, 500)


class Carte129_135TransversalTests(TestCase):
    """129–130: linkuri în pagini; 132 CSRF; 134 management command; 135 migrări aplicate."""

    def test_129_navbar_links_on_home(self):
        r = Client().get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        text = r.content.decode("utf-8")
        for path in ("/pets/", "/servicii/", "/shop/", "/transport/"):
            self.assertIn(path, text)

    def test_130_footer_legal_links(self):
        for view_name in ("home", "pets_all", "contact"):
            r = Client().get(reverse(view_name))
            self.assertEqual(r.status_code, 200)
            low = r.content.decode("utf-8").lower()
            self.assertTrue(
                "termeni" in low or "politic" in low or "gdpr" in low or "cookie" in low,
                msg=view_name,
            )

    def test_131_viewport_meta_on_home(self):
        r = Client().get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"viewport", r.content.lower())

    def test_132_post_without_csrf_returns_403_when_enforced(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("transport_submit"), {})
        self.assertEqual(r.status_code, 403)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_133_locmem_email_backend_configurable(self):
        from django.core import mail

        mail.send_mail("subj", "body", "from@test", ["to@test"])
        self.assertEqual(len(mail.outbox), 1)

    def test_134_expire_transport_jobs_runs(self):
        out = call_command("expire_transport_jobs", verbosity=0)
        self.assertIsNone(out)

    def test_135_no_pending_migrations(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.assertEqual(
            plan,
            [],
            msg="Există migrări neaplicate în mediul de test.",
        )
