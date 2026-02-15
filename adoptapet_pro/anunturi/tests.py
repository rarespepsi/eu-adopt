from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch

from .models import Pet, AdoptionRequest
from .forms import AdoptionRequestForm
from .adoption_platform import platform_validation_passes, run_validation_link


class AdoptionRequestFormTest(TestCase):
    """Teste pentru formularul de adopție."""

    def test_form_valid_with_required_fields(self):
        data = {
            "nume_complet": "Ion Popescu",
            "email": "ion@example.com",
            "telefon": "0722123456",
            "adresa": "",
            "mesaj": "",
            "ridicare_personala": False,
            "doreste_transport": False,
            "doreste_cazare_medicala_toiletare": False,
        }
        form = AdoptionRequestForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_invalid_without_email(self):
        data = {
            "nume_complet": "Ion Popescu",
            "email": "",
            "telefon": "0722123456",
        }
        form = AdoptionRequestForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class PlatformValidationTest(TestCase):
    """Teste pentru validarea automată a platformei."""

    def setUp(self):
        self.pet = Pet.objects.create(
            nume="Rex",
            slug="rex",
            rasa="Labrador",
            tip="dog",
            varsta="young",
            sex="male",
            marime="large",
            status="adoptable",
        )

    def test_validation_passes_with_two_words_and_phone(self):
        req = AdoptionRequest(
            pet=self.pet,
            nume_complet="Ion Popescu",
            email="ion@test.ro",
            telefon="0722123456",
        )
        self.assertTrue(platform_validation_passes(req))

    def test_validation_fails_single_word_name(self):
        req = AdoptionRequest(
            pet=self.pet,
            nume_complet="Ion",
            email="ion@test.ro",
            telefon="0722123456",
        )
        self.assertFalse(platform_validation_passes(req))

    def test_validation_fails_short_phone(self):
        req = AdoptionRequest(
            pet=self.pet,
            nume_complet="Ion Popescu",
            email="ion@test.ro",
            telefon="0722",
        )
        self.assertFalse(platform_validation_passes(req))


class AdoptionViewsTest(TestCase):
    """Teste pentru view-urile de adopție."""

    def setUp(self):
        self.pet = Pet.objects.create(
            nume="Pisica",
            slug="pisica",
            rasa="Europeana",
            tip="cat",
            varsta="adult",
            sex="female",
            marime="medium",
            status="adoptable",
        )
        self.client = Client()

    def test_pets_single_renders_with_form(self):
        url = reverse("pets_single", kwargs={"pk": self.pet.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("adoption_form", resp.context)
        self.assertIn("Formular de adopție", resp.content.decode("utf-8"))

    @patch("anunturi.views.send_adoption_request_to_ong")
    @patch("anunturi.views.platform_validation_passes")
    def test_adoption_submit_creates_request_and_redirects(self, mock_validation, mock_send):
        mock_validation.return_value = False  # nu trece validarea -> rămâne "new"
        url = reverse("adoption_request_submit", kwargs={"pk": self.pet.pk})
        data = {
            "nume_complet": "Maria Ionescu",
            "email": "maria@example.com",
            "telefon": "0733123456",
            "adresa": "Str. Florilor 1",
            "mesaj": "Vreau să adopt.",
            "ridicare_personala": True,
            "doreste_cazare_medicala_toiletare": False,
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AdoptionRequest.objects.count(), 1)
        req = AdoptionRequest.objects.get(pet=self.pet)
        self.assertEqual(req.nume_complet, "Maria Ionescu")
        self.assertEqual(req.status, "new")
        self.assertTrue(req.ridicare_personala)


class ValidationLinkTest(TestCase):
    """Teste pentru linkul de validare (run_validation_link)."""

    def setUp(self):
        self.pet = Pet.objects.create(
            nume="Rex",
            slug="rex",
            rasa="Labrador",
            tip="dog",
            varsta="young",
            sex="male",
            marime="large",
            status="adoptable",
            ong_email="ong@asociatie.ro",
        )
        self.req = AdoptionRequest.objects.create(
            pet=self.pet,
            nume_complet="Ion Popescu",
            email="ion@test.ro",
            telefon="0722123456",
            status="approved_platform",
            validation_token="valid-token-123",
        )

    def test_run_validation_fails_without_token(self):
        self.req.validation_token = None
        self.req.save()
        success, err = run_validation_link(self.req)
        self.assertFalse(success)
        self.assertIn("invalid", err.lower())

    def test_run_validation_fails_wrong_status(self):
        self.req.status = "new"
        self.req.save()
        success, err = run_validation_link(self.req)
        self.assertFalse(success)

    @patch("anunturi.adoption_platform.send_mail")
    def test_run_validation_success_sends_emails_and_updates_status(self, mock_send_mail):
        success, err = run_validation_link(self.req)
        self.assertTrue(success)
        self.assertIsNone(err)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "approved_ong")
        self.assertIsNone(self.req.validation_token)
        self.assertEqual(mock_send_mail.call_count, 2)  # un email ONG, unul client
