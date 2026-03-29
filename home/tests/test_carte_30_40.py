"""
Carte puncte 30–40: colaborator (validări), apoi pagini publice GET 200 (fără 500).
"""

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from home.models import AnimalListing

User = get_user_model()


def _uniq():
    return uuid.uuid4().hex[:10]


def _collab_post_transport_no_checks(u: str):
    """Colaborator transport fără național/internațional — restul câmpuri valide."""
    return {
        "tip_partener": "transport",
        "denumire": "Cabinet Test",
        "denumire_societate": "SRL Test Transport",
        "cui": f"RO{u[:8]}",
        "cui_cu_ro": "da",
        "pers_contact": "Contact",
        "judet": "Neamț",
        "oras": "Piatra Neamț",
        "email": f"col_tr_{u}@carte-test.local",
        "telefon": f"+40752{u[:7].zfill(7)}",
        "parola1": "ParolaColab12",
        "parola2": "ParolaColab12",
        "accept_termeni_col": "on",
        "accept_gdpr_col": "on",
        "max_caini": "2",
        "max_pisici": "2",
    }


def _collab_post_cabinet_ok(u: str):
    return {
        "tip_partener": "cabinet",
        "denumire": "Cabinet Vet",
        "denumire_societate": "SRL Cabinet",
        "cui": f"RO{u[:8]}",
        "cui_cu_ro": "da",
        "pers_contact": "Dr. Test",
        "judet": "Cluj",
        "oras": "Cluj-Napoca",
        "email": f"col_cb_{u}@carte-test.local",
        "telefon": f"+40753{u[:7].zfill(7)}",
        "parola1": "ParolaColab12",
        "parola2": "ParolaColab12",
        "accept_termeni_col": "on",
        "accept_gdpr_col": "on",
    }


class Carte30_32CollaboratorTests(TestCase):
    """30–32: validări formular colaborator + redirect SMS."""

    def test_30_submit_without_partner_type_shows_error(self):
        c = Client()
        r = c.post(
            reverse("signup_colaborator"),
            {
                "denumire": "X",
                "denumire_societate": "Y",
                "cui": "RO123",
                "cui_cu_ro": "da",
                "pers_contact": "Z",
                "judet": "Alba",
                "oras": "Alba Iulia",
                "email": f"e_{_uniq()}@t.local",
                "telefon": "+40700000001",
                "parola1": "ParolaCol12",
                "parola2": "ParolaCol12",
                "accept_termeni_col": "on",
                "accept_gdpr_col": "on",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("Trebuie să alegi tipul de partener", r.content.decode("utf-8"))

    def test_31_transport_without_national_or_international_error(self):
        u = _uniq()
        c = Client()
        r = c.post(reverse("signup_colaborator"), _collab_post_transport_no_checks(u))
        self.assertEqual(r.status_code, 200)
        self.assertIn("TRANSPORT NAȚIONAL", r.content.decode("utf-8"))

    def test_32_valid_collaborator_redirects_to_sms(self):
        u = _uniq()
        c = Client()
        r = c.post(reverse("signup_colaborator"), _collab_post_cabinet_ok(u))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_verificare_sms"), r.url or "")


class Carte33_40PublicPagesTests(TestCase):
    """33–40: GET anonim — pagini principale și shop (conținut minim / status)."""

    def test_33_home_200(self):
        r = Client().get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_34_pets_with_filters_200(self):
        r = Client().get(reverse("pets_all"), {"judet": "Cluj", "marime": "medie"})
        self.assertEqual(r.status_code, 200)
        self.assertLess(len(r.content), 50 * 1024 * 1024)

    def test_35_pets_go_no_500(self):
        r = Client().get(reverse("pets_all"), {"go": "999998"})
        self.assertLess(r.status_code, 500)

    def test_36_pets_single_published_200(self):
        owner = User.objects.create_user(
            username=f"o{_uniq()}",
            email=f"o{_uniq()}@t.local",
            password="PassTest12345",
        )
        listing = AnimalListing.objects.create(
            owner=owner,
            name="CartePet",
            species="dog",
            is_published=True,
        )
        r = Client().get(reverse("pets_single", args=[listing.pk]))
        self.assertEqual(r.status_code, 200)

    def test_37_servicii_200(self):
        r = Client().get(reverse("servicii"))
        self.assertEqual(r.status_code, 200)

    def test_38_shop_200(self):
        r = Client().get(reverse("shop"))
        self.assertEqual(r.status_code, 200)

    def test_39_shop_comanda_personalizate_200(self):
        r = Client().get(reverse("shop_comanda_personalizate"))
        self.assertEqual(r.status_code, 200)

    def test_40_shop_magazin_foto_200(self):
        r = Client().get(reverse("shop_magazin_foto"))
        self.assertEqual(r.status_code, 200)
