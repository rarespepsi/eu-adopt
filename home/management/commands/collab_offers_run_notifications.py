"""
Rulează zilnic (cron): dezactivează oferte expirate; trimite max. 1 mail T−5 zile / perioadă
valid_until și max. 1 mail stoc 1 rămas / ciclu stoc (reset la edit fișă).
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from home.models import CollaboratorServiceOffer

logger = logging.getLogger(__name__)


def _ro_today():
    return timezone.localdate()


def _collab_offer_is_valid_today(offer) -> bool:
    today = _ro_today()
    if offer.valid_from is not None and today < offer.valid_from:
        return False
    if offer.valid_until is not None and today > offer.valid_until:
        return False
    return True


def _control_url() -> str:
    path = reverse("collab_offers_control")
    base = getattr(settings, "SITE_BASE_URL", "") or ""
    base = base.rstrip("/")
    return f"{base}{path}" if base else path


class Command(BaseCommand):
    help = (
        "Dezactivează oferte cu valid_until în trecut; trimite remindere email "
        "(expirare în 5 zile, stoc 1 rămas) cu deduplicare pe model."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează ce s-ar face fără a scrie DB sau a trimite email.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        today = _ro_today()
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"

        # 1) Expirate → inactive (nu mai apar în Servicii / listări publice)
        expired_qs = CollaboratorServiceOffer.objects.filter(
            is_active=True,
            valid_until__isnull=False,
            valid_until__lt=today,
        )
        n_exp = expired_qs.count()
        if dry:
            self.stdout.write(f"[dry-run] Would deactivate {n_exp} expired offer(s).")
        else:
            updated = expired_qs.update(is_active=False)
            self.stdout.write(self.style.SUCCESS(f"Deactivated {updated} expired offer(s)."))

        # 2) Mail: exact 5 zile înainte de valid_until (ofertă încă activă și în fereastră)
        offers_exp = (
            CollaboratorServiceOffer.objects.filter(is_active=True, valid_until__isnull=False)
            .select_related("collaborator")
            .iterator(chunk_size=100)
        )
        sent_exp = 0
        for o in offers_exp:
            if not _collab_offer_is_valid_today(o):
                continue
            if (o.valid_until - today) != timedelta(days=5):
                continue
            if o.expiry_notice_sent_for_valid_until == o.valid_until:
                continue
            to = (getattr(o.collaborator, "email", None) or "").strip()
            if not to:
                logger.warning("collab_offer_expiry_mail skip offer=%s no email", o.pk)
                continue
            subj = f"EU-Adopt: oferta „{o.title}” expiră în 5 zile"
            vu = o.valid_until.strftime("%d.%m.%Y")
            vf = o.valid_from.strftime("%d.%m.%Y") if o.valid_from else "—"
            link = _control_url()
            body = (
                f"Bună ziua,\n\n"
                f"Oferta ta „{o.title}” are valabilitate până la {vu} (început: {vf}).\n"
                f"Dacă nu prelungești perioada din contul colaborator (Magazinul meu → Oferte), "
                f"după această dată oferta va fi scoasă automat din Servicii și va rămâne în lista ta ca inactivă.\n\n"
                f"Link gestionare oferte: {link}\n\n"
                f"— Aplicația EU-Adopt\n"
            )
            if dry:
                self.stdout.write(f"[dry-run] Expiry mail → {to} offer pk={o.pk}")
            else:
                try:
                    send_mail(subj, body, from_email, [to], fail_silently=False)
                    CollaboratorServiceOffer.objects.filter(pk=o.pk).update(
                        expiry_notice_sent_for_valid_until=o.valid_until
                    )
                    sent_exp += 1
                except Exception:
                    logger.exception("collab_offer_expiry_mail fail offer=%s", o.pk)
        self.stdout.write(f"Expiry reminder emails sent: {sent_exp}")

        # 3) Mail: stoc — rămâne 1 loc, inițial erau > 1 oferte bifate
        offers_stock = (
            CollaboratorServiceOffer.objects.filter(
                is_active=True,
                low_stock_notice_sent=False,
                quantity_available__gt=1,
            )
            .annotate(cc=Count("claims"))
            .select_related("collaborator")
            .iterator(chunk_size=100)
        )
        sent_st = 0
        for o in offers_stock:
            if not _collab_offer_is_valid_today(o):
                continue
            rem = int(o.quantity_available) - int(o.cc)
            if rem != 1:
                continue
            to = (getattr(o.collaborator, "email", None) or "").strip()
            if not to:
                logger.warning("collab_offer_low_stock_mail skip offer=%s no email", o.pk)
                continue
            subj = f"EU-Adopt: oferta „{o.title}” — mai ai 1 loc disponibil"
            link = _control_url()
            body = (
                f"Bună ziua,\n\n"
                f"Pentru oferta „{o.title}” mai este disponibil un singur loc din stocul setat. "
                f"Dacă vrei să continui vânzările fără întrerupere, poți mări numărul de oferte din fișa ofertei — "
                f"doar dacă dorești.\n\n"
                f"Link gestionare: {link}\n\n"
                f"— Aplicația EU-Adopt\n"
            )
            if dry:
                self.stdout.write(f"[dry-run] Low-stock mail → {to} offer pk={o.pk}")
            else:
                try:
                    send_mail(subj, body, from_email, [to], fail_silently=False)
                    CollaboratorServiceOffer.objects.filter(pk=o.pk).update(low_stock_notice_sent=True)
                    sent_st += 1
                except Exception:
                    logger.exception("collab_offer_low_stock_mail fail offer=%s", o.pk)
        self.stdout.write(f"Low-stock reminder emails sent: {sent_st}")
