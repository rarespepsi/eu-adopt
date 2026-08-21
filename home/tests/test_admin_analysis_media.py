from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from home.admin_analysis_media import (
    build_media_outreach_whatsapp_text,
    import_media_csv,
    media_wa_digits,
    normalize_media_kind,
)
from home.models import MediaOutreachProspect

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
