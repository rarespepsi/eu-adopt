"""Normalizare în masă contacte prospecte (email multiplu + telefon)."""

from django.core.management.base import BaseCommand

from home.models import StaffOnboardingLead
from home.staff_invite_email_expand import (
    split_email_field,
    staff_invite_expand_lead_send_targets,
)
from home.staff_lead_contact_normalize import lead_has_multi_phone, normalize_lead_phone


class Command(BaseCommand):
    help = "Normalizează telefoane multiple și desface emailuri combinate în DB (fără trimitere SMTP)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează ce s-ar schimba, fără salvare.",
        )
        parser.add_argument(
            "--phones-only",
            action="store_true",
            help="Doar telefoane (fără split email).",
        )
        parser.add_argument(
            "--emails-only",
            action="store_true",
            help="Doar emailuri combinate (fără telefon).",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        phones_only = bool(options.get("phones_only"))
        emails_only = bool(options.get("emails_only"))
        do_phones = not emails_only
        do_emails = not phones_only

        phone_n = email_n = 0
        for lead in StaffOnboardingLead.objects.all().order_by("pk").iterator():
            changed_parts: list[str] = []

            if do_phones and lead_has_multi_phone(lead.phone):
                if dry:
                    changed_parts.append(f"phone {lead.phone!r}")
                elif normalize_lead_phone(lead, save=True):
                    phone_n += 1
                    self.stdout.write(f"#{lead.pk} phone -> {lead.phone!r}")

            if do_emails and len(split_email_field(lead.email)) > 1:
                if dry:
                    changed_parts.append(f"email {lead.email!r}")
                else:
                    before_pks = set(
                        StaffOnboardingLead.objects.filter(
                            notes__contains=f"[split din lead #{lead.pk}]"
                        ).values_list("pk", flat=True)
                    )
                    staff_invite_expand_lead_send_targets(lead)
                    lead.refresh_from_db()
                    after = StaffOnboardingLead.objects.filter(
                        notes__contains=f"[split din lead #{lead.pk}]"
                    ).exclude(pk__in=before_pks)
                    email_n += 1
                    self.stdout.write(
                        f"#{lead.pk} email -> {lead.email!r}"
                        + (f" (+{after.count()} clone)" if after.exists() else "")
                    )

            if dry and changed_parts:
                self.stdout.write(f"#{lead.pk}: " + " · ".join(changed_parts))

        if dry:
            self.stdout.write(self.style.WARNING("Dry-run — nimic salvat."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Gata: telefoane normalizate={phone_n}, emailuri desfăcute={email_n}."
                )
            )
