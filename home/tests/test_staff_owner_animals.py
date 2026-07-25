from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from home.models import AccountProfile, AnimalListing, CollaboratorServiceOffer


User = get_user_model()


class StaffOwnerAnimalsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner_su_test", password="Pass_Owner12")
        AccountProfile.objects.get_or_create(
            user=self.owner,
            defaults={"role": AccountProfile.ROLE_ORG},
        )
        self.pet = AnimalListing.objects.create(
            owner=self.owner,
            name="RexSu",
            species="dog",
            county="Cluj",
            city="Cluj-Napoca",
            is_published=True,
            sex="M",
        )
        self.superuser = User.objects.create_superuser(
            username="su_test",
            email="su@example.com",
            password="Pass_Su12xx",
        )
        self.normal = User.objects.create_user(username="normal_su_test", password="Pass_Norm12")

    def test_staff_owner_animals_superuser_ok(self):
        c = Client()
        c.login(username="su_test", password="Pass_Su12xx")
        r = c.get(reverse("staff_owner_animals", kwargs={"username": self.owner.username}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "RexSu")
        self.assertContains(r, "@owner_su_test")

    def test_staff_owner_animals_forbidden_for_normal(self):
        c = Client()
        c.login(username="normal_su_test", password="Pass_Norm12")
        r = c.get(reverse("staff_owner_animals", kwargs={"username": self.owner.username}))
        self.assertEqual(r.status_code, 404)

    def test_pet_ficha_shows_owner_link_only_for_superuser(self):
        from home.shelter_directory import animal_public_url, ensure_animal_slug

        ensure_animal_slug(self.pet, save=True)
        url = animal_public_url(self.pet)
        owner_list_url = reverse("staff_owner_animals", kwargs={"username": self.owner.username})

        c = Client()
        c.login(username="su_test", password="Pass_Su12xx")
        r = c.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, owner_list_url)
        self.assertContains(r, f"@{self.owner.username}")

        c2 = Client()
        c2.login(username="normal_su_test", password="Pass_Norm12")
        r2 = c2.get(url)
        self.assertEqual(r2.status_code, 200)
        self.assertNotContains(r2, owner_list_url)


class StaffCollaboratorOffersTests(TestCase):
    def setUp(self):
        self.collab = User.objects.create_user(username="collab_su_test", password="Pass_Collab12")
        AccountProfile.objects.get_or_create(
            user=self.collab,
            defaults={"role": AccountProfile.ROLE_COLLAB},
        )
        self.offer = CollaboratorServiceOffer.objects.create(
            collaborator=self.collab,
            partner_kind=CollaboratorServiceOffer.PARTNER_KIND_CABINET,
            title="Oferta Su Chip",
            is_active=True,
        )
        self.superuser = User.objects.create_superuser(
            username="su_offer_test",
            email="suoffer@example.com",
            password="Pass_Su12xx",
        )
        self.normal = User.objects.create_user(username="normal_offer_test", password="Pass_Norm12")

    def test_staff_collaborator_offers_superuser_ok(self):
        c = Client()
        c.login(username="su_offer_test", password="Pass_Su12xx")
        r = c.get(reverse("staff_collaborator_offers", kwargs={"username": self.collab.username}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Oferta Su Chip")
        self.assertContains(r, "@collab_su_test")

    def test_staff_collaborator_offers_forbidden_for_normal(self):
        c = Client()
        c.login(username="normal_offer_test", password="Pass_Norm12")
        r = c.get(reverse("staff_collaborator_offers", kwargs={"username": self.collab.username}))
        self.assertEqual(r.status_code, 404)

    def test_offer_detail_shows_owner_link_only_for_superuser(self):
        detail = reverse("public_offer_detail", args=[self.offer.pk])
        offers_url = reverse("staff_collaborator_offers", kwargs={"username": self.collab.username})

        c = Client()
        c.login(username="su_offer_test", password="Pass_Su12xx")
        r = c.get(detail)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, offers_url)
        self.assertContains(r, f"@{self.collab.username}")

        c2 = Client()
        c2.login(username="normal_offer_test", password="Pass_Norm12")
        r2 = c2.get(detail)
        self.assertEqual(r2.status_code, 200)
        self.assertNotContains(r2, offers_url)
