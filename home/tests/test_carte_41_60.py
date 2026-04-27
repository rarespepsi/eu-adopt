"""
Carte puncte 41–60: pagini publice, contact, publicitate (autorizare), legale, cont și editări.
"""

import uuid
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import AccountProfile, CollaboratorServiceOffer, UserProfile

User = get_user_model()

try:
    from PIL import Image
except ImportError:
    Image = None


def _tiny_jpeg_upload():
    if Image is None:
        raise RuntimeError("Pillow required for CollaboratorServiceOffer image tests")
    buf = BytesIO()
    Image.new("RGB", (1, 1), color=(200, 200, 200)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("offer.jpg", buf.read(), content_type="image/jpeg")


def _pf_user_with_profile(**kwargs):
    u = uuid.uuid4().hex[:8]
    email = kwargs.get("email") or f"pf_{u}@carte41.local"
    user = User.objects.create_user(
        username=f"user_{u}",
        email=email,
        password="Carte4141Test!",
    )
    acc = getattr(user, "account_profile", None)
    if acc:
        acc.role = AccountProfile.ROLE_PF
        acc.save()
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
    profile.phone = kwargs.get("phone", "+40 712345678")
    profile.judet = kwargs.get("judet", "Cluj")
    profile.oras = kwargs.get("oras", "Cluj-Napoca")
    profile.accept_termeni = True
    profile.accept_gdpr = True
    profile.save()
    return user


def _staff_user():
    u = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"staff_{u}",
        email=f"staff_{u}@carte41.local",
        password="StaffCarte41!",
        is_staff=True,
    )


def _collab_user_with_offer():
    u = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"collab_{u}",
        email=f"coll_{u}@carte41.local",
        password="CollCarte41!",
    )
    acc = getattr(user, "account_profile", None)
    if acc:
        acc.role = AccountProfile.ROLE_COLLAB
        acc.save()
    offer = CollaboratorServiceOffer.objects.create(
        collaborator=user,
        partner_kind=CollaboratorServiceOffer.PARTNER_KIND_CABINET,
        title=f"Ofertă test {u}",
        image=_tiny_jpeg_upload(),
        is_active=True,
    )
    return user, offer


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class Carte41_60Tests(TestCase):
    """Verificări automate carte 41–60 (fără modificare template-uri înghețate)."""

    # --- Partea C (41–47) ---

    def test_41_transport_200(self):
        r = Client().get(reverse("transport"))
        self.assertEqual(r.status_code, 200)

    def test_42_custi_200(self):
        r = Client().get(reverse("custi"))
        self.assertEqual(r.status_code, 200)

    def test_43_i_love_anon_redirects_to_login(self):
        r = Client().get(reverse("i_love"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r.url or "")

    def test_43_i_love_logged_in_200(self):
        c = Client()
        user = _pf_user_with_profile()
        c.login(username=user.username, password="Carte4141Test!")
        r = c.get(reverse("i_love"))
        self.assertEqual(r.status_code, 200)

    def test_44_oferte_parteneri_list_removed_404(self):
        r = Client().get("/oferte-parteneri/")
        self.assertEqual(r.status_code, 404)

    def test_45_public_offer_detail_200(self):
        _, offer = _collab_user_with_offer()
        r = Client().get(reverse("public_offer_detail", args=[offer.pk]))
        self.assertEqual(r.status_code, 200)

    def test_46_contact_200(self):
        r = Client().get(reverse("contact"))
        self.assertEqual(r.status_code, 200)

    def test_47_publicitate_anonymous_redirects_login(self):
        r = Client().get(reverse("publicitate_harta"))
        self.assertEqual(r.status_code, 302)

    def test_47_publicitate_staff_200(self):
        c = Client()
        s = _staff_user()
        c.login(username=s.username, password="StaffCarte41!")
        r = c.get(reverse("publicitate_harta"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "publicitate", status_code=200, html=False)

    def test_47_publicitate_collab_200(self):
        c = Client()
        user, _ = _collab_user_with_offer()
        c.login(username=user.username, password="CollCarte41!")
        r = c.get(reverse("publicitate_harta"))
        self.assertEqual(r.status_code, 200)

    def test_47_publicitate_cos_anonymous_redirects_login(self):
        r = Client().get(reverse("publicitate_cos"))
        self.assertEqual(r.status_code, 302)

    def test_47_publicitate_cos_collab_200_and_harta_links_cos(self):
        c = Client()
        user, _ = _collab_user_with_offer()
        c.login(username=user.username, password="CollCarte41!")
        r = c.get(reverse("publicitate_cos"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Detalii slot", status_code=200, html=False)
        self.assertContains(r, "pub-grid", status_code=200, html=False)
        self.assertContains(r, reverse("publicitate_harta"), status_code=200, html=False)
        rh = c.get(reverse("publicitate_harta"))
        self.assertEqual(rh.status_code, 200)
        self.assertContains(rh, reverse("publicitate_cos"), status_code=200, html=False)

    # --- Legale 48–54 ---

    def test_48_termeni_200(self):
        self.assertEqual(Client().get(reverse("termeni")).status_code, 200)

    def test_49_termeni_read_200(self):
        self.assertEqual(Client().get(reverse("termeni_read")).status_code, 200)

    def test_50_politica_confidentialitate_200(self):
        self.assertEqual(Client().get(reverse("politica_confidentialitate")).status_code, 200)

    def test_51_politici_altele_200(self):
        self.assertEqual(Client().get(reverse("politici_altele")).status_code, 200)

    def test_52_politica_cookie_200(self):
        self.assertEqual(Client().get(reverse("politica_cookie")).status_code, 200)

    def test_53_politica_servicii_platite_200(self):
        self.assertEqual(Client().get(reverse("politica_servicii_platite")).status_code, 200)

    def test_54_politica_moderare_200(self):
        self.assertEqual(Client().get(reverse("politica_moderare")).status_code, 200)

    # --- Partea D 55–60 ---

    def test_55_account_logged_in_200(self):
        c = Client()
        user = _pf_user_with_profile()
        c.login(username=user.username, password="Carte4141Test!")
        r = c.get(reverse("account"))
        self.assertEqual(r.status_code, 200)

    def test_56_account_edit_post_updates_names(self):
        c = Client()
        user = _pf_user_with_profile()
        c.login(username=user.username, password="Carte4141Test!")
        r = c.post(
            reverse("account_edit"),
            {
                "first_name": "NumeEditat",
                "last_name": "PrenumeEditat",
                "email": user.email,
                "phone_country": "+40",
                "phone": "712345678",
                "judet": "Cluj",
                "oras": "Cluj-Napoca",
                "accept_termeni": "on",
                "accept_gdpr": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("account"), r.url or "")
        user.refresh_from_db()
        self.assertEqual(user.first_name, "NumeEditat")

    def test_57_edit_verificare_sms_get_without_pending_redirects_account(self):
        c = Client()
        user = _pf_user_with_profile()
        c.login(username=user.username, password="Carte4141Test!")
        r = c.get(reverse("edit_verificare_sms"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("account"), r.url or "")

    def test_58_edit_check_email_200_when_logged_in(self):
        c = Client()
        user = _pf_user_with_profile()
        c.login(username=user.username, password="Carte4141Test!")
        r = c.get(reverse("edit_check_email"), {"email": user.email})
        self.assertEqual(r.status_code, 200)

    def test_59_edit_verify_email_no_token_redirects(self):
        c = Client()
        user = _pf_user_with_profile()
        c.login(username=user.username, password="Carte4141Test!")
        r = c.get(reverse("edit_verify_email"))
        self.assertEqual(r.status_code, 302)

    def test_60_username_change_post(self):
        c = Client()
        user = _pf_user_with_profile()
        c.login(username=user.username, password="Carte4141Test!")
        new_name = f"userrenamed{uuid.uuid4().hex[:6]}"
        r = c.post(reverse("account_edit_username"), {"username": new_name})
        self.assertEqual(r.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.username, new_name)
