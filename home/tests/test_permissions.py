"""
Teste permisiuni: rute protejate, Django Admin pentru non-staff.
Rulează: python manage.py test home.tests.test_permissions
"""

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class ProtectedAndAdminTests(TestCase):
    """7–8: anonim → cont; user normal → /admin/."""

    def setUp(self):
        u = uuid.uuid4().hex[:10]
        self.user = User.objects.create_user(
            username=f"perm_{u}",
            email=f"perm_{u}@test.local",
            password="PermTest_Pass12",
        )
        self.user.is_active = True
        self.user.is_staff = False
        self.user.save()

    def test_anonymous_cannot_access_account(self):
        r = Client().get(reverse("account"))
        self.assertEqual(r.status_code, 302)
        loc = r.url or ""
        self.assertIn(reverse("login"), loc)
        self.assertIn("next=", loc)

    def test_authenticated_non_staff_cannot_use_django_admin(self):
        c = Client()
        c.login(username=self.user.username, password="PermTest_Pass12")
        r = c.get("/admin/")
        # Django poate răspunde 403 sau 302 către /admin/login/ dacă lipsește is_staff
        self.assertIn(r.status_code, (302, 403))
        if r.status_code == 302:
            self.assertIn("/admin/login", r.url or "")
