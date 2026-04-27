"""
Smoke tests: răspuns HTTP rezonabil pe rute critice (fără 500).
Rulează: python manage.py test home.tests.test_smoke
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()

# Nume de rute care trebuie să răspundă 200 la GET anonim (pagini publice).
PUBLIC_GET_200_NAMES = [
    "home",
    "login",
    "signup_choose_type",
    "signup_pf",
    "signup_organizatie",
    "signup_colaborator",
    "pets_all",
    "servicii",
    "shop",
    "shop_comanda_personalizate",
    "shop_magazin_foto",
    "shop_magazin_foto_more",
    "transport",
    "custi",
    "contact",
    "termeni",
    "termeni_read",
    "politica_confidentialitate",
    "politici_altele",
    "politica_cookie",
    "politica_servicii_platite",
    "politica_moderare",
    "forgot_password",
]

# GET anonim → redirect la login (302) sau interzis fără crash.
ANONYMOUS_REDIRECT_OR_FORBIDDEN_NAMES = [
    "account",
    "mypet",
    "i_love",
    "i_love_cos",
    "site_cart_checkout",
    "site_cart_checkout_success",
    "magazinul_meu",
    "transport_operator_panel",
]


class CartePunct1LoginPageTests(TestCase):
    """Carte punct 1: /login/ — încărcare, formular, linkuri cont nou + parolă uitată."""

    def test_login_page_point_1(self):
        r = Client().get(reverse("login"))
        self.assertEqual(r.status_code, 200)
        content = r.content.decode("utf-8")
        self.assertIn('name="login"', content)
        self.assertIn('name="password"', content)
        self.assertIn("id_login", content)
        self.assertIn("id_password", content)
        self.assertIn("Ți-ai uitat parola", content)
        self.assertIn("Creează cont", content)


class SmokePublicPagesTests(TestCase):
    """Pagini publice: 200 și fără excepție."""

    def test_public_routes_return_200(self):
        c = Client()
        failures = []
        for name in PUBLIC_GET_200_NAMES:
            url = reverse(name)
            r = c.get(url)
            if r.status_code != 200:
                failures.append(f"{name} ({url}): got {r.status_code}, expected 200")
        self.assertFalse(failures, "\n".join(failures))

    def test_signup_colaborator_with_tip_transport_returns_200(self):
        r = Client().get(reverse("signup_colaborator"), {"tip": "transport"})
        self.assertEqual(r.status_code, 200)

    def test_anonymous_protected_routes_redirect_or_client_error(self):
        c = Client()
        for name in ANONYMOUS_REDIRECT_OR_FORBIDDEN_NAMES:
            url = reverse(name)
            r = c.get(url)
            self.assertIn(
                r.status_code,
                (302, 301, 303, 307, 308, 403),
                msg=f"{name} ({url}): expected redirect or 403, got {r.status_code}",
            )


class SmokeLoginTests(TestCase):
    """Login POST: utilizator creat în test DB poate intra în cont."""

    def setUp(self):
        # AccountProfile e creat automat la save User (signal în home.models).
        self.user = User.objects.create_user(
            username="smoke_user",
            email="smoke@test.local",
            password="SmokeTestPass123",
        )

    def test_login_post_success_redirects(self):
        c = Client()
        r = c.post(
            reverse("login"),
            {"login": "smoke@test.local", "password": "SmokeTestPass123"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.endswith("/") or "next" in r.url or r.url.startswith("/"))

    def test_login_post_wrong_password_returns_200_with_error(self):
        c = Client()
        r = c.post(
            reverse("login"),
            {"login": "smoke@test.local", "password": "wrong"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "login-error-box", status_code=200)

    def test_account_accessible_after_login(self):
        c = Client()
        c.login(username="smoke_user", password="SmokeTestPass123")
        r = c.get(reverse("account"))
        self.assertEqual(r.status_code, 200)


class SmokeLogoutTests(TestCase):
    def test_logout_get_returns_redirect(self):
        r = Client().get(reverse("logout"))
        self.assertEqual(r.status_code, 302)

    def test_logout_then_account_requires_login(self):
        """Carte 4: după logout, acces /cont/ anonim → redirect (sesiune închisă)."""
        user = User.objects.create_user(
            username="logout_test_u",
            email="logout_test@test.local",
            password="LogoutTestPass123",
        )
        c = Client()
        c.login(username=user.username, password="LogoutTestPass123")
        self.assertEqual(c.get(reverse("account")).status_code, 200)
        self.assertEqual(c.get(reverse("logout")).status_code, 302)
        r = c.get(reverse("account"))
        self.assertIn(r.status_code, (302, 301, 303, 307, 308, 403))


class CartePartA_ForgotResetContTests(TestCase):
    """Carte A: 5 forgot GET 200; 6 reset fără token → redirect (flux real cu token din email); 7 /cont/ anonim → redirect."""

    def test_forgot_password_get_200(self):
        r = Client().get(reverse("forgot_password"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="email"', status_code=200)
        self.assertContains(r, "id_email", status_code=200)

    def test_reset_password_no_token_redirects_to_forgot(self):
        r = Client().get(reverse("reset_password"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("forgot", r.url or "")

    def test_account_anonymous_redirects(self):
        r = Client().get(reverse("account"))
        self.assertIn(r.status_code, (302, 301, 303, 307, 308, 403))

    def test_reset_password_valid_token_get_200(self):
        """Carte 6: pagină reset cu token valid (semnat) — formular parolă nouă."""
        from django.core.signing import TimestampSigner

        user = User.objects.create_user(
            username="reset_tok_u",
            email="reset_tok@test.local",
            password="ResetTokPass123",
        )
        token = TimestampSigner().sign(user.pk)
        r = Client().get(reverse("reset_password"), {"token": token})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "password1", status_code=200)
        self.assertContains(r, "password2", status_code=200)


class CartePunct8_9_10_SignupTests(TestCase):
    """Carte B1 8–9, B2 10: alege tip (carduri + linkuri), PF formular cu câmpuri obligatorii marcate."""

    def test_signup_choose_type_cards_and_back_links(self):
        r = Client().get(reverse("signup_choose_type"))
        self.assertEqual(r.status_code, 200)
        content = r.content.decode("utf-8")
        self.assertIn("Persoană fizică", content)
        self.assertIn("Adăpost / ONG / Firmă", content)
        self.assertIn("Transportator", content)
        self.assertIn(reverse("signup_pf"), content)
        self.assertIn(reverse("signup_organizatie"), content)
        self.assertIn(reverse("signup_colaborator"), content)
        self.assertIn("Înapoi la prima pagină", content)
        self.assertIn(reverse("home"), content)
        self.assertIn("Am deja cont", content)
        self.assertIn(reverse("login"), content)

    def test_signup_pf_form_required_markers(self):
        r = Client().get(reverse("signup_pf"))
        self.assertEqual(r.status_code, 200)
        content = r.content.decode("utf-8")
        self.assertIn("Nume *", content)
        self.assertIn("Email *", content)
        self.assertIn('name="password1"', content)
        self.assertIn("required", content)


class SmokeMyPetAddTests(TestCase):
    """Punct 63 carte: GET /mypet/add/ pentru utilizator PF (MyPet permis)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="carte_mypet_add",
            email="carte_mypet_add@test.local",
            password="CarteTestPass123",
        )

    def test_mypet_add_get_200_and_form(self):
        c = Client()
        self.assertTrue(c.login(username="carte_mypet_add", password="CarteTestPass123"))
        r = c.get(reverse("mypet_add"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "mypet-add-form", status_code=200)

    def test_mypet_add_species_query_dog_cat_other(self):
        c = Client()
        self.assertTrue(c.login(username="carte_mypet_add", password="CarteTestPass123"))
        for species in ("dog", "cat", "other"):
            with self.subTest(species=species):
                r = c.get(reverse("mypet_add"), {"species": species})
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, "mypet-add-form", status_code=200)


class SmokeSeoTests(TestCase):
    """robots.txt și sitemap.xml (SEO)."""

    def test_robots_txt_200_and_sitemap_line(self):
        r = Client().get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        text = r.content.decode("utf-8")
        self.assertIn("User-agent:", text)
        self.assertIn("Sitemap:", text)
        self.assertIn("/sitemap.xml", text)

    def test_sitemap_xml_200(self):
        r = Client().get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"urlset", r.content.lower())
        self.assertNotIn(
            b"example.com",
            r.content.lower(),
            "sitemap must not use default django.contrib.sites domain",
        )
