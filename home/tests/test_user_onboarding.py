"""Tests user onboarding (prima vizită pagină)."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import UserPageOnboardingSeen
from home.user_onboarding import (
    is_new_user_for_onboarding,
    mark_onboarding_page_seen,
    onboarding_payload_for_request,
    user_has_seen_onboarding_page,
)


class UserOnboardingTests(TestCase):
    def test_new_user_within_30_days(self):
        u = User.objects.create_user(username="nou1", email="n1@t.local", password="x")
        self.assertTrue(is_new_user_for_onboarding(u))

    def test_old_user_outside_window(self):
        u = User.objects.create_user(username="vechi", email="v@t.local", password="x")
        User.objects.filter(pk=u.pk).update(date_joined=timezone.now() - timedelta(days=45))
        u.refresh_from_db()
        self.assertFalse(is_new_user_for_onboarding(u))

    def test_mark_seen_and_payload_hidden(self):
        u = User.objects.create_user(username="staffx", email="sx@t.local", password="x", is_staff=True)
        mark_onboarding_page_seen(u, "home")
        self.assertTrue(user_has_seen_onboarding_page(u, "home"))

    @override_settings(PRELAUNCH_MODE=False, USER_ONBOARDING_ENABLED=True)
    def test_dismiss_endpoint(self):
        u = User.objects.create_user(username="onb1", email="onb1@t.local", password="Secret1!")
        c = Client()
        c.force_login(u)
        r = c.post(reverse("user_onboarding_mark_seen"), {"page_key": "mypet"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(UserPageOnboardingSeen.objects.filter(user=u, page_key="mypet").exists())

    def test_payload_none_when_seen(self):
        from django.test import RequestFactory

        u = User.objects.create_user(username="onb2", email="onb2@t.local", password="x")
        mark_onboarding_page_seen(u, "home")
        rf = RequestFactory()
        req = rf.get("/")
        req.user = u
        req.resolver_match = type("RM", (), {"url_name": "home"})()
        self.assertIsNone(onboarding_payload_for_request(req))
