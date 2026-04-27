"""
Remindere email proprietar la ~24h / ~72h pentru cereri adopție în așteptare;
după ~7 zile fără răspuns: închide cererea, notifică adoptatorul (email + inbox), resincronizează animalul.

Programare recomandată (Task Scheduler / cron): cel puțin o dată pe oră, ex.:
  python manage.py adoption_pending_reminders
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from home import inbox_notifications as _inbox
from home.models import AdoptionBonusSelection, AdoptionRequest, PetMessage


class Command(BaseCommand):
    help = (
        "Remindere 24h/72h proprietar pentru cereri adopție pending; după 7 zile expiră cererea și notifică adoptatorul."
    )

    def handle(self, *args, **options):
        from home.views import (
            _send_adoption_pending_owner_reminder_email,
            _send_adoption_reject_adopter_email,
            _sync_animal_adoption_state,
        )

        now = timezone.now()
        d7 = timedelta(days=7)
        h72 = timedelta(hours=72)
        h24 = timedelta(hours=24)

        qs = (
            AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_PENDING)
            .filter(created_at__lte=now - h24)
            .select_related("animal", "animal__owner", "adopter")
            .order_by("pk")
        )

        n_expire = 0
        n_rem24 = 0
        n_rem72 = 0
        n_skip = 0

        for ar in qs:
            age = now - ar.created_at
            if age >= d7:
                with transaction.atomic():
                    locked = (
                        AdoptionRequest.objects.select_for_update()
                        .filter(
                            pk=ar.pk,
                            status=AdoptionRequest.STATUS_PENDING,
                        )
                        .select_related("animal", "animal__owner", "adopter")
                        .first()
                    )
                    if not locked:
                        n_skip += 1
                        continue
                    if (now - locked.created_at) < d7:
                        n_skip += 1
                        continue
                    AdoptionBonusSelection.objects.filter(adoption_request_id=locked.pk).delete()
                    locked.status = AdoptionRequest.STATUS_EXPIRED
                    locked.save(update_fields=["status", "updated_at"])
                    _send_adoption_reject_adopter_email(locked, reason="pending_timeout")
                    pet = locked.animal
                    pl = (pet.name or f"Animal #{pet.pk}").strip()
                    PetMessage.objects.create(
                        animal=pet,
                        sender=pet.owner,
                        receiver=locked.adopter,
                        body=(
                            "Cererea de adopție a fost închisă automat: nu s-a primit răspuns în termenul prevăzut "
                            "(7 zile). Îți mulțumim pentru interes."
                        ),
                        is_read=False,
                    )
                    _inbox.create_inbox_notification(
                        locked.adopter,
                        _inbox.KIND_ADOPTION_PENDING_EXPIRED_ADOPTER,
                        "Cererea ta de adopție a expirat (fără răspuns)",
                        f"Pentru „{pl}” nu s-a primit răspuns în 7 zile; cererea a fost închisă automat.",
                        link_url=reverse("mypet") + f"?open_messages=1&open_adopter_animal={locked.animal_id}",
                        metadata={"pet_id": locked.animal_id},
                    )
                    _sync_animal_adoption_state(pet)
                n_expire += 1
                continue

            if age >= h24 and not ar.owner_reminder_24h_sent_at:
                with transaction.atomic():
                    locked = (
                        AdoptionRequest.objects.select_for_update()
                        .filter(
                            pk=ar.pk,
                            status=AdoptionRequest.STATUS_PENDING,
                            owner_reminder_24h_sent_at__isnull=True,
                        )
                        .first()
                    )
                    if not locked:
                        n_skip += 1
                        continue
                    if _send_adoption_pending_owner_reminder_email(locked, variant="24h"):
                        locked.owner_reminder_24h_sent_at = timezone.now()
                        locked.save(
                            update_fields=["owner_reminder_24h_sent_at", "updated_at"],
                        )
                        n_rem24 += 1
                continue

            if age >= h72 and not ar.owner_reminder_72h_sent_at:
                with transaction.atomic():
                    locked = (
                        AdoptionRequest.objects.select_for_update()
                        .filter(
                            pk=ar.pk,
                            status=AdoptionRequest.STATUS_PENDING,
                            owner_reminder_72h_sent_at__isnull=True,
                        )
                        .first()
                    )
                    if not locked:
                        n_skip += 1
                        continue
                    if _send_adoption_pending_owner_reminder_email(locked, variant="72h"):
                        locked.owner_reminder_72h_sent_at = timezone.now()
                        locked.save(
                            update_fields=["owner_reminder_72h_sent_at", "updated_at"],
                        )
                        n_rem72 += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"adoption_pending_reminders: expired={n_expire}, reminder_24h={n_rem24}, "
                f"reminder_72h={n_rem72}, skipped={n_skip}"
            )
        )
