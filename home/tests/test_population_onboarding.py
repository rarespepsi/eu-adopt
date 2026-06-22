"""Teste reguli populare adăpost / ONG."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from home.models import AccountProfile, AnimalListing

User = get_user_model()


@override_settings(
    POPULATION_ONBOARDING_ENABLED=True,
    PRELAUNCH_MODE=True,
    POPULATION_ANIMAL_MIN=2,
    POPULATION_ANIMAL_MAX=5,
    SMS_OTP_DEV_CODE="528419",
)
class PopulationOnboardingTests(TestCase):
    def setUp(self):
        self.org_user = User.objects.create_user(username="ong_pop", password="x")
        AccountProfile.objects.filter(user=self.org_user).update(role=AccountProfile.ROLE_ORG)
        self.org_user._state.fields_cache.clear()

    def test_org_nav_reduced_context(self):
        from home.population_onboarding import population_context_for_user

        ctx = population_context_for_user(self.org_user)
        self.assertTrue(ctx["population_org_nav_reduced"])
        self.assertFalse(ctx["population_onboarding_complete"])

    def test_max_animals_blocks_add(self):
        from home.population_onboarding import check_org_can_add_animal

        for i in range(5):
            AnimalListing.objects.create(owner=self.org_user, name=f"P{i}", is_published=True)
        ok, msg = check_org_can_add_animal(self.org_user)
        self.assertFalse(ok)
        self.assertIn("maximum 5", msg.lower())

    def test_pf_not_limited(self):
        from home.population_onboarding import check_org_can_add_animal

        pf = User.objects.create_user(username="pf_pop", password="x")
        prof, _ = AccountProfile.objects.get_or_create(user=pf)
        prof.role = AccountProfile.ROLE_PF
        prof.save(update_fields=["role"])
        ok, _ = check_org_can_add_animal(pf)
        self.assertTrue(ok)

    def test_mypet_add_redirect_at_max(self):
        for i in range(5):
            AnimalListing.objects.create(owner=self.org_user, name=f"M{i}", is_published=True)
        c = Client()
        c.force_login(self.org_user)
        r = c.get("/mypet/add/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/mypet/", r.url)

    def test_pf_login_blocked_during_population(self):
        pf = User.objects.create_user(username="pf_login", password="Secret12ab")
        AccountProfile.objects.filter(user=pf).update(role=AccountProfile.ROLE_PF)
        c = Client()
        r = c.post("/login/", {"login": "pf_login", "password": "Secret12ab"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"populare", r.content.lower())

    def test_org_login_allowed(self):
        self.org_user.set_password("Secret12ab")
        self.org_user.save()
        c = Client()
        r = c.post("/login/", {"login": "ong_pop", "password": "Secret12ab"})
        self.assertEqual(r.status_code, 302)

    def test_org_blocked_from_shop(self):
        self.org_user.set_password("x")
        self.org_user.save()
        c = Client()
        c.login(username="ong_pop", password="x")
        r = c.get("/shop/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/mypet/", r.url)

    def test_signup_organizatie_public_in_prelaunch(self):
        c = Client()
        r = c.get("/signup/organizatie/")
        self.assertEqual(r.status_code, 200)
