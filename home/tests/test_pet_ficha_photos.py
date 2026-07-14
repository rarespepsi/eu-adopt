"""Fișă animal: doar pozele încărcate de user — fără fallback demo pe sloturi goale."""

import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from home.models import AnimalListing

User = get_user_model()

_MIN_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xd9"
)


class PetFichaPhotosTests(TestCase):
    def test_missing_photo_2_and_3_no_demo_fallback(self):
        owner = User.objects.create_user(username=f"own_{uuid.uuid4().hex[:8]}", password="x")
        photo = SimpleUploadedFile("p1.jpg", _MIN_JPEG, content_type="image/jpeg")
        pet = AnimalListing.objects.create(
            owner=owner,
            name="Bibi",
            species="dog",
            is_published=True,
            photo_1=photo,
        )
        resp = Client().get(reverse("pets_single", args=[pet.pk]))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8", errors="replace")
        self.assertNotIn("charlie-275x275", html)
        self.assertNotIn("charlie-400x200", html)
        self.assertIn("mypet-fisa-photo-1 has-photo", html)
        self.assertIn('class="mypet-fisa-photo-slot mypet-fisa-photo-2"', html)
        self.assertNotIn("alt=\"Poza 2\"", html)
        self.assertNotIn("alt=\"Poza 3\"", html)
