"""
Date și liste pentru panoul Analiza staff (/admin-analysis/).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from urllib.parse import quote, urlencode

from django.db.models import Model, Q
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model

from .models import (
    AccountProfile,
    AdoptionBonusSelection,
    AdoptionRequest,
    AnimalListing,
    CollaboratorServiceOffer,
    ContactMessage,
    PublicitateLineCreative,
    PublicitateOrder,
    TransportDispatchJob,
    TransportVeterinaryRequest,
)

ANALYSIS_DESC_MIN_LEN = 80
ANALYSIS_LIST_LIMIT = 100

# Chei filtru ?filter= pentru paginile Dogs / Requests / Users / Alerts
FILTER_ADOPTION_PENDING_48H = "adoption_pending_48h"
FILTER_TRANSPORT_OPEN = "transport_open"
FILTER_TRANSPORT_BLOCKED = "transport_blocked"
FILTER_TRANSPORT_MEDICAL = "transport_medical"
FILTER_ACCOUNTS_INACTIVE = "accounts_inactive"
FILTER_DOGS_NO_PHOTO = "dogs_no_photo"
FILTER_DOGS_NO_DESCRIPTION = "dogs_no_description"
FILTER_CATS_NO_PHOTO = "cats_no_photo"
FILTER_CATS_NO_DESCRIPTION = "cats_no_description"
FILTER_MODERATION = "moderation"
FILTER_BONUS_PENDING = "bonus_pending"
FILTER_EXPIRED_PARTNERS = "expired_partners"
FILTER_ADOPTION_PENDING = "adoption_pending"
FILTER_REQUESTS_IN_PROGRESS = "requests_in_progress"
FILTER_ADOPTION_RECENT_FINALIZED = "adoption_recent_finalized"

def _admin_change_url(model: type[Model], pk: int) -> str:
    meta = model._meta
    return reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=[pk])


def _filter_item(
    primary: str,
    secondary: str,
    *,
    action_url: str = "",
    action_label: str = "Deschide",
    action_new_tab: bool = False,
) -> dict[str, str | bool]:
    row: dict[str, str | bool] = {"primary": primary, "secondary": secondary}
    if action_url:
        row["action_url"] = action_url
        row["action_label"] = action_label
        row["action_new_tab"] = action_new_tab
    return row


def _mailto_action(email: str, subject: str, label: str = "Trimite email") -> tuple[str, str]:
    subj = quote(subject or "")
    return (f"mailto:{email}?subject={subj}", label)


FILTER_LABELS = {
    FILTER_ADOPTION_PENDING_48H: "Cereri adopție fără răspuns >48h",
    FILTER_TRANSPORT_OPEN: "Cereri transport fără răspuns",
    FILTER_TRANSPORT_BLOCKED: "Transporturi blocate",
    FILTER_TRANSPORT_MEDICAL: "Cereri medicale nepreluate",
    FILTER_ACCOUNTS_INACTIVE: "Conturi noi în așteptare",
    FILTER_DOGS_NO_PHOTO: "Câini publici fără poze complete",
    FILTER_DOGS_NO_DESCRIPTION: "Câini activi fără descriere insuficientă",
    FILTER_CATS_NO_PHOTO: "Pisici publice fără poze complete",
    FILTER_CATS_NO_DESCRIPTION: "Pisici active fără descriere insuficientă",
    FILTER_MODERATION: "Raportări moderare (Contact)",
    FILTER_BONUS_PENDING: "Beneficii adopție — bonus neexpediat",
    FILTER_EXPIRED_PARTNERS: "Oferte partener expirate (încă active)",
    FILTER_ADOPTION_PENDING: "Cereri adopție în așteptare",
    FILTER_REQUESTS_IN_PROGRESS: "Cereri în lucru (adopții acceptate + transport asignat)",
    FILTER_ADOPTION_RECENT_FINALIZED: "Adopții finalizate recent (30 zile)",
}


def _requests_filter_url(filter_key: str) -> str:
    return f"{reverse('admin_analysis_requests')}?{urlencode({'filter': filter_key})}"


def _cats_filter_url(filter_key: str) -> str:
    return f"{reverse('admin_analysis_cats')}?{urlencode({'filter': filter_key})}"


def _dogs_filter_url(filter_key: str) -> str:
    return f"{reverse('admin_analysis_dogs')}?{urlencode({'filter': filter_key})}"


def staff_analysis_requests_kpis() -> dict[str, int | float | None]:
    """KPI-uri rândul de sus — pagina Analiza / Requests."""
    adoption_total = AdoptionRequest.objects.count()
    transport_total = TransportVeterinaryRequest.objects.count()
    new_count = AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_PENDING).count()
    new_count += TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_OPEN).count()
    in_work = AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_ACCEPTED).count()
    in_work += TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_ASSIGNED).count()
    finalized = AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_FINALIZED).count()
    finalized += TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_COMPLETED).count()
    blocked = TransportDispatchJob.objects.filter(
        status__in=(TransportDispatchJob.STATUS_EXPIRED, TransportDispatchJob.STATUS_EXHAUSTED)
    ).count()
    blocked += AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_EXPIRED).count()

    avg_hours: float | None = None
    accepted = AdoptionRequest.objects.filter(
        accepted_at__isnull=False,
        status__in=(AdoptionRequest.STATUS_ACCEPTED, AdoptionRequest.STATUS_FINALIZED),
    ).only("created_at", "accepted_at")[:2000]
    deltas = []
    for ar in accepted:
        if ar.accepted_at and ar.created_at:
            deltas.append((ar.accepted_at - ar.created_at).total_seconds() / 3600.0)
    if deltas:
        avg_hours = round(sum(deltas) / len(deltas), 1)

    org_adoptions = AdoptionRequest.objects.filter(
        animal__owner__account_profile__role=AccountProfile.ROLE_ORG
    ).count()

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = AdoptionRequest.objects.filter(created_at__gte=month_start).count()
    this_month += TransportVeterinaryRequest.objects.filter(created_at__gte=month_start).count()

    return {
        "total": adoption_total + transport_total,
        "new": new_count,
        "in_work": in_work,
        "finalized": finalized,
        "blocked": blocked,
        "adoption_total": adoption_total,
        "transport_total": transport_total,
        "pending_adoptions": AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_PENDING).count(),
        "open_transport": count_transport_open(),
        "org_adoptions": org_adoptions,
        "this_month": this_month,
        "avg_response_hours": avg_hours,
    }


def staff_analysis_requests_page_context(filter_key: str | None) -> dict[str, Any]:
    """Context complet pentru /admin-analysis/requests/."""
    ctx = staff_analysis_filter_context(filter_key)
    kpis = staff_analysis_requests_kpis()
    ctx["requests_kpis"] = kpis
    ctx["requests_attention_rows"] = [
        {
            "label": "Cereri vechi nepreluate",
            "filter": FILTER_ADOPTION_PENDING_48H,
            "count": count_adoption_pending_48h(),
            "url": _requests_filter_url(FILTER_ADOPTION_PENDING_48H),
        },
        {
            "label": "Cereri fără răspuns (Adopții)",
            "filter": FILTER_ADOPTION_PENDING,
            "count": int(kpis["pending_adoptions"]),
            "url": _requests_filter_url(FILTER_ADOPTION_PENDING),
        },
        {
            "label": "Transport – cereri fără răspuns",
            "filter": FILTER_TRANSPORT_OPEN,
            "count": count_transport_open(),
            "url": _requests_filter_url(FILTER_TRANSPORT_OPEN),
        },
        {
            "label": "Medical – cereri nepreluate",
            "filter": FILTER_TRANSPORT_MEDICAL,
            "count": count_transport_medical_unprocessed(),
            "url": _requests_filter_url(FILTER_TRANSPORT_MEDICAL),
        },
        {
            "label": "Cereri blocate",
            "filter": FILTER_TRANSPORT_BLOCKED,
            "count": count_transport_blocked()
            + AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_EXPIRED).count(),
            "url": _requests_filter_url(FILTER_TRANSPORT_BLOCKED),
        },
    ]
    ctx["requests_useful_rows"] = [
        {
            "label": "Cereri recente finalizate",
            "filter": FILTER_ADOPTION_RECENT_FINALIZED,
            "count": AdoptionRequest.objects.filter(
                status=AdoptionRequest.STATUS_FINALIZED,
                finalized_at__gte=timezone.now() - timedelta(days=30),
            ).count(),
            "url": _requests_filter_url(FILTER_ADOPTION_RECENT_FINALIZED),
        },
        {
            "label": "Timp mediu răspuns (adopții acceptate)",
            "filter": "",
            "count": None,
            "url": "",
            "hint": (
                f"{kpis['avg_response_hours']} h"
                if kpis.get("avg_response_hours") is not None
                else "—"
            ),
        },
        {
            "label": "Adopții noi / în lucru",
            "filter": FILTER_ADOPTION_PENDING,
            "count": int(kpis["pending_adoptions"]),
            "url": _requests_filter_url(FILTER_ADOPTION_PENDING),
        },
        {
            "label": "Transport – cele mai vechi deschise",
            "filter": FILTER_TRANSPORT_OPEN,
            "count": count_transport_open(),
            "url": _requests_filter_url(FILTER_TRANSPORT_OPEN),
        },
    ]
    avg = kpis.get("avg_response_hours")
    ctx["requests_dist_lines"] = [
        f"Adopții {kpis['adoption_total']} · Transport {kpis['transport_total']}",
        (
            f"În așteptare {kpis['pending_adoptions']} · "
            f"Deschise {kpis['open_transport']} · "
            f"În lucru {kpis['in_work']}"
        ),
        f"Luna curentă: {kpis['this_month']} cereri noi",
        f"ONG (cereri adopție): {kpis['org_adoptions']}",
        f"Timp mediu răspuns adopție: {avg} h" if avg is not None else "Timp mediu răspuns: —",
    ]
    ctx["requests_kpi_links"] = {
        "new": _requests_filter_url(FILTER_ADOPTION_PENDING),
        "in_work": _requests_filter_url(FILTER_REQUESTS_IN_PROGRESS),
        "finalized": _requests_filter_url(FILTER_ADOPTION_RECENT_FINALIZED),
        "blocked": _requests_filter_url(FILTER_TRANSPORT_BLOCKED),
    }
    return ctx


def _published_dog_q() -> Q:
    return Q(is_published=True, species="dog") & ~Q(adoption_state=AnimalListing.ADOPTION_STATE_ADOPTED)


def _published_cat_q() -> Q:
    return Q(is_published=True, species="cat") & ~Q(adoption_state=AnimalListing.ADOPTION_STATE_ADOPTED)


def _listing_missing_photo_q() -> Q:
    return Q(photo_1__isnull=True) | Q(photo_1="") | Q(photo_2__isnull=True) | Q(photo_2="") | Q(
        photo_3__isnull=True
    ) | Q(photo_3="")


def count_adoption_pending_48h(now=None) -> int:
    now = now or timezone.now()
    return AdoptionRequest.objects.filter(
        status=AdoptionRequest.STATUS_PENDING,
        created_at__lt=now - timedelta(hours=48),
    ).count()


def count_transport_open() -> int:
    return TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_OPEN).count()


def count_transport_blocked() -> int:
    return TransportDispatchJob.objects.filter(
        status__in=(TransportDispatchJob.STATUS_EXPIRED, TransportDispatchJob.STATUS_EXHAUSTED)
    ).count()


def count_transport_medical_unprocessed(now=None) -> int:
    now = now or timezone.now()
    threshold = now - timedelta(hours=24)
    no_job = TransportVeterinaryRequest.objects.filter(dispatch_job__isnull=True).count()
    stale_open = TransportVeterinaryRequest.objects.filter(
        dispatch_job__status=TransportDispatchJob.STATUS_OPEN,
        created_at__lt=threshold,
    ).count()
    return no_job + stale_open


def count_accounts_inactive() -> int:
    User = get_user_model()
    return User.objects.filter(is_active=False, is_staff=False).count()


def count_dogs_no_photo() -> int:
    return AnimalListing.objects.filter(_published_dog_q()).filter(_listing_missing_photo_q()).count()


def count_dogs_no_description() -> int:
    return _count_thin_description(_published_dog_q())


def count_cats_no_photo() -> int:
    return AnimalListing.objects.filter(_published_cat_q()).filter(_listing_missing_photo_q()).count()


def count_cats_no_description() -> int:
    return _count_thin_description(_published_cat_q())


def _count_thin_description(species_q: Q) -> int:
    qs = AnimalListing.objects.filter(species_q)
    n = 0
    for row in qs.only("detalii_animal", "cine_sunt")[:5000]:
        text = f"{(row.detalii_animal or '').strip()} {(row.cine_sunt or '').strip()}".strip()
        if len(text) < ANALYSIS_DESC_MIN_LEN:
            n += 1
    return n


def count_moderation_reports() -> int:
    return ContactMessage.objects.filter(topic=ContactMessage.TOPIC_MODERATION).count()


def count_bonus_pending() -> int:
    return AdoptionBonusSelection.objects.filter(bonus_emails_sent_at__isnull=True).count()


def count_expired_partners(today=None) -> int:
    today = today or timezone.localdate()
    offers = CollaboratorServiceOffer.objects.filter(
        is_active=True,
        valid_until__isnull=False,
        valid_until__lt=today,
    ).count()
    pub_pending = PublicitateLineCreative.objects.filter(
        status=PublicitateLineCreative.STATUS_PENDING,
        line__order__status=PublicitateOrder.STATUS_PAID,
    ).count()
    return offers + pub_pending


def staff_analysis_home_alert_rows() -> list[dict[str, Any]]:
    """Rânduri panou Alerte — număr, link (?filter=), tooltip."""
    now = timezone.now()

    def _url(view_name: str, filter_key: str) -> str:
        base = reverse(view_name)
        return f"{base}?{urlencode({'filter': filter_key})}"

    rows_spec = [
        (
            "critical",
            "CRITIC",
            "Cereri adopție fără răspuns >48h",
            count_adoption_pending_48h(now),
            _url("admin_analysis_requests", FILTER_ADOPTION_PENDING_48H),
            "Cereri în așteptare (proprietar) de peste 48h — vezi lista Cereri",
        ),
        (
            "critical",
            "CRITIC",
            "Cereri transport fără răspuns",
            count_transport_open(),
            _url("admin_analysis_requests", FILTER_TRANSPORT_OPEN),
            "Job-uri dispatch deschise, fără transportator asignat",
        ),
        (
            "critical",
            "CRITIC",
            "Transporturi blocate",
            count_transport_blocked(),
            _url("admin_analysis_requests", FILTER_TRANSPORT_BLOCKED),
            "Dispatch expirat sau fără transportatori disponibili",
        ),
        (
            "critical",
            "CRITIC",
            "Cereri medicale nepreluate",
            count_transport_medical_unprocessed(now),
            _url("admin_analysis_requests", FILTER_TRANSPORT_MEDICAL),
            "Cereri transport veterinar fără job sau deschise de peste 24h",
        ),
        (
            "medium",
            "MEDIU",
            "Conturi noi în așteptare verificare/aprobare",
            count_accounts_inactive(),
            _url("admin_analysis_users", FILTER_ACCOUNTS_INACTIVE),
            "Conturi create, email neconfirmat (is_active=False)",
        ),
        (
            "medium",
            "MEDIU",
            "Câini publici fără poze complete",
            count_dogs_no_photo(),
            _url("admin_analysis_dogs", FILTER_DOGS_NO_PHOTO),
            "Câini publicați activi cu cel puțin o poză lipsă (1–3)",
        ),
        (
            "medium",
            "MEDIU",
            "Câini activi fără descriere suficientă",
            count_dogs_no_description(),
            _url("admin_analysis_dogs", FILTER_DOGS_NO_DESCRIPTION),
            f"Text combinat detalii + poveste sub {ANALYSIS_DESC_MIN_LEN} caractere",
        ),
        (
            "medium",
            "MEDIU",
            "Utilizatori raportați / problematici",
            count_moderation_reports(),
            _url("admin_analysis_alerts", FILTER_MODERATION),
            "Mesaje Contact cu tip Moderare / raportări",
        ),
        (
            "biz",
            "BUSINESS",
            "Beneficii / PIN-uri nevalidate",
            count_bonus_pending(),
            _url("admin_analysis_alerts", FILTER_BONUS_PENDING),
            "Selecții bonus adopție fără emailuri trimise către parteneri",
        ),
        (
            "biz",
            "BUSINESS",
            "Sponsori / parteneri expirați",
            count_expired_partners(),
            _url("admin_analysis_alerts", FILTER_EXPIRED_PARTNERS),
            "Oferte colaborator expirate (încă marcate active) + materiale pub neîncărcate",
        ),
    ]
    out = []
    for tag_cls, tag_label, text, count, url, title in rows_spec:
        out.append(
            {
                "tag_class": tag_cls,
                "tag_label": tag_label,
                "text": text,
                "count": count,
                "url": url,
                "title": title,
                "count_hot": count > 0,
            }
        )
    return out


def staff_analysis_dogs_page_context(filter_key: str | None) -> dict[str, Any]:
    """Context pentru /admin-analysis/dogs/."""
    ctx = staff_analysis_filter_context(filter_key)
    ctx["dogs_attention_rows"] = [
        {
            "label": "Câini fără poză principală",
            "url": _dogs_filter_url(FILTER_DOGS_NO_PHOTO),
            "count": count_dogs_no_photo(),
        },
        {
            "label": "Câini fără descriere suficientă",
            "url": _dogs_filter_url(FILTER_DOGS_NO_DESCRIPTION),
            "count": count_dogs_no_description(),
        },
    ]
    return ctx


def staff_analysis_cats_page_context(filter_key: str | None) -> dict[str, Any]:
    """Context pentru /admin-analysis/cats/."""
    ctx = staff_analysis_filter_context(filter_key)
    ctx["cats_attention_rows"] = [
        {
            "label": "Pisici fără poză principală",
            "url": _cats_filter_url(FILTER_CATS_NO_PHOTO),
            "count": count_cats_no_photo(),
        },
        {
            "label": "Pisici fără descriere suficientă",
            "url": _cats_filter_url(FILTER_CATS_NO_DESCRIPTION),
            "count": count_cats_no_description(),
        },
    ]
    return ctx


def staff_analysis_filter_context(filter_key: str | None) -> dict[str, Any]:
    """Listă detaliu pentru paginile Câini/Pisici/Cereri/Utilizatori/Alerte (?filter=)."""
    if not filter_key or filter_key not in FILTER_LABELS:
        return {
            "analysis_filter": None,
            "analysis_filter_label": "",
            "analysis_filter_items": [],
            "analysis_filter_total": 0,
        }

    items: list[dict[str, str | bool]] = []
    User = get_user_model()
    now = timezone.now()

    if filter_key == FILTER_ADOPTION_PENDING_48H:
        qs = (
            AdoptionRequest.objects.filter(
                status=AdoptionRequest.STATUS_PENDING,
                created_at__lt=now - timedelta(hours=48),
            )
            .select_related("animal", "adopter")
            .order_by("created_at")[:ANALYSIS_LIST_LIMIT]
        )
        for ar in qs:
            pet = ar.animal.name or f"#{ar.animal_id}"
            items.append(
                _filter_item(
                    f"#{ar.pk} — {pet}",
                    f"{ar.adopter.email or ar.adopter.username} · {ar.created_at:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(AdoptionRequest, ar.pk),
                    action_label="Admin — cerere adopție",
                )
            )

    elif filter_key == FILTER_ADOPTION_PENDING:
        qs = (
            AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_PENDING)
            .select_related("animal", "adopter")
            .order_by("-created_at")[:ANALYSIS_LIST_LIMIT]
        )
        for ar in qs:
            pet = ar.animal.name or f"#{ar.animal_id}"
            items.append(
                _filter_item(
                    f"#{ar.pk} — {pet}",
                    f"{ar.adopter.email or ar.adopter.username} · {ar.created_at:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(AdoptionRequest, ar.pk),
                    action_label="Admin — cerere adopție",
                )
            )

    elif filter_key == FILTER_REQUESTS_IN_PROGRESS:
        for ar in (
            AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_ACCEPTED)
            .select_related("animal", "adopter")
            .order_by("-accepted_at")[:ANALYSIS_LIST_LIMIT]
        ):
            pet = ar.animal.name or f"#{ar.animal_id}"
            items.append(
                _filter_item(
                    f"Adopție #{ar.pk} — {pet}",
                    f"Acceptată · {ar.accepted_at:%d.%m.%Y %H:%M}" if ar.accepted_at else "Acceptată",
                    action_url=_admin_change_url(AdoptionRequest, ar.pk),
                    action_label="Admin — cerere adopție",
                )
            )
        remaining = ANALYSIS_LIST_LIMIT - len(items)
        if remaining > 0:
            for job in (
                TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_ASSIGNED)
                .select_related("tvr", "assigned_transporter")
                .order_by("-assigned_at")[:remaining]
            ):
                tvr = job.tvr
                op = job.assigned_transporter
                items.append(
                    _filter_item(
                        f"Transport #{job.pk} — {tvr.judet}/{tvr.oras}",
                        f"Asignat {op.email if op else '—'} · {job.assigned_at:%d.%m.%Y %H:%M}"
                        if job.assigned_at
                        else "Asignat",
                        action_url=_admin_change_url(TransportDispatchJob, job.pk),
                        action_label="Admin — dispatch",
                    )
                )

    elif filter_key == FILTER_ADOPTION_RECENT_FINALIZED:
        qs = (
            AdoptionRequest.objects.filter(
                status=AdoptionRequest.STATUS_FINALIZED,
                finalized_at__gte=now - timedelta(days=30),
            )
            .select_related("animal", "adopter")
            .order_by("-finalized_at")[:ANALYSIS_LIST_LIMIT]
        )
        for ar in qs:
            pet = ar.animal.name or f"#{ar.animal_id}"
            items.append(
                _filter_item(
                    f"#{ar.pk} — {pet}",
                    f"Finalizată {ar.finalized_at:%d.%m.%Y %H:%M}" if ar.finalized_at else "Finalizată",
                    action_url=_admin_change_url(AdoptionRequest, ar.pk),
                    action_label="Admin — cerere adopție",
                )
            )

    elif filter_key == FILTER_TRANSPORT_OPEN:
        qs = (
            TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_OPEN)
            .select_related("tvr", "assigned_transporter")
            .order_by("-created_at")[:ANALYSIS_LIST_LIMIT]
        )
        for job in qs:
            tvr = job.tvr
            items.append(
                _filter_item(
                    f"Dispatch #{job.pk} — {tvr.judet}/{tvr.oras}",
                    f"Creat {job.created_at:%d.%m.%Y %H:%M}"
                    + (f" · expiră {job.expires_at:%d.%m.%Y %H:%M}" if job.expires_at else ""),
                    action_url=_admin_change_url(TransportDispatchJob, job.pk),
                    action_label="Admin — dispatch",
                )
            )

    elif filter_key == FILTER_TRANSPORT_BLOCKED:
        qs = (
            TransportDispatchJob.objects.filter(
                status__in=(TransportDispatchJob.STATUS_EXPIRED, TransportDispatchJob.STATUS_EXHAUSTED)
            )
            .select_related("tvr")
            .order_by("-updated_at")[:ANALYSIS_LIST_LIMIT]
        )
        for job in qs:
            items.append(
                _filter_item(
                    f"Dispatch #{job.pk} [{job.get_status_display()}]",
                    f"{job.tvr.judet}/{job.tvr.oras} · actualizat {job.updated_at:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(TransportDispatchJob, job.pk),
                    action_label="Admin — dispatch",
                )
            )

    elif filter_key == FILTER_TRANSPORT_MEDICAL:
        threshold = now - timedelta(hours=24)
        seen = set()
        for tvr in (
            TransportVeterinaryRequest.objects.filter(dispatch_job__isnull=True)
            .order_by("-created_at")[:ANALYSIS_LIST_LIMIT]
        ):
            seen.add(tvr.pk)
            items.append(
                _filter_item(
                    f"TVR #{tvr.pk} — {tvr.judet}/{tvr.oras}",
                    f"Fără job dispatch · {tvr.created_at:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(TransportVeterinaryRequest, tvr.pk),
                    action_label="Admin — cerere transport",
                )
            )
        for tvr in (
            TransportVeterinaryRequest.objects.filter(
                dispatch_job__status=TransportDispatchJob.STATUS_OPEN,
                created_at__lt=threshold,
            )
            .select_related("dispatch_job")
            .order_by("created_at")[:ANALYSIS_LIST_LIMIT]
        ):
            if tvr.pk in seen:
                continue
            seen.add(tvr.pk)
            items.append(
                _filter_item(
                    f"TVR #{tvr.pk} — {tvr.judet}/{tvr.oras}",
                    f"Dispatch deschis >24h · {tvr.created_at:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(TransportVeterinaryRequest, tvr.pk),
                    action_label="Admin — cerere transport",
                )
            )

    elif filter_key == FILTER_ACCOUNTS_INACTIVE:
        qs = User.objects.filter(is_active=False, is_staff=False).order_by("-date_joined")[:ANALYSIS_LIST_LIMIT]
        for u in qs:
            items.append(
                _filter_item(
                    u.email or u.username,
                    f"Înregistrat {u.date_joined:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(User, u.pk),
                    action_label="Admin — cont utilizator",
                )
            )

    elif filter_key == FILTER_DOGS_NO_PHOTO:
        qs = (
            AnimalListing.objects.filter(_published_dog_q())
            .filter(_listing_missing_photo_q())
            .select_related("owner")
            .order_by("-updated_at")[:ANALYSIS_LIST_LIMIT]
        )
        for listing in qs:
            missing = []
            if not listing.photo_1:
                missing.append("poza 1")
            if not listing.photo_2:
                missing.append("poza 2")
            if not listing.photo_3:
                missing.append("poza 3")
            items.append(
                _filter_item(
                    listing.name or f"Anunț #{listing.pk}",
                    f"Lipsă: {', '.join(missing)} · {listing.owner.email or listing.owner.username}",
                    action_url=reverse("pets_single", args=[listing.pk]),
                    action_label="Vezi anunț public",
                    action_new_tab=True,
                )
            )

    elif filter_key == FILTER_DOGS_NO_DESCRIPTION:
        qs = AnimalListing.objects.filter(_published_dog_q()).select_related("owner").order_by("-updated_at")
        for listing in qs[:5000]:
            if len(items) >= ANALYSIS_LIST_LIMIT:
                break
            text = f"{(listing.detalii_animal or '').strip()} {(listing.cine_sunt or '').strip()}".strip()
            if len(text) < ANALYSIS_DESC_MIN_LEN:
                items.append(
                    _filter_item(
                        listing.name or f"Anunț #{listing.pk}",
                        f"{len(text)} caractere · {listing.owner.email or listing.owner.username}",
                        action_url=reverse("pets_single", args=[listing.pk]),
                        action_label="Vezi anunț public",
                        action_new_tab=True,
                    )
                )

    elif filter_key == FILTER_CATS_NO_PHOTO:
        qs = (
            AnimalListing.objects.filter(_published_cat_q())
            .filter(_listing_missing_photo_q())
            .select_related("owner")
            .order_by("-updated_at")[:ANALYSIS_LIST_LIMIT]
        )
        for listing in qs:
            missing = []
            if not listing.photo_1:
                missing.append("poza 1")
            if not listing.photo_2:
                missing.append("poza 2")
            if not listing.photo_3:
                missing.append("poza 3")
            items.append(
                _filter_item(
                    listing.name or f"Anunț #{listing.pk}",
                    f"Lipsă: {', '.join(missing)} · {listing.owner.email or listing.owner.username}",
                    action_url=reverse("pets_single", args=[listing.pk]),
                    action_label="Vezi anunț public",
                    action_new_tab=True,
                )
            )

    elif filter_key == FILTER_CATS_NO_DESCRIPTION:
        qs = AnimalListing.objects.filter(_published_cat_q()).select_related("owner").order_by("-updated_at")
        for listing in qs[:5000]:
            if len(items) >= ANALYSIS_LIST_LIMIT:
                break
            text = f"{(listing.detalii_animal or '').strip()} {(listing.cine_sunt or '').strip()}".strip()
            if len(text) < ANALYSIS_DESC_MIN_LEN:
                items.append(
                    _filter_item(
                        listing.name or f"Anunț #{listing.pk}",
                        f"{len(text)} caractere · {listing.owner.email or listing.owner.username}",
                        action_url=reverse("pets_single", args=[listing.pk]),
                        action_label="Vezi anunț public",
                        action_new_tab=True,
                    )
                )

    elif filter_key == FILTER_MODERATION:
        qs = ContactMessage.objects.filter(topic=ContactMessage.TOPIC_MODERATION).order_by("-created_at")[
            :ANALYSIS_LIST_LIMIT
        ]
        for msg in qs:
            mail_url, mail_label = _mailto_action(
                msg.email,
                f"EU-Adopt moderare #{msg.pk}: {msg.subject[:60]}",
            )
            items.append(
                _filter_item(
                    msg.subject[:120],
                    f"{msg.full_name} · {msg.email} · {msg.created_at:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(ContactMessage, msg.pk),
                    action_label="Admin — mesaj",
                )
            )
            items[-1]["action_url_secondary"] = mail_url
            items[-1]["action_label_secondary"] = mail_label

    elif filter_key == FILTER_BONUS_PENDING:
        qs = (
            AdoptionBonusSelection.objects.filter(bonus_emails_sent_at__isnull=True)
            .select_related("adoption_request", "offer")
            .order_by("-created_at")[:ANALYSIS_LIST_LIMIT]
        )
        for sel in qs:
            ar = sel.adoption_request
            items.append(
                _filter_item(
                    f"Bonus AR#{ar.pk} — {sel.offer.title[:80]}",
                    f"Stare cerere: {ar.get_status_display()} · {sel.created_at:%d.%m.%Y %H:%M}",
                    action_url=_admin_change_url(AdoptionRequest, ar.pk),
                    action_label="Admin — cerere adopție",
                )
            )

    elif filter_key == FILTER_EXPIRED_PARTNERS:
        today = timezone.localdate()
        for offer in (
            CollaboratorServiceOffer.objects.filter(
                is_active=True,
                valid_until__isnull=False,
                valid_until__lt=today,
            )
            .select_related("collaborator")
            .order_by("valid_until")[:ANALYSIS_LIST_LIMIT]
        ):
            items.append(
                _filter_item(
                    offer.title[:100],
                    f"Expirat {offer.valid_until:%d.%m.%Y} · {offer.collaborator.email or offer.collaborator.username}",
                    action_url=_admin_change_url(CollaboratorServiceOffer, offer.pk),
                    action_label="Admin — ofertă",
                )
            )
        remaining = ANALYSIS_LIST_LIMIT - len(items)
        if remaining > 0:
            for creative in (
                PublicitateLineCreative.objects.filter(
                    status=PublicitateLineCreative.STATUS_PENDING,
                    line__order__status=PublicitateOrder.STATUS_PAID,
                )
                .select_related("line", "line__order")
                .order_by("-submitted_at", "-line__order__paid_at")[:remaining]
            ):
                line = creative.line
                items.append(
                    _filter_item(
                        f"Pub comandă #{line.order_id} — {line.section}/{line.slot_code}",
                        "Materiale creative neîncărcate (comandă plătită)",
                        action_url=_admin_change_url(PublicitateOrder, line.order_id),
                        action_label="Admin — comandă pub",
                    )
                )

    total = len(items)
    if filter_key in (
        FILTER_ADOPTION_PENDING_48H,
        FILTER_ADOPTION_PENDING,
        FILTER_TRANSPORT_OPEN,
        FILTER_TRANSPORT_BLOCKED,
        FILTER_ACCOUNTS_INACTIVE,
        FILTER_MODERATION,
        FILTER_BONUS_PENDING,
    ):
        counters = {
            FILTER_ADOPTION_PENDING_48H: count_adoption_pending_48h,
            FILTER_ADOPTION_PENDING: lambda: AdoptionRequest.objects.filter(
                status=AdoptionRequest.STATUS_PENDING
            ).count(),
            FILTER_TRANSPORT_OPEN: count_transport_open,
            FILTER_TRANSPORT_BLOCKED: count_transport_blocked,
            FILTER_ACCOUNTS_INACTIVE: count_accounts_inactive,
            FILTER_MODERATION: count_moderation_reports,
            FILTER_BONUS_PENDING: count_bonus_pending,
        }
        if filter_key in counters:
            total = counters[filter_key]()
    elif filter_key == FILTER_REQUESTS_IN_PROGRESS:
        total = (
            AdoptionRequest.objects.filter(status=AdoptionRequest.STATUS_ACCEPTED).count()
            + TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_ASSIGNED).count()
        )
    elif filter_key == FILTER_ADOPTION_RECENT_FINALIZED:
        total = AdoptionRequest.objects.filter(
            status=AdoptionRequest.STATUS_FINALIZED,
            finalized_at__gte=now - timedelta(days=30),
        ).count()
    elif filter_key == FILTER_TRANSPORT_MEDICAL:
        total = count_transport_medical_unprocessed()
    elif filter_key == FILTER_DOGS_NO_PHOTO:
        total = count_dogs_no_photo()
    elif filter_key == FILTER_DOGS_NO_DESCRIPTION:
        total = count_dogs_no_description()
    elif filter_key == FILTER_CATS_NO_PHOTO:
        total = count_cats_no_photo()
    elif filter_key == FILTER_CATS_NO_DESCRIPTION:
        total = count_cats_no_description()
    elif filter_key == FILTER_EXPIRED_PARTNERS:
        total = count_expired_partners()

    return {
        "analysis_filter": filter_key,
        "analysis_filter_label": FILTER_LABELS[filter_key],
        "analysis_filter_items": items,
        "analysis_filter_total": total,
        "analysis_filter_truncated": total > len(items),
    }
