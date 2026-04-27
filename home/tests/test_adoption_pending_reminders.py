"""Comandă adoption_pending_reminders: remindere proprietar + expirare 7 zile."""

from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from home import inbox_notifications as _inbox
from home.models import AdoptionRequest, AnimalListing, UserInboxNotification
from home.tests.test_carte_61_100 import _pf_user, _published_pet


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AdoptionPendingRemindersCommandTests(TestCase):
    def test_expires_after_7_days_and_notifies_adopter(self):
        owner = _pf_user()
        adopter = _pf_user("adexp")
        pet = _published_pet(owner)
        pet.adoption_state = AnimalListing.ADOPTION_STATE_OPEN
        pet.save(update_fields=["adoption_state", "updated_at"])
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        past = timezone.now() - timedelta(days=8)
        AdoptionRequest.objects.filter(pk=ar.pk).update(created_at=past)

        mail.outbox.clear()
        call_command("adoption_pending_reminders")
        ar.refresh_from_db()
        pet.refresh_from_db()

        self.assertEqual(ar.status, AdoptionRequest.STATUS_EXPIRED)
        self.assertTrue(
            UserInboxNotification.objects.filter(
                user=adopter,
                kind=_inbox.KIND_ADOPTION_PENDING_EXPIRED_ADOPTER,
            ).exists()
        )
        self.assertEqual(pet.adoption_state, AnimalListing.ADOPTION_STATE_FREE)
        self.assertTrue(len(mail.outbox) >= 1)
        self.assertIn("închisă automat", mail.outbox[-1].body.lower())

    def test_owner_reminder_24h(self):
        owner = _pf_user()
        adopter = _pf_user("adr24")
        pet = _published_pet(owner)
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        past = timezone.now() - timedelta(hours=25)
        AdoptionRequest.objects.filter(pk=ar.pk).update(created_at=past)

        mail.outbox.clear()
        call_command("adoption_pending_reminders")
        ar.refresh_from_db()
        self.assertIsNotNone(ar.owner_reminder_24h_sent_at)
        self.assertIsNone(ar.owner_reminder_72h_sent_at)
        self.assertEqual(ar.status, AdoptionRequest.STATUS_PENDING)
        self.assertTrue(any("reamintire" in m.subject.lower() for m in mail.outbox))
