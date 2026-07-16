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
    POPULATION_SUPERUSER_ONLY_LOGIN=False,
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
        self.assertEqual(ctx["population_banner_mode"], "always")

    def test_banner_mode_always_below_min(self):
        from home.population_onboarding import population_banner_mode

        AnimalListing.objects.create(owner=self.org_user, name="P0", is_published=True)
        self.assertEqual(population_banner_mode(self.org_user), "always")

    def test_banner_mode_intermittent_between_min_and_max(self):
        from home.population_onboarding import population_banner_mode

        for i in range(2):
            AnimalListing.objects.create(owner=self.org_user, name=f"I{i}", is_published=True)
        self.assertEqual(population_banner_mode(self.org_user), "intermittent")

    def test_banner_mode_hidden_at_max(self):
        from home.population_onboarding import population_banner_mode

        for i in range(5):
            AnimalListing.objects.create(owner=self.org_user, name=f"H{i}", is_published=True)
        self.assertEqual(population_banner_mode(self.org_user), "hidden")

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

    def test_pf_login_allowed_during_population_varianta_b(self):
        pf = User.objects.create_user(username="pf_login", password="Secret12ab")
        AccountProfile.objects.filter(user=pf).update(role=AccountProfile.ROLE_PF)
        c = Client()
        r = c.post("/login/", {"login": "pf_login", "password": "Secret12ab"})
        self.assertEqual(r.status_code, 302)

    def test_invited_pf_login_allowed_during_population(self):
        from django.utils import timezone

        from home.models import StaffOnboardingLead

        pf = User.objects.create_user(
            username="pf_invited",
            email="pf_invited@test.local",
            password="Secret12ab",
        )
        pf.is_active = True
        pf.save(update_fields=["is_active"])
        AccountProfile.objects.filter(user=pf).update(role=AccountProfile.ROLE_PF)
        StaffOnboardingLead.objects.create(
            email=pf.email,
            display_name="PF Invitat",
            account_kind=StaffOnboardingLead.KIND_PF,
            status=StaffOnboardingLead.ST_IMPORTED,
            invite_mail_status=StaffOnboardingLead.INVITE_SIGNED_UP,
            invite_email_last_sent_at=timezone.now(),
            imported_user=pf,
        )
        c = Client()
        r = c.post("/login/", {"login": "pf_invited", "password": "Secret12ab"})
        self.assertEqual(r.status_code, 302)

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


@override_settings(
    POPULATION_ONBOARDING_ENABLED=True,
    PRELAUNCH_MODE=True,
    POPULATION_SUPERUSER_ONLY_LOGIN=True,
    SMS_OTP_DEV_CODE="528419",
)
class PopulationSuperuserOnlyLoginTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_only", email="admin@eu-adopt.ro", password="Secret12ab"
        )
        self.org_user = User.objects.create_user(username="ong_blocked", password="x")
        AccountProfile.objects.filter(user=self.org_user).update(role=AccountProfile.ROLE_ORG)
        self.staff_user = User.objects.create_user(username="staff_blocked", password="Secret12ab")
        self.staff_user.is_staff = True
        self.staff_user.save(update_fields=["is_staff"])

    def test_superuser_login_allowed(self):
        c = Client()
        r = c.post("/login/", {"login": "admin_only", "password": "Secret12ab"})
        self.assertEqual(r.status_code, 302)

    def test_org_login_blocked(self):
        self.org_user.set_password("Secret12ab")
        self.org_user.save()
        c = Client()
        r = c.post("/login/", {"login": "ong_blocked", "password": "Secret12ab"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"superuser", r.content.lower())

    def test_staff_non_superuser_login_blocked(self):
        c = Client()
        r = c.post("/login/", {"login": "staff_blocked", "password": "Secret12ab"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"superuser", r.content.lower())

    def test_signup_organizatie_blocked(self):
        c = Client()
        r = c.get("/signup/organizatie/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.url)

    def test_signup_organizatie_allowed_with_valid_staff_invite(self):
        from django.utils import timezone

        from home.models import StaffOnboardingLead

        lead = StaffOnboardingLead.objects.create(
            email="inv_ong@test.local",
            display_name="Inv ONG",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            invite_email_last_sent_at=timezone.now(),
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        lead.refresh_from_db()
        c = Client()
        r = c.get(f"/signup/organizatie/?inv={lead.consent_invite_token}")
        self.assertEqual(r.status_code, 200)
