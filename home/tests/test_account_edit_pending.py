"""Confirmare schimbare email — cache cross-device + polling desktop."""

import uuid

from django.contrib.auth import get_user_model
from django.core.signing import TimestampSigner
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from urllib.parse import quote

from home.account_edit_pending import load_edit_pending, save_edit_pending
from home.models import AccountProfile, UserProfile


def _pf_user_with_profile(*, email_suffix: str | None = None):
    User = get_user_model()
    suffix = email_suffix or uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"pfedit{suffix}",
        email=f"pfedit{suffix}@example.com",
        password="EditPendingTest!",
        first_name="Ion",
        last_name="Test",
    )
    UserProfile.objects.create(
        user=user,
        phone="+40 711111111",
        judet="Cluj",
        oras="Cluj-Napoca",
        accept_termeni=True,
        accept_gdpr=True,
    )
    acc = getattr(user, "account_profile", None)
    if acc:
        acc.role = AccountProfile.ROLE_PF
        acc.save(update_fields=["role"])
    return user


@override_settings(
    PRELAUNCH_MODE=False,
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-edit-pending",
        }
    },
)
class EditEmailCrossDeviceTests(TestCase):
    def test_verify_email_applies_pending_from_cache_without_session(self):
        user = _pf_user_with_profile()
        new_email = f"nou{uuid.uuid4().hex[:6]}@example.com"
        pending = {
            "user_pk": user.pk,
            "first_name": "PrenumeNou",
            "last_name": "NumeNou",
            "email": new_email,
            "phone_country": "+40",
            "phone": "722222222",
            "judet": "Brașov",
            "oras": "Brașov",
            "accept_termeni": True,
            "accept_gdpr": True,
            "email_opt_in_wishlist": False,
            "phone_changed": False,
            "email_changed": True,
        }
        save_edit_pending(user.pk, pending)

        token = TimestampSigner().sign(f"{user.pk}:{new_email}")
        phone_client = Client()
        r = phone_client.get(reverse("edit_verify_email") + "?token=" + quote(token))
        self.assertEqual(r.status_code, 302)
        self.assertIn("updated=1", r.url or "")

        user.refresh_from_db()
        self.assertEqual(user.email, new_email)
        self.assertEqual(user.first_name, "PrenumeNou")
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.judet, "Brașov")
        self.assertIsNone(load_edit_pending(user.pk))

    def test_status_polling_detects_confirmed_email(self):
        user = _pf_user_with_profile()
        new_email = f"poll{uuid.uuid4().hex[:6]}@example.com"
        user.email = new_email
        user.save(update_fields=["email"])
        save_edit_pending(
            user.pk,
            {
                "user_pk": user.pk,
                "email": new_email,
                "email_changed": True,
            },
        )

        c = Client()
        c.login(username=user.username, password="EditPendingTest!")
        r = c.get(reverse("edit_verify_email_status"), {"email": new_email})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["confirmed"])
        self.assertIn("updated=1", data["redirect_url"])
        self.assertIsNone(load_edit_pending(user.pk))

    def test_check_email_page_includes_status_poll_script(self):
        user = _pf_user_with_profile()
        c = Client()
        c.login(username=user.username, password="EditPendingTest!")
        r = c.get(reverse("edit_check_email"), {"email": user.email})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "fetch(statusUrl")
        self.assertContains(r, "status/")
