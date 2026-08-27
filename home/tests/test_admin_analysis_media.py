from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from home.admin_analysis_media import (
    build_media_outreach_whatsapp_text,
    import_media_csv,
    media_wa_digits,
    normalize_media_kind,
)
from home.media_outreach_invite import (
    media_outreach_can_send,
    media_outreach_process_one,
    media_outreach_sent_count,
)
from home.models import MediaOutreachInviteLog, MediaOutreachProspect

User = get_user_model()


class MediaOutreachTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="media_staff",
            email="media_staff@example.com",
            password="x",
            is_staff=True,
        )

    def test_normalize_kind(self):
        self.assertEqual(normalize_media_kind("Radio"), MediaOutreachProspect.KIND_RADIO)
        self.assertEqual(normalize_media_kind("televiziune"), MediaOutreachProspect.KIND_TV)
        self.assertEqual(normalize_media_kind("ziar"), MediaOutreachProspect.KIND_PRESS)

    def test_wa_digits(self):
        self.assertEqual(media_wa_digits("0744 396 000"), "40744396000")

    def test_import_csv_and_list(self):
        csv_body = (
            "media_kind,outlet_name,contact_name,email,phone,judet,oras\n"
            "radio,Radio Test,Ana,ana@test.ro,0722000111,Iași,Iași\n"
            "tv,TV Local,, ,0744123456,Cluj,Cluj-Napoca\n"
        )
        stats = import_media_csv(csv_body)
        self.assertEqual(stats["created"], 2)
        self.assertEqual(MediaOutreachProspect.objects.count(), 2)

        self.client.force_login(self.staff)
        r = self.client.get(reverse("admin_analysis_media"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Radio Test")
        self.assertContains(r, "Audio/TV")
        self.assertContains(r, "outreach")

    def test_whatsapp_text(self):
        p = MediaOutreachProspect.objects.create(
            media_kind=MediaOutreachProspect.KIND_RADIO,
            outlet_name="Radio Demo",
            contact_name="Andreea",
            phone="0744396000",
            judet="Iași",
        )
        text = build_media_outreach_whatsapp_text(p)
        self.assertIn("Andreea", text)
        self.assertIn("Radio Demo", text)
        self.assertIn("eu-adopt.ro", text)

    def test_home_has_button(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("admin_analysis_home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Audio/TV")
        self.assertContains(r, reverse("admin_analysis_media"))

    @override_settings(STAFF_INVITE_EMAIL_ENABLED=False, MEDIA_OUTREACH_EMAIL_ENABLED=None)
    def test_simulate_send(self):
        p = MediaOutreachProspect.objects.create(
            media_kind=MediaOutreachProspect.KIND_RADIO,
            outlet_name="Radio Demo",
            contact_name="Ana",
            email="redactie@demo-radio.example",
            max_sends=3,
            cooldown_days=7,
        )
        self.assertTrue(media_outreach_can_send(p)[0])
        result = media_outreach_process_one(self.staff, p)
        self.assertEqual(result, "simulated")
        self.assertEqual(
            MediaOutreachInviteLog.objects.filter(
                prospect=p, outcome=MediaOutreachInviteLog.OUTCOME_DRY_RUN
            ).count(),
            1,
        )
        self.assertEqual(media_outreach_sent_count(p), 0)

    def test_radio_email_template_and_greeting(self):
        from home.media_outreach_invite import media_outreach_greeting_name, media_outreach_subject_body

        p = MediaOutreachProspect.objects.create(
            media_kind=MediaOutreachProspect.KIND_RADIO,
            outlet_name="Radio Moldovei",
            contact_name="Ioana Popescu",
            email="ioana@radio.example",
        )
        self.assertEqual(media_outreach_greeting_name(p), "Ioana Popescu")
        subj, body = media_outreach_subject_body(p)
        self.assertIn("Radio Moldovei", subj)
        self.assertIn("Bună ziua, Ioana Popescu,", body)
        self.assertIn("Adrian", body)
        self.assertIn("eu-adopt.ro", body)
        self.assertIn("animale-pierdute", body)
        self.assertIn("+40 73 EUADOPT", body)

    def test_tv_blocked_from_radio_email(self):
        p = MediaOutreachProspect.objects.create(
            media_kind=MediaOutreachProspect.KIND_TV,
            outlet_name="TV Demo",
            email="stiri@tv-demo.example",
        )
        ok, reason = media_outreach_can_send(p)
        self.assertFalse(ok)
        self.assertIn("radio", reason.lower())

    @override_settings(STAFF_INVITE_EMAIL_ENABLED=False, MEDIA_OUTREACH_EMAIL_ENABLED=None)
    def test_mark_dnc_blocks_send(self):
        p = MediaOutreachProspect.objects.create(
            media_kind=MediaOutreachProspect.KIND_RADIO,
            outlet_name="Radio DNC",
            email="stiri@radio-dnc.example",
            outreach_status=MediaOutreachProspect.ST_DNC,
        )
        ok, reason = media_outreach_can_send(p)
        self.assertFalse(ok)
        self.assertIn("contacta", reason.lower())
