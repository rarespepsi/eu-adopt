"""
Carte puncte 61–100: MyPet, adopție, promo A2, magazin colaborator, mesaje, transport, wishlist.
"""

import uuid
from datetime import timedelta
from io import BytesIO
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.signing import TimestampSigner
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.data import DEMO_DOGS
from home.models import (
    AccountProfile,
    AdoptionRequest,
    AnimalListing,
    CollaboratorServiceOffer,
    PetMessage,
    UserProfile,
)

User = get_user_model()

try:
    from PIL import Image
except ImportError:
    Image = None


def _tiny_jpeg(name="x.jpg"):
    if Image is None:
        raise RuntimeError("Pillow required")
    buf = BytesIO()
    Image.new("RGB", (4, 4), color=(100, 150, 200)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


def _pf_user(suffix=None):
    u = suffix or uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"pf_{u}",
        email=f"pf_{u}@t61.local",
        password="Test61_PF_pass!",
    )
    ap = getattr(user, "account_profile", None)
    if ap:
        ap.role = AccountProfile.ROLE_PF
        ap.save()
    prof, _ = UserProfile.objects.get_or_create(user=user, defaults={})
    prof.phone = "+40 711222333"
    prof.judet = "Cluj"
    prof.oras = "Cluj-Napoca"
    prof.accept_termeni = True
    prof.accept_gdpr = True
    prof.save()
    return user


def _collab_cabinet_user():
    u = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"col_{u}",
        email=f"col_{u}@t61.local",
        password="Test61_Col_pass!",
    )
    ap = getattr(user, "account_profile", None)
    if ap:
        ap.role = AccountProfile.ROLE_COLLAB
        ap.save()
    prof, _ = UserProfile.objects.get_or_create(user=user, defaults={})
    prof.collaborator_type = "cabinet"
    prof.company_judet = "Cluj"
    prof.judet = "Cluj"
    prof.company_display_name = "Cabinet Test"
    prof.save()
    return user


def _published_pet(owner, name="RexTest"):
    return AnimalListing.objects.create(
        owner=owner,
        name=name,
        species="dog",
        is_published=True,
        county="Cluj",
        city="Cluj-Napoca",
    )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class Carte61_80Tests(TestCase):
    """Carte 61–80: MyPet, promo A2, mesaje, adopție, bonus, email owner."""

    def test_61_upload_avatar_json_ok(self):
        user = _pf_user()
        c = Client()
        c.login(username=user.username, password="Test61_PF_pass!")
        r = c.post(
            reverse("account_upload_avatar"),
            {"avatar": _tiny_jpeg("av.jpg")},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))

    def test_62_mypet_list_200(self):
        owner = _pf_user()
        _published_pet(owner)
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.get(reverse("mypet"))
        self.assertEqual(r.status_code, 200)

    def test_63_mypet_add_200(self):
        owner = _pf_user()
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.get(reverse("mypet_add"))
        self.assertEqual(r.status_code, 200)

    def test_64_mypet_edit_200(self):
        owner = _pf_user()
        pet = _published_pet(owner)
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.get(reverse("mypet_edit", args=[pet.pk]))
        self.assertEqual(r.status_code, 200)

    def test_65_66_67_promo_a2_flow(self):
        owner = _pf_user()
        pet = _published_pet(owner)
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.get(reverse("promo_a2_order", args=[pet.pk]))
        self.assertEqual(r.status_code, 200)
        today = timezone.localdate().isoformat()
        r2 = c.post(
            reverse("promo_a2_order", args=[pet.pk]),
            {
                "package": "6h",
                "quantity": "1",
                "start_date": today,
            },
        )
        self.assertEqual(r2.status_code, 302)
        r3 = c.get(reverse("promo_a2_checkout_demo", args=[pet.pk]))
        self.assertEqual(r3.status_code, 200)
        r4 = c.get(reverse("promo_a2_checkout_demo_success", args=[pet.pk]))
        self.assertEqual(r4.status_code, 200)

    def test_68_mypet_observatii_post_json(self):
        owner = _pf_user()
        pet = _published_pet(owner)
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.post(
            reverse("mypet_observatii_update", args=[pet.pk]),
            {"observatii": "Notă test carte"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        pet.refresh_from_db()
        self.assertIn("Notă test", pet.observatii)

    def test_69_70_71_mypet_messages_json(self):
        owner = _pf_user()
        adopter = _pf_user("adpmsg")
        pet = _published_pet(owner)
        AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_ACCEPTED,
        )
        PetMessage.objects.create(
            animal=pet,
            sender=adopter,
            receiver=owner,
            body="Salut",
        )
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.get(reverse("mypet_messages_list", args=[pet.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        r2 = c.get(reverse("mypet_messages_thread", args=[pet.pk, adopter.pk]))
        self.assertEqual(r2.status_code, 200)
        r3 = c.post(
            reverse("mypet_messages_reply", args=[pet.pk, adopter.pk]),
            {"message": "Răspuns proprietar"},
        )
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.json().get("ok"))

    def test_72_73_74_adopter_messages_json(self):
        owner = _pf_user()
        adopter = _pf_user("adpthr")
        pet = _published_pet(owner)
        AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_ACCEPTED,
        )
        PetMessage.objects.create(
            animal=pet,
            sender=owner,
            receiver=adopter,
            body="Bună",
        )
        c = Client()
        c.login(username=adopter.username, password="Test61_PF_pass!")
        r = c.get(reverse("adopter_messages_list"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        r2 = c.get(reverse("adopter_messages_thread", args=[pet.pk]))
        self.assertEqual(r2.status_code, 200)
        r3 = c.post(
            reverse("adopter_messages_reply", args=[pet.pk]),
            {"message": "Mesaj adopter"},
        )
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.json().get("ok"))

    def test_75_adoption_request_post(self):
        owner = _pf_user()
        adopter = _pf_user("adoptreq")
        pet = _published_pet(owner)
        c = Client()
        c.login(username=adopter.username, password="Test61_PF_pass!")
        r = c.post(reverse("pet_adoption_request", args=[pet.pk]), {})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_76_pet_send_message_post(self):
        owner = _pf_user()
        adopter = _pf_user("sendmsg")
        pet = _published_pet(owner)
        # Hibrid: mesaj din fișă fără cerere de adopție acceptată în prealabil
        c = Client()
        c.login(username=adopter.username, password="Test61_PF_pass!")
        r = c.post(
            reverse("pet_send_message", args=[pet.pk]),
            {"message": "Mesaj fișă publică"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_77_pet_track_post(self):
        owner = _pf_user()
        pet = _published_pet(owner)
        c = Client()
        r = c.post(
            reverse("pet_track_event", args=[pet.pk]),
            {"event": "media_view"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_78_adoption_bonus_toggle(self):
        collab = _collab_cabinet_user()
        prof = collab.profile
        prof.company_judet = "Cluj"
        prof.save()
        offer = CollaboratorServiceOffer.objects.create(
            collaborator=collab,
            partner_kind=CollaboratorServiceOffer.PARTNER_KIND_CABINET,
            title="Bonus vet",
            image=_tiny_jpeg(),
            is_active=True,
            quantity_available=10,
            valid_from=timezone.localdate() - timedelta(days=1),
            valid_until=timezone.localdate() + timedelta(days=30),
            price_hint="100 lei",
            discount_percent=10,
            species_dog=True,
            species_cat=False,
            species_other=False,
        )
        owner = _pf_user()
        adopter = _pf_user("bonusad")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        c = Client()
        c.login(username=adopter.username, password="Test61_PF_pass!")
        r = c.post(
            reverse("adoption_bonus_offer_toggle"),
            {"adoption_request_id": str(ar.pk), "offer_id": str(offer.pk)},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_79_adoption_email_owner_action(self):
        owner = _pf_user()
        adopter = _pf_user("mailown")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        signer = TimestampSigner(salt="adoption-owner-email-v1")
        token = signer.sign(f"{ar.pk}:{owner.pk}")
        r = Client().get(reverse("adoption_email_owner_action") + "?" + urlencode({"t": token, "d": "accept"}))
        self.assertEqual(r.status_code, 200)
        ar.refresh_from_db()
        self.assertEqual(ar.status, AdoptionRequest.STATUS_ACCEPTED)

    def test_79b_adoption_email_owner_action_path_legacy(self):
        """Link vechi în path (/adoption/email/<token>/accept/) rămâne valid pentru emailuri deja trimise."""
        owner = _pf_user()
        adopter = _pf_user("mailown2")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        signer = TimestampSigner(salt="adoption-owner-email-v1")
        token = signer.sign(f"{ar.pk}:{owner.pk}")
        r = Client().get(reverse("adoption_email_owner_action_path", args=[token, "accept"]))
        self.assertEqual(r.status_code, 200)
        ar.refresh_from_db()
        self.assertEqual(ar.status, AdoptionRequest.STATUS_ACCEPTED)

    def test_80_mypet_adoption_accept_post(self):
        owner = _pf_user()
        adopter = _pf_user("acc80")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.post(reverse("mypet_adoption_accept", args=[ar.pk]), {})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class Carte81_100Tests(TestCase):
    """Carte 81–100: respingere/prelungire/finalizare adopție; magazin; oferte; mesaje; transport; wishlist."""

    def test_81_mypet_adoption_reject(self):
        owner = _pf_user()
        adopter = _pf_user("rj81")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.post(reverse("mypet_adoption_reject", args=[ar.pk]), {})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_82_mypet_adoption_extend(self):
        owner = _pf_user()
        adopter = _pf_user("ex82")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_ACCEPTED,
            accepted_at=timezone.now(),
            accepted_expires_at=timezone.now() + timedelta(days=3),
        )
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.post(reverse("mypet_adoption_extend", args=[ar.pk]), {})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_83_mypet_adoption_next_no_queue(self):
        owner = _pf_user()
        adopter = _pf_user("nx83")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_ACCEPTED,
            accepted_at=timezone.now(),
            accepted_expires_at=timezone.now() + timedelta(days=5),
        )
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.post(reverse("mypet_adoption_next", args=[ar.pk]), {})
        self.assertEqual(r.status_code, 400)
        r_page = c.get(reverse("mypet"))
        self.assertEqual(r_page.status_code, 200)
        # Butonul ⚙ (nu regula CSS `.mypet-row-adopt-manage` din același șablon).
        self.assertNotIn(b'class="mypet-row-adopt-btn mypet-row-adopt-manage"', r_page.content)

    def test_84_mypet_adoption_finalize(self):
        owner = _pf_user()
        adopter = _pf_user("fn84")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_ACCEPTED,
            accepted_at=timezone.now(),
            accepted_expires_at=timezone.now() + timedelta(days=5),
        )
        c = Client()
        c.login(username=owner.username, password="Test61_PF_pass!")
        r = c.post(reverse("mypet_adoption_finalize", args=[ar.pk]), {})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_85_86_magazin_redirects_collab(self):
        collab = _collab_cabinet_user()
        c = Client()
        c.login(username=collab.username, password="Test61_Col_pass!")
        r = c.get(reverse("magazinul_meu"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("oferte", r.url or "")
        r2 = c.get(reverse("collab_offers_control"))
        self.assertEqual(r2.status_code, 200)

    def test_87_collab_offer_new_200(self):
        collab = _collab_cabinet_user()
        c = Client()
        c.login(username=collab.username, password="Test61_Col_pass!")
        r = c.get(reverse("collab_offer_new"))
        self.assertEqual(r.status_code, 200)

    def test_88_collab_offer_add_post_creates(self):
        collab = _collab_cabinet_user()
        c = Client()
        c.login(username=collab.username, password="Test61_Col_pass!")
        d0 = timezone.localdate()
        d1 = d0 + timedelta(days=60)
        r = c.post(
            reverse("collab_offer_add"),
            {
                "title": "Serviciu test carte",
                "description": "Desc",
                "price_hint": "150 lei",
                "discount_percent": "15",
                "quantity_available": "5",
                "valid_from": d0.isoformat(),
                "valid_until": d1.isoformat(),
                "species_dog": "on",
                "image": _tiny_jpeg("add88.jpg"),
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            CollaboratorServiceOffer.objects.filter(
                collaborator=collab, title="Serviciu test carte"
            ).exists()
        )

    def test_89_90_91_collab_offer_edit_toggle_delete(self):
        collab = _collab_cabinet_user()
        d0 = timezone.localdate()
        d1 = d0 + timedelta(days=30)
        offer = CollaboratorServiceOffer.objects.create(
            collaborator=collab,
            partner_kind=CollaboratorServiceOffer.PARTNER_KIND_CABINET,
            title="Edit me",
            image=_tiny_jpeg("o89.jpg"),
            quantity_available=3,
            valid_from=d0,
            valid_until=d1,
            price_hint="50 lei",
            discount_percent=5,
            species_dog=True,
            species_cat=True,
            species_other=False,
            is_active=True,
        )
        c = Client()
        c.login(username=collab.username, password="Test61_Col_pass!")
        r = c.get(reverse("collab_offer_edit", args=[offer.pk]))
        self.assertEqual(r.status_code, 200)
        r2 = c.post(reverse("collab_offer_toggle_active", args=[offer.pk]), {})
        self.assertEqual(r2.status_code, 302)
        offer.refresh_from_db()
        self.assertFalse(offer.is_active)
        r3 = c.post(reverse("collab_offer_delete", args=[offer.pk]), {})
        self.assertEqual(r3.status_code, 302)
        self.assertFalse(CollaboratorServiceOffer.objects.filter(pk=offer.pk).exists())

    def test_92_collab_inbox_list_json(self):
        collab = _collab_cabinet_user()
        c = Client()
        c.login(username=collab.username, password="Test61_Col_pass!")
        r = c.get(reverse("collab_inbox_list"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_93_94_collab_inbox_thread_reply(self):
        collab = _collab_cabinet_user()
        client_u = _pf_user("clmsg")
        from home.models import CollabServiceMessage

        CollabServiceMessage.objects.create(
            collaborator=collab,
            context_type=CollabServiceMessage.CONTEXT_GENERAL,
            context_ref="",
            sender=client_u,
            receiver=collab,
            body="Întrebare",
        )
        c = Client()
        c.login(username=collab.username, password="Test61_Col_pass!")
        r = c.get(reverse("collab_inbox_thread"), {"client_id": str(client_u.pk)})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        r2 = c.post(
            reverse("collab_inbox_reply"),
            {"message": "Răspuns collab", "client_id": str(client_u.pk)},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json().get("ok"))

    def test_95_public_offer_request_post(self):
        collab = _collab_cabinet_user()
        d0 = timezone.localdate()
        d1 = d0 + timedelta(days=20)
        offer = CollaboratorServiceOffer.objects.create(
            collaborator=collab,
            partner_kind=CollaboratorServiceOffer.PARTNER_KIND_CABINET,
            title="Public req",
            image=_tiny_jpeg("p95.jpg"),
            quantity_available=5,
            valid_from=d0,
            valid_until=d1,
            price_hint="80 lei",
            discount_percent=10,
            species_dog=True,
            species_cat=True,
            species_other=False,
            is_active=True,
        )
        buyer = _pf_user("buy95")
        c = Client()
        c.login(username=buyer.username, password="Test61_PF_pass!")
        r = c.post(
            reverse("public_offer_request", args=[offer.pk]),
            {"name": "Ion", "email": buyer.email},
        )
        self.assertEqual(r.status_code, 302)

    def test_95b_public_offer_request_anonymous_redirects_login(self):
        collab = _collab_cabinet_user()
        d0 = timezone.localdate()
        d1 = d0 + timedelta(days=20)
        offer = CollaboratorServiceOffer.objects.create(
            collaborator=collab,
            partner_kind=CollaboratorServiceOffer.PARTNER_KIND_CABINET,
            title="Anon gate",
            image=_tiny_jpeg("p95b.jpg"),
            quantity_available=5,
            valid_from=d0,
            valid_until=d1,
            price_hint="80 lei",
            discount_percent=10,
            species_dog=True,
            species_cat=True,
            species_other=False,
            is_active=True,
        )
        c = Client()
        detail_path = reverse("public_offer_detail", args=[offer.pk])
        r = c.post(reverse("public_offer_request", args=[offer.pk]), {})
        self.assertEqual(r.status_code, 302)
        loc = r.get("Location", "")
        self.assertIn(reverse("login"), loc)
        qs = parse_qs(urlparse(loc).query)
        next_vals = qs.get("next") or []
        self.assertTrue(next_vals, msg="login redirect should carry next=")
        self.assertEqual(unquote(next_vals[0]), detail_path)

    def test_95c_public_offer_request_collab_rejected(self):
        collab = _collab_cabinet_user()
        d0 = timezone.localdate()
        d1 = d0 + timedelta(days=20)
        offer = CollaboratorServiceOffer.objects.create(
            collaborator=collab,
            partner_kind=CollaboratorServiceOffer.PARTNER_KIND_CABINET,
            title="Collab no buy",
            image=_tiny_jpeg("p95c.jpg"),
            quantity_available=5,
            valid_from=d0,
            valid_until=d1,
            price_hint="80 lei",
            discount_percent=10,
            species_dog=True,
            species_cat=True,
            species_other=False,
            is_active=True,
        )
        c = Client()
        c.login(username=collab.username, password="Test61_Col_pass!")
        r = c.post(reverse("public_offer_request", args=[offer.pk]), {})
        self.assertEqual(r.status_code, 302)
        self.assertIn(str(offer.pk), r.get("Location", ""))

    def test_96_98_collab_client_messages(self):
        collab = _collab_cabinet_user()
        client_u = _pf_user("clin96")
        from home.models import CollabServiceMessage

        CollabServiceMessage.objects.create(
            collaborator=collab,
            context_type=CollabServiceMessage.CONTEXT_GENERAL,
            context_ref="",
            sender=collab,
            receiver=client_u,
            body="Ofertă",
        )
        c = Client()
        c.login(username=client_u.username, password="Test61_PF_pass!")
        r = c.get(reverse("collab_client_inbox_list"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        r2 = c.get(
            reverse("collab_client_thread"),
            {"collaborator_id": str(collab.pk)},
        )
        self.assertEqual(r2.status_code, 200)
        j2 = r2.json()
        self.assertTrue(j2.get("ok"))
        self.assertIn("partner_card", j2)
        self.assertIn("partner_name", j2["partner_card"])
        r3 = c.post(
            reverse("collab_client_reply"),
            {"message": "Mulțumesc", "collaborator_id": str(collab.pk)},
        )
        self.assertEqual(r3.status_code, 200)

    def test_99_collab_contact_message_post(self):
        collab = _collab_cabinet_user()
        visitor = _pf_user("vis99")
        c = Client()
        c.login(username=visitor.username, password="Test61_PF_pass!")
        r = c.post(
            reverse("collab_contact_message"),
            {
                "message": "Contact test",
                "collaborator_id": str(collab.pk),
                "context_type": "general",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_100_transport_operator_panel_collab(self):
        u = uuid.uuid4().hex[:8]
        user = User.objects.create_user(
            username=f"tr_{u}",
            email=f"tr_{u}@t61.local",
            password="Test61_Tr_pass!",
        )
        ap = getattr(user, "account_profile", None)
        if ap:
            ap.role = AccountProfile.ROLE_COLLAB
            ap.save()
        prof, _ = UserProfile.objects.get_or_create(user=user, defaults={})
        prof.collaborator_type = "transport"
        prof.save()
        c = Client()
        c.login(username=user.username, password="Test61_Tr_pass!")
        r = c.get(reverse("transport_operator_panel"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode("utf-8")
        self.assertIn(reverse("unified_inbox"), html)
        self.assertIn(reverse("transport"), html)

    def test_101_transport_submit_post_anon_400_or_redirect(self):
        c = Client()
        r = c.post(reverse("transport_submit"), {})
        # View redirects to /transport/ with error if judet/oras/plecare/sosire lipsesc
        self.assertTrue(
            r.status_code >= 400 or r.status_code in (302, 301),
            msg=f"unexpected status {r.status_code}",
        )

    def test_102_106_transport_dispatch_anonymous_redirect_or_405(self):
        c = Client()
        for name, extra in [
            ("transport_dispatch_accept", {}),
            ("transport_dispatch_decline", {}),
            ("transport_dispatch_cancel_user", {}),
            ("transport_op_release_job", {}),
            ("transport_op_accept_pending", {}),
            ("transport_op_decline_pending", {}),
            ("transport_dispatch_rate", {"job_id": 999999}),
        ]:
            kwargs = extra if "job_id" in extra else {}
            url = reverse(name, kwargs=kwargs) if kwargs else reverse(name)
            r = c.get(url)
            self.assertIn(r.status_code, (302, 301, 400, 403, 404, 405), msg=name)

    def test_107_wishlist_toggle_post(self):
        user = _pf_user("wl107")
        c = Client()
        c.login(username=user.username, password="Test61_PF_pass!")
        aid = DEMO_DOGS[0]["id"]
        r = c.post(reverse("wishlist_toggle"), {"animal_id": str(aid)})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_108_i_love_logged_in_200(self):
        user = _pf_user("il108")
        c = Client()
        c.login(username=user.username, password="Test61_PF_pass!")
        r = c.get(reverse("i_love"))
        self.assertEqual(r.status_code, 200)

    def test_109_114_admin_analysis_staff(self):
        staff = User.objects.create_user(
            username=f"st_{uuid.uuid4().hex[:6]}",
            email=f"st@t.local",
            password="Staff61!",
            is_staff=True,
        )
        c = Client()
        c.login(username=staff.username, password="Staff61!")
        for name in (
            "admin_analysis_home",
            "admin_analysis_set_view_as",
            "admin_analysis_dogs",
            "admin_analysis_requests",
            "admin_analysis_users",
            "admin_analysis_alerts",
        ):
            r = c.get(reverse(name))
            self.assertIn(r.status_code, (200, 302), msg=name)
