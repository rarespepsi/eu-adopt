from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.mail_helpers import adoption_pet_public_email_lines, pet_copy_location_text
from home.models import AnimalListing, UserProfile

User = get_user_model()


class PetCopyLocationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="loc_owner",
            email="loc_owner@test.local",
            password="PassTest12345",
        )
        UserProfile.objects.create(
            user=self.owner,
            company_address="Str. Adăpost 12",
            company_oras="Piatra Neamț",
            company_judet="Neamț",
        )
        self.pet = AnimalListing.objects.create(
            owner=self.owner,
            name="Rex",
            species="dog",
            is_published=True,
            city="Piatra Neamț",
            county="Neamț",
        )

    def test_copy_text_includes_address_city_county_romania(self):
        text = pet_copy_location_text(self.pet)
        self.assertIn("Str. Adăpost 12", text)
        self.assertIn("Piatra Neamț", text)
        self.assertIn("Neamț", text)
        self.assertIn("România", text)

    def test_email_lines_include_copy_block(self):
        lines = adoption_pet_public_email_lines(self.pet)
        joined = "\n".join(lines)
        self.assertIn("Locație PET (copie pentru Transport):", joined)
        self.assertIn("Str. Adăpost 12", joined)

    @override_settings(
        PRELAUNCH_MODE=False,
        EUADOPT_NON_RO_STAFF_ONLY=False,
        EUADOPT_EU_PRODUCT_SKIN=True,
    )
    def test_ficha_shows_medium_copy_box(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.get(reverse("pets_single", args=[self.pet.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode("utf-8", errors="replace")
        self.assertIn('id="petCopyLoc"', html)
        self.assertIn("Copie locația PET", html)
        self.assertIn("Str. Adăpost 12", html)
        self.assertIn('id="petQrCorner"', html)
        self.assertTrue(html.find("petCopyLoc") < html.find("petQrCorner"))
