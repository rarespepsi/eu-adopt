from django.core.cache import cache
from django.test import TestCase, override_settings

from home.staff_invite_daily_wave import (
    STAFF_INVITE_CRON_REGION_CACHE_KEY,
    mark_region_group_used,
    next_region_group_for_cron,
    run_staff_invite_daily_wave,
)
from home.staff_invite_email_expand import split_email_field


class StaffInviteDailyWaveTests(TestCase):
    def tearDown(self):
        cache.delete(STAFF_INVITE_CRON_REGION_CACHE_KEY)

    def test_region_group_alternates(self):
        self.assertEqual(next_region_group_for_cron(), "a")
        mark_region_group_used("a")
        self.assertEqual(next_region_group_for_cron(), "b")
        mark_region_group_used("b")
        self.assertEqual(next_region_group_for_cron(), "a")

    def test_split_email_field(self):
        raw = "a@x.ro / b@y.com   c@z.net"
        self.assertEqual(split_email_field(raw), ["a@x.ro", "b@y.com", "c@z.net"])

    @override_settings(STAFF_INVITE_CRON_ENABLED=False)
    def test_cron_disabled_skips(self):
        result = run_staff_invite_daily_wave()
        self.assertTrue(result.skipped)
