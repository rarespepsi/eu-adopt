"""Director Adăpost/ONG + URL frumoase animale."""

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import AccountProfile, AnimalListing, UserProfile
from home.shelter_directory import animal_public_url, ensure_org_slug, make_base_slug


@override_settings(PRELAUNCH_MODE=True)
class ShelterDirectoryTests(TestCase):
    def setUp(self):
        self.org = User.objects.create_user(
            username="orgshelter1",
            email="orgshelter1@t.local",
            password="PassTest12345",
            first_name="Ana",
            last_name="Contact",
        )
        AccountProfile.objects.update_or_create(
            user=self.org,
            defaults={"role": AccountProfile.ROLE_ORG, "is_public_shelter": True},
        )
        UserProfile.objects.update_or_create(
            user=self.org,
            defaults={
                "company_display_name": "Adăpost Test Brașov",
                "company_oras": "Brașov",
                "company_judet": "Brașov",
                "phone": "0700111222",
                "company_representative": "Ana Contact",
            },
        )
        self.pet = AnimalListing.objects.create(
            owner=self.org,
            name="Rex",
            city="București",
            species="dog",
            is_published=True,
        )

    def test_slug_rex_bucuresti(self):
        self.assertEqual(make_base_slug("Rex", "București"), "rex-bucuresti")
        url = animal_public_url(self.pet)
        self.assertTrue(url.startswith("/caini/"))
        self.assertIn("rex", url)

    def test_directory_lists_org_with_animals(self):
        ensure_org_slug(self.org, save=True)
        r = Client().get(reverse("shelter_directory"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Adăpost Test")

    def test_detail_sidebar_and_pets(self):
        ensure_org_slug(self.org, save=True)
        r = Client().get(reverse("shelter_detail", kwargs={"slug": self.org.account_profile.public_slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Despre noi")
        self.assertContains(r, "Rex")
        self.assertContains(r, "0700111222")

    def test_pets_pk_redirects_to_slug(self):
        r = Client().get(reverse("pets_single", args=[self.pet.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/caini/", r["Location"])
