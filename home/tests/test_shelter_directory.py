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
        self.assertContains(r, 'id="adpDirJudet"')
        self.assertContains(r, 'data-county="Brașov"')
        self.assertContains(r, "Toate județele")

    def test_detail_back_keeps_judet_filter(self):
        ensure_org_slug(self.org, save=True)
        slug = self.org.account_profile.public_slug
        r = Client().get(reverse("shelter_detail", kwargs={"slug": slug}) + "?from_judet=Bra%C8%99ov")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "judet=Bra")
        self.assertContains(r, "adp-det__back")

    def test_detail_sidebar_and_pets(self):
        ensure_org_slug(self.org, save=True)
        r = Client().get(reverse("shelter_detail", kwargs={"slug": self.org.account_profile.public_slug}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Despre noi")
        self.assertContains(r, "Adăpost Test Brașov")
        self.assertNotContains(r, "înregistrată pe EU-Adopt")
        self.assertContains(r, "Rex")
        self.assertContains(r, "0700111222")

    def test_org_about_custom_text(self):
        from home.shelter_directory import normalize_external_link, org_about_text, org_external_link, org_promo_links

        self.assertEqual(org_about_text(self.org), "Adăpost Test Brașov")
        prof = self.org.profile
        prof.despre_noi = "Primim câini și pisici din județ. Ne poți vizita în weekend."
        prof.link_extern = "exemplu.ro/adapost"
        prof.link_social = "facebook.com/adapost"
        prof.link_mancare = "https://shop.example/mancare"
        prof.link_propriu = ""
        prof.save(update_fields=["despre_noi", "link_extern", "link_social", "link_mancare", "link_propriu"])
        self.assertIn("Primim câini", org_about_text(self.org))
        self.assertNotIn("înregistrată pe EU-Adopt", org_about_text(self.org))
        self.assertEqual(normalize_external_link("exemplu.ro/adapost"), "https://exemplu.ro/adapost")
        self.assertEqual(org_external_link(self.org), "https://exemplu.ro/adapost")
        promo = org_promo_links(self.org)
        self.assertEqual(promo["social"], "https://facebook.com/adapost")
        self.assertEqual(promo["mancare"], "https://shop.example/mancare")
        self.assertTrue(promo["propriu_is_default"])
        self.assertIn("donatii", promo["propriu"])
        self.assertIn("Suflet", promo["propriu_label"])
        ensure_org_slug(self.org, save=True)
        r = Client().get(reverse("shelter_detail", kwargs={"slug": self.org.account_profile.public_slug}))
        self.assertContains(r, "Site / pagină")
        self.assertContains(r, "https://exemplu.ro/adapost")
        self.assertContains(r, "Suflet")
        self.assertContains(r, promo["social"])
        self.assertContains(r, promo["mancare"])

    def test_pets_pk_redirects_to_slug(self):
        r = Client().get(reverse("pets_single", args=[self.pet.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/caini/", r["Location"])
