"""
După PUBLICITATE_CREATIVE_REVIEW_HOURS de la live_at: listează sloturi „de verificat”
(opțional: trimite un rezumat pe email la staff).
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from home.mail_helpers import send_mail_text_and_html
from home.models import PublicitateLineCreative


def _staff_recipient_emails() -> list[str]:
    raw = (getattr(settings, "PUBLICITATE_CREATIVE_STAFF_EMAILS", None) or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()][:12]
    out: list[str] = []
    admins = getattr(settings, "ADMINS", None) or ()
    for _name, em in admins:
        e = (em or "").strip()
        if e and e not in out:
            out.append(e)
    if out:
        return out[:8]
    fallback = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    if fallback:
        return [fallback]
    return []


class Command(BaseCommand):
    help = (
        "Listă materiale publicitate cu status live și review_until în trecut "
        "(fereastră verificare recomandată depășită). Opțional: --email trimite rezumat la staff."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            action="store_true",
            help="Trimite email la PUBLICITATE_CREATIVE_STAFF_EMAILS sau ADMINS dacă există rânduri.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        qs = (
            PublicitateLineCreative.objects.filter(
                status=PublicitateLineCreative.STATUS_LIVE,
                review_until__isnull=False,
                review_until__lt=now,
            )
            .select_related("line", "line__order", "line__order__user")
            .order_by("review_until")[:200]
        )
        rows = list(qs)
        if not rows:
            self.stdout.write(self.style.SUCCESS("OK: no rows past review_until."))
            return

        lines_out = []
        for c in rows:
            line = c.line
            ord_u = line.order.user.username if line.order.user_id else "?"
            lines_out.append(
                f"- #{c.pk} comandă #{line.order_id} {line.section}/{line.slot_code} "
                f"user={ord_u} review_until={c.review_until}"
            )
        text = "Materiale publicitate — fereastră verificare depășită:\n" + "\n".join(lines_out)
        self.stdout.write(text)

        if options.get("email"):
            recipients = _staff_recipient_emails()
            from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
            if recipients and from_email:
                subj = f"[EU-Adopt staff] Publicitate: {len(rows)} slot(uri) — verificare recomandată depășită"
                try:
                    send_mail_text_and_html(
                        subj,
                        text,
                        from_email,
                        recipients,
                        html_body=f"<pre style=\"white-space:pre-wrap\">{text}</pre>",
                        mail_kind="publicitate_creative_reminder",
                    )
                    self.stdout.write(self.style.SUCCESS(f"Email trimis la: {', '.join(recipients)}"))
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f"Email eșuat: {exc}"))
            else:
                self.stderr.write("No recipients (PUBLICITATE_CREATIVE_STAFF_EMAILS / ADMINS) or DEFAULT_FROM_EMAIL.")
