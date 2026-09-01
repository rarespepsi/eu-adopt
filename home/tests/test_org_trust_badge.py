from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import TestCase

from home.models import AccountProfile
from home.org_trust_badge import (
    owner_ids_with_org_trust_badge,
    pet_shows_org_trust_badge,
    user_has_org_trust_badge,
)

User = get_user_model()


class OrgTrustBadgeTests(TestCase):
    def _user(self, username: str, role: str, *, active=True, pending_delete=False):
        u = User.objects.create_user(username=username, email=f"{username}@example.com", password="x")
        u.is_active = active
        u.save(update_fields=["is_active"])
        ap, _ = AccountProfile.objects.get_or_create(user=u, defaults={"role": role})
        ap.role = role
        if pending_delete:
            from django.utils import timezone

            ap.pending_deletion_requested_at = timezone.now()
        else:
            ap.pending_deletion_requested_at = None
        ap.save()
        return u

    def test_pf_no_badge(self):
        u = self._user("pf1", AccountProfile.ROLE_PF)
        self.assertFalse(user_has_org_trust_badge(u))

    def test_org_active_has_badge(self):
        u = self._user("org1", AccountProfile.ROLE_ORG)
        self.assertTrue(user_has_org_trust_badge(u))

    def test_org_pending_deletion_no_badge(self):
        u = self._user("org2", AccountProfile.ROLE_ORG, pending_delete=True)
        self.assertFalse(user_has_org_trust_badge(u))

    def test_owner_ids_batch(self):
        org = self._user("org3", AccountProfile.ROLE_ORG)
        pf = self._user("pf2", AccountProfile.ROLE_PF)
        ids = owner_ids_with_org_trust_badge([org.pk, pf.pk, 99999])
        self.assertEqual(ids, frozenset([org.pk]))

    def test_pet_dict_flag(self):
        self.assertTrue(pet_shows_org_trust_badge({"show_org_trust_badge": True}))
        self.assertFalse(pet_shows_org_trust_badge({"show_org_trust_badge": False}))

    def test_badge_template_tooltip_text(self):
        tpl = Template('{% load anunturi_extras %}{% eu_org_trust_badge show=True %}')
        html = tpl.render(Context({}))
        self.assertIn("Adăpost/ONG verificat", html)
        self.assertIn("eu-org-trust-badge__tip", html)
