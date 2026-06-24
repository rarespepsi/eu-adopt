"""
Trimite o invitație staff (șablon lung) către un singur email — pilot / test.

Exemplu:
  python manage.py staff_invite_send_one --email nicolalexandru77@gmail.com
  python manage.py staff_invite_send_one --email x@y.ro --kind adapost --subtype adpub --dry-run
"""

from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory

from home.models import StaffOnboardingLead, StaffOnboardingInviteLog
from home.staff_onboarding_invite import (
    staff_invite_process_one,
    staff_invite_subject_body,
)

User = get_user_model()


def _request_for_base_url(base_url: str):
    parsed = urlparse(base_url.strip().rstrip("/") + "/")
    if not parsed.scheme or not parsed.netloc:
        raise CommandError(f"URL invalid: {base_url!r}")
    rf = RequestFactory()
    secure = parsed.scheme == "https"
    return rf.get("/", HTTP_HOST=parsed.netloc, secure=secure)


class Command(BaseCommand):
    help = "Creează/actualizează un lead și trimite invitația email (pilot)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Adresa destinatarului")
        parser.add_argument(
            "--kind",
            default=StaffOnboardingLead.KIND_ADAPOST,
            choices=[
                StaffOnboardingLead.KIND_ADAPOST,
                StaffOnboardingLead.KIND_ORG,
                StaffOnboardingLead.KIND_COLLAB,
                StaffOnboardingLead.KIND_PF,
            ],
        )
        parser.add_argument(
            "--subtype",
            default=StaffOnboardingLead.COLLAB_ADPUB,
            help="adpub, adprv, cabinet, magazin, transport, grooming, servicii",
        )
        parser.add_argument("--name", default="", help="Nume afișat / contact")
        parser.add_argument("--org", default="", help="Denumire organizație")
        parser.add_argument("--judet", default="", help="Județ")
        parser.add_argument("--oras", default="", help="Oraș")
        parser.add_argument(
            "--base-url",
            default="",
            help="Origin linkuri (implicit SITE_BASE_URL sau https://www.eu-adopt.ro)",
        )
        parser.add_argument(
            "--staff-username",
            default="rares",
            help="User staff care apare în jurnalul de trimitere",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează subiectul și începutul corpului, fără SMTP",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Trimite chiar dacă STAFF_INVITE_EMAIL_ENABLED=0 (pilot)",
        )

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        if not email or "@" not in email:
            raise CommandError("Email invalid")

        base_url = (options["base_url"] or "").strip().rstrip("/")
        if not base_url:
            base_url = (
                getattr(settings, "SITE_BASE_URL", "").strip().rstrip("/")
                or "https://www.eu-adopt.ro"
            )

        staff_user = User.objects.filter(
            username=(options["staff_username"] or "").strip(),
            is_staff=True,
        ).first()
        if not staff_user:
            staff_user = User.objects.filter(is_superuser=True).first()
        if not staff_user:
            raise CommandError("Nu există user staff pentru jurnalul de trimitere")

        kind = options["kind"]
        sub = (options["subtype"] or "").strip().lower()
        display = (options["name"] or "").strip() or email.split("@", 1)[0]
        org = (options["org"] or "").strip()
        is_public = sub == StaffOnboardingLead.COLLAB_ADPUB
        if kind == StaffOnboardingLead.KIND_ADAPOST and sub not in (
            StaffOnboardingLead.COLLAB_ADPUB,
            StaffOnboardingLead.COLLAB_ADPRV,
        ):
            sub = StaffOnboardingLead.COLLAB_ADPUB
            is_public = True

        lead, created = StaffOnboardingLead.objects.get_or_create(
            email=email,
            defaults={
                "display_name": display,
                "org_display_name": org,
                "account_kind": kind,
                "collaborator_subtype": sub if kind in (
                    StaffOnboardingLead.KIND_ADAPOST,
                    StaffOnboardingLead.KIND_COLLAB,
                ) else "",
                "is_public_shelter": is_public,
                "judet": (options["judet"] or "").strip(),
                "oras": (options["oras"] or "").strip(),
                "status": StaffOnboardingLead.ST_READY,
            },
        )
        if not created:
            lead.display_name = display or lead.display_name
            if org:
                lead.org_display_name = org
            lead.account_kind = kind
            if kind in (StaffOnboardingLead.KIND_ADAPOST, StaffOnboardingLead.KIND_COLLAB):
                lead.collaborator_subtype = sub
            if kind == StaffOnboardingLead.KIND_ADAPOST:
                lead.is_public_shelter = is_public
            if options["judet"]:
                lead.judet = options["judet"].strip()
            if options["oras"]:
                lead.oras = options["oras"].strip()
            if lead.imported_user_id:
                lead.imported_user = None
                lead.invite_mail_status = StaffOnboardingLead.INVITE_NEVER
                lead.invite_email_last_sent_at = None
            lead.save()

        request = _request_for_base_url(base_url)
        subj, body, template_key = staff_invite_subject_body(request, lead)

        self.stdout.write(f"Lead id={lead.pk} created={created} template={template_key}")
        self.stdout.write(f"Base URL: {base_url}")
        self.stdout.write(f"Subject: {subj}")
        self.stdout.write("--- body (first 800 chars) ---")
        self.stdout.write(body[:800])
        if len(body) > 800:
            self.stdout.write("...")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run — nu s-a trimis email."))
            return

        prev = getattr(settings, "STAFF_INVITE_EMAIL_ENABLED", False)
        if options["force"]:
            settings.STAFF_INVITE_EMAIL_ENABLED = True

        try:
            result = staff_invite_process_one(
                request,
                staff_user,
                lead,
                dispatch_kind=StaffOnboardingInviteLog.DISPATCH_MANUAL,
            )
        finally:
            if options["force"]:
                settings.STAFF_INVITE_EMAIL_ENABLED = prev

        if result == "sent":
            self.stdout.write(self.style.SUCCESS(f"TRIMIS către {email}"))
        elif result == "simulated":
            self.stdout.write(
                self.style.WARNING(
                    f"Simulare (SMTP invitații dezactivat). Repetă cu --force sau "
                    f"EUADOPT_STAFF_INVITE_EMAIL_ENABLED=1"
                )
            )
        elif result == "error":
            raise CommandError("Eroare SMTP — vezi log / StaffOnboardingInviteLog")
        else:
            raise CommandError(f"Nu s-a trimis: {result}")
