"""Smoke test for weekly new-member thanks helpers (no SMTP)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from home.models import UserProfile
from home.weekly_new_member_thanks import (
    build_thanks_bodies,
    candidates_queryset,
    process_weekly_thanks,
    week_window_for_sunday_run,
)

RO = ZoneInfo("Europe/Bucharest")


class WeeklyThanksWindowTests(SimpleTestCase):
    def test_sunday_window_includes_prior_monday_catchup(self):
        # Sunday 2026-09-06 18:00 RO
        now = datetime(2026, 9, 6, 18, 0, tzinfo=RO)
        start, end = week_window_for_sunday_run(now)
        self.assertEqual(start.astimezone(RO).date().isoformat(), "2026-08-24")  # Mon, week before current
        self.assertEqual(end, now)


@override_settings(WEEKLY_NEW_MEMBER_THANKS_EMAIL_ENABLED=True)
class WeeklyThanksCandidatesTests(TestCase):
    def test_body_mentions_partners_and_one_offer(self):
        u = User.objects.create_user("u1", "u1@example.com", "x")
        subj, body, html = build_thanks_bodies(u)
        self.assertIn("cabinet", body.lower())
        self.assertIn("grooming", body.lower())
        self.assertIn("o singură ofertă", body.lower())
        self.assertIn("signup/colaborator", body)
        self.assertIn("singură ofertă", html.lower())

    def test_process_skips_non_sunday_without_force(self):
        # Wednesday
        now = datetime(2026, 9, 2, 12, 0, tzinfo=RO)
        stats = process_weekly_thanks(dry_run=True, force=False, now=now)
        self.assertFalse(stats["ok"])
        self.assertIn("not_sunday", stats["reason"])

    def test_candidate_once_flag(self):
        now = datetime(2026, 9, 6, 18, 0, tzinfo=RO)  # Sunday
        u = User.objects.create_user("newu", "new@example.com", "x")
        u.date_joined = now - timedelta(days=2)
        u.save(update_fields=["date_joined"])
        UserProfile.objects.create(user=u)
        qs, _, _ = candidates_queryset(now)
        self.assertTrue(qs.filter(pk=u.pk).exists())
        u.profile.weekly_thanks_sent_at = timezone.now()
        u.profile.save(update_fields=["weekly_thanks_sent_at"])
        qs2, _, _ = candidates_queryset(now)
        self.assertFalse(qs2.filter(pk=u.pk).exists())
