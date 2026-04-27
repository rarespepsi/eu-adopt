"""
Logică dispatch transport: eligibilitate, creare job, notificări email, accept, anulare, re-ofertă.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from html import escape as html_escape
from typing import List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .mail_helpers import email_subject_for_user
from .inbox_notifications import (
    KIND_TRANSPORT_ASSIGNED_CLIENT,
    KIND_TRANSPORT_ASSIGNED_OPERATOR,
    KIND_TRANSPORT_CANCELLED_USER,
    KIND_TRANSPORT_COMPLETED,
    KIND_TRANSPORT_DISPATCH_OPEN,
    KIND_TRANSPORT_EXHAUSTED,
    KIND_TRANSPORT_EXPIRED,
    KIND_TRANSPORT_INVITE_OPERATOR,
    KIND_TRANSPORT_NO_TRANSPORTERS,
    KIND_TRANSPORT_REOPENED,
    create_inbox_notification,
    reverse_safe,
)
from .models import (
    TransportDispatchJob,
    TransportDispatchRecipient,
    TransportOperatorProfile,
    TransportTripRating,
    TransportVeterinaryRequest,
    UserProfile,
)

logger = logging.getLogger(__name__)
User = get_user_model()
signer = TimestampSigner()


def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _transporter_is_eligible(
    top: TransportOperatorProfile,
    tvr: TransportVeterinaryRequest,
) -> bool:
    if top.approval_status != TransportOperatorProfile.APPROVAL_APPROVED:
        return False
    if top.removed_after_third_block:
        return False
    now = timezone.now()
    if top.blocked_until and top.blocked_until > now:
        return False
    scope = (tvr.route_scope or TransportVeterinaryRequest.ROUTE_NATIONAL).strip()
    if scope == TransportVeterinaryRequest.ROUTE_INTERNATIONAL:
        return bool(top.transport_international)
    if not top.transport_national:
        return False
    try:
        prof: UserProfile = top.user.profile
    except Exception:
        return False
    cj = _norm(prof.company_judet or prof.judet or "")
    co = _norm(prof.company_oras or prof.oras or "")
    return _norm(tvr.judet) == cj and _norm(tvr.oras) == co


def eligible_transporter_users(tvr: TransportVeterinaryRequest) -> List[User]:
    tops = (
        TransportOperatorProfile.objects.select_related("user")
        .filter(user__is_active=True)
        .all()
    )
    out: List[User] = []
    for top in tops:
        if _transporter_is_eligible(top, tvr):
            out.append(top.user)
    return out


def _expires_at_for_tvr(tvr: TransportVeterinaryRequest) -> Optional[timezone.datetime]:
    u = (tvr.urgency_window or TransportVeterinaryRequest.URGENCY_FLEX).strip()
    now = timezone.now()
    if u == TransportVeterinaryRequest.URGENCY_FLEX:
        return None
    if u == TransportVeterinaryRequest.URGENCY_24H:
        return now + timedelta(hours=24)
    if u == TransportVeterinaryRequest.URGENCY_TODAY:
        # Sfârșitul zilei locale (Europe/Bucharest în settings)
        local = timezone.localtime(now)
        end = local.replace(hour=23, minute=59, second=59, microsecond=999999)
        return end if end > now else now + timedelta(hours=1)
    return None


def _notify_transporters_dispatch_invite(request, tvr: TransportVeterinaryRequest, job: TransportDispatchJob, users: List[User]) -> None:
    """Notificare inbox + plic navbar pentru fiecare transportator invitat (nu doar email)."""
    panel_url = reverse_safe("transport_operator_panel")
    summary = f"Cerere #{tvr.pk} · job #{job.pk} · {tvr.judet or '—'} / {tvr.oras or '—'}"
    for u in users:
        if not u:
            continue
        create_inbox_notification(
            u,
            KIND_TRANSPORT_INVITE_OPERATOR,
            "Ofertă nouă de transport",
            f"{summary}. Răspunde din email sau deschide My transport.",
            link_url=panel_url,
            metadata={"tvr_id": tvr.pk, "job_id": job.pk},
        )


def _absolute(request, path: str) -> str:
    if request is None:
        base = (getattr(settings, "SITE_URL", None) or "").rstrip("/")
        return f"{base}{path}" if base else path
    return request.build_absolute_uri(path)


def make_token(action: str, job_id: int, user_id: int) -> str:
    return signer.sign(f"{action}:{job_id}:{user_id}")


def parse_token(token: str, max_age: int = 86400 * 14) -> Optional[tuple[str, int, int]]:
    try:
        raw = signer.unsign(token, max_age=max_age)
        parts = raw.split(":")
        if len(parts) != 3:
            return None
        action, jid, uid = parts[0], int(parts[1]), int(parts[2])
        return action, jid, uid
    except (BadSignature, SignatureExpired, ValueError):
        return None


def create_dispatch_for_tvr(request, tvr: TransportVeterinaryRequest) -> Optional[TransportDispatchJob]:
    """
    Creează job + destinatari + trimite emailuri. Dacă nu există transportatori, marchează exhausted și notifică userul.
    """
    if not tvr.user_id:
        return None
    users = eligible_transporter_users(tvr)
    if not users:
        job = TransportDispatchJob.objects.create(
            tvr=tvr,
            status=TransportDispatchJob.STATUS_EXHAUSTED,
            expires_at=None,
        )
        _email_user_no_transporters(request, tvr, job)
        u = tvr.user
        if u:
            create_inbox_notification(
                u,
                KIND_TRANSPORT_NO_TRANSPORTERS,
                "Transport: nu există transportatori în zonă",
                f"Cererea #{tvr.pk} nu poate fi repartizată momentan. Poți încerca din nou mai târziu.",
                link_url=reverse_safe("transport"),
                metadata={"tvr_id": tvr.pk, "job_id": job.pk},
            )
        return job

    exp = _expires_at_for_tvr(tvr)
    with transaction.atomic():
        job = TransportDispatchJob.objects.create(
            tvr=tvr,
            status=TransportDispatchJob.STATUS_OPEN,
            expires_at=exp,
        )
        for u in users:
            TransportDispatchRecipient.objects.create(
                job=job,
                transporter=u,
                status=TransportDispatchRecipient.ST_PENDING,
            )
    for u in users:
        _email_transporter_new_offer(request, tvr, job, u)
    _notify_transporters_dispatch_invite(request, tvr, job, users)
    _email_user_request_received(request, tvr, job)
    if tvr.user:
        create_inbox_notification(
            tvr.user,
            KIND_TRANSPORT_DISPATCH_OPEN,
            "Cererea ta de transport a fost trimisă",
            f"Cerere #{tvr.pk}: am notificat transportatorii eligibili. Primul care acceptă preia comanda.",
            link_url=reverse_safe("transport"),
            metadata={"tvr_id": tvr.pk, "job_id": job.pk},
        )
    return job


def _tvr_summary_lines(tvr: TransportVeterinaryRequest) -> str:
    return (
        f"Județ / localitate: {tvr.judet} / {tvr.oras}\n"
        f"Plecare: {tvr.plecare}\n"
        f"Sosire: {tvr.sosire}\n"
        f"Nr. animale: {tvr.nr_caini}\n"
        f"Data/oră (formular): {tvr.data_raw} {tvr.ora_raw}\n"
    )


def _email_user_no_transporters(request, tvr: TransportVeterinaryRequest, job: TransportDispatchJob) -> None:
    u = tvr.user
    if not u or not u.email:
        return
    subj = email_subject_for_user(u.username, "EU-Adopt — Nu există transportatori disponibili în zonă")
    body = (
        "Bună ziua,\n\n"
        "Ne pare rău, momentan nu există transportatori activi care să acopere traseul selectat.\n\n"
        f"Detalii cerere #{tvr.pk}:\n{_tvr_summary_lines(tvr)}\n"
        "Poți încerca din nou mai târziu sau contacta suportul.\n\n"
        "Echipa EU-Adopt"
    )
    try:
        send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [u.email], fail_silently=False)
    except Exception:
        logger.exception("email no_transporters tvr=%s", tvr.pk)


def _email_user_request_received(request, tvr: TransportVeterinaryRequest, job: TransportDispatchJob) -> None:
    u = tvr.user
    if not u or not u.email:
        return
    cancel_tok = make_token("cancel_user", job.pk, u.pk)
    cancel_path = reverse("transport_dispatch_cancel_user") + f"?t={cancel_tok}"
    cancel_url = _absolute(request, cancel_path)
    subj = email_subject_for_user(u.username, "EU-Adopt — Cererea ta de transport a fost trimisă transportatorilor")
    body = (
        "Bună ziua,\n\n"
        "Cererea ta a fost transmisă transportatorilor eligibili. Primul care acceptă primește detaliile.\n\n"
        f"Cerere #{tvr.pk} · Job dispatch #{job.pk}\n{_tvr_summary_lines(tvr)}\n"
        "Vei primi un email când un transportator acceptă sau dacă nu mai sunt disponibilități.\n\n"
        f"Anulează cererea (înainte să fie preluată): {cancel_url}\n\n"
        "Echipa EU-Adopt"
    )
    try:
        send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [u.email], fail_silently=False)
    except Exception:
        logger.exception("email user received tvr=%s", tvr.pk)


def _email_transporter_new_offer(
    request,
    tvr: TransportVeterinaryRequest,
    job: TransportDispatchJob,
    transporter: User,
) -> None:
    if not transporter.email:
        return
    token = make_token("accept", job.pk, transporter.pk)
    decline_tok = make_token("decline", job.pk, transporter.pk)
    path = reverse("transport_dispatch_accept") + f"?t={token}"
    path_d = reverse("transport_dispatch_decline") + f"?t={decline_tok}"
    url = _absolute(request, path)
    url_d = _absolute(request, path_d)
    subj = email_subject_for_user(transporter.username, f"EU-Adopt — Cerere nouă de transport (#{job.pk})")
    body = (
        "Bună ziua,\n\n"
        "Ai o cerere nouă de transport în zona ta.\n\n"
        f"{_tvr_summary_lines(tvr)}\n"
        f"Acceptă (primul accept preia comanda): {url}\n"
        f"Sau refuză: {url_d}\n\n"
        "Echipa EU-Adopt"
    )
    summary_esc = html_escape(_tvr_summary_lines(tvr).rstrip("\n"))
    url_e = html_escape(url)
    url_de = html_escape(url_d)
    html_body = (
        "<html><body style=\"font-family:Arial,Helvetica,sans-serif;line-height:1.45;color:#111;font-size:15px;\">"
        "<p>Bună ziua,</p>"
        "<p>Ai o <strong>cerere nouă de transport</strong> în zona ta.</p>"
        f"<pre style=\"white-space:pre-wrap;font-family:inherit;font-size:14px;background:#f5f5f5;"
        f"border:1px solid #ddd;border-radius:8px;padding:12px 14px;margin:12px 0;\">{summary_esc}</pre>"
        "<p style=\"margin:16px 0 8px;\">"
        f"<a href=\"{url_e}\" style=\"display:inline-block;padding:12px 18px;border-radius:8px;"
        "background:#2e7d32;color:#fff !important;text-decoration:none;font-weight:700;margin:6px 8px 6px 0;\">"
        "Acceptă</a>"
        f"<a href=\"{url_de}\" style=\"display:inline-block;padding:12px 18px;border-radius:8px;"
        "background:#fff;color:#b71c1c !important;border:2px solid #b71c1c;text-decoration:none;font-weight:700;"
        "margin:6px 0;\">Refuză</a>"
        "</p>"
        "<p style=\"font-size:13px;color:#555;margin-top:12px;\">"
        "Primul care <strong>acceptă</strong> preia comanda. Dacă nu vezi butoane, folosește linkurile din versiunea text de mai sus."
        "</p>"
        "<p>Echipa EU-Adopt</p>"
        "</body></html>"
    )
    try:
        send_mail(
            subj,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [transporter.email],
            fail_silently=False,
            html_message=html_body,
        )
    except Exception:
        logger.exception("email transporter offer job=%s to=%s", job.pk, transporter.pk)


def _email_transporter_superseded(request, job: TransportDispatchJob, transporter: User, winner: User) -> None:
    if not transporter.email:
        return
    name = winner.get_full_name() or winner.username
    subj = email_subject_for_user(
        transporter.username,
        f"EU-Adopt — Cererea #{job.pk} a fost acceptată de alt transportator",
    )
    body = (
        "Bună ziua,\n\n"
        f"Comanda a fost acceptată de {name}.\n"
        "Nu mai este nevoie de acțiune din partea ta pentru această cerere.\n\n"
        "Echipa EU-Adopt"
    )
    try:
        send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [transporter.email], fail_silently=False)
    except Exception:
        logger.exception("email superseded job=%s", job.pk)


def _email_user_assigned(request, tvr: TransportVeterinaryRequest, job: TransportDispatchJob, op: User) -> None:
    u = tvr.user
    if not u or not u.email:
        return
    prof = getattr(op, "transport_operator_profile", None)
    avg = prof.average_rating_public if prof else None
    avg_txt = f"{avg}" if avg is not None else "—"
    prof_user = getattr(op, "profile", None)
    phone = getattr(prof_user, "phone", "") or ""
    rate_url = _absolute(request, rating_page_path(job.pk))
    subj = email_subject_for_user(u.username, "EU-Adopt — Un transportator a acceptat cererea ta")
    body = (
        "Bună ziua,\n\n"
        f"Transportator: {op.get_full_name() or op.username}\n"
        f"Email: {op.email}\n"
        f"Telefon: {phone or '—'}\n"
        f"Notă generală (medie): {avg_txt}\n\n"
        f"Detalii cerere:\n{_tvr_summary_lines(tvr)}\n"
        "Te rugăm să contactezi transportatorul pentru detalii.\n\n"
        f"După încheierea cursei, poți lăsa o evaluare (stele + comentariu): {rate_url}\n\n"
        "Echipa EU-Adopt"
    )
    try:
        send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [u.email], fail_silently=False)
    except Exception:
        logger.exception("email user assigned job=%s", job.pk)


def _email_op_assigned_client(request, tvr: TransportVeterinaryRequest, job: TransportDispatchJob, op: User) -> None:
    u = tvr.user
    if not op.email:
        return
    phone = ""
    try:
        phone = (u.profile.phone or "") if u.profile else ""
    except Exception:
        pass
    rate_url = _absolute(request, rating_page_path(job.pk))
    subj = email_subject_for_user(op.username, "EU-Adopt — Ai acceptat o cerere de transport")
    body = (
        "Bună ziua,\n\n"
        "Date client:\n"
        f"Nume: {u.get_full_name() or u.username}\n"
        f"Email: {u.email}\n"
        f"Telefon: {phone or '—'}\n\n"
        f"Detalii transport:\n{_tvr_summary_lines(tvr)}\n\n"
        f"După cursă, poți evalua experiența (vizibil doar ție, clientului și adminului): {rate_url}\n\n"
        "Echipa EU-Adopt"
    )
    try:
        send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [op.email], fail_silently=False)
    except Exception:
        logger.exception("email op assigned job=%s", job.pk)


def accept_job(request, job_id: int, transporter_user_id: int) -> tuple[bool, str]:
    """Primul accept câștigă. Returnează (ok, mesaj)."""
    with transaction.atomic():
        try:
            job = TransportDispatchJob.objects.select_for_update().get(pk=job_id)
        except TransportDispatchJob.DoesNotExist:
            return False, "Cererea nu există."
        if job.status != TransportDispatchJob.STATUS_OPEN:
            return False, "Cererea nu mai este disponibilă."
        if job.expires_at and job.expires_at < timezone.now():
            job.status = TransportDispatchJob.STATUS_EXPIRED
            job.save(update_fields=["status", "updated_at"])
            _email_user_job_expired(job)
            return False, "Cererea a expirat."
        try:
            rec = TransportDispatchRecipient.objects.select_for_update().get(
                job_id=job.pk,
                transporter_id=transporter_user_id,
                status=TransportDispatchRecipient.ST_PENDING,
            )
        except TransportDispatchRecipient.DoesNotExist:
            return False, "Nu ești în lista pentru această cerere sau ai răspuns deja."
        job.status = TransportDispatchJob.STATUS_ASSIGNED
        job.assigned_transporter_id = transporter_user_id
        job.assigned_at = timezone.now()
        job.save(update_fields=["status", "assigned_transporter", "assigned_at", "updated_at"])
        rec.status = TransportDispatchRecipient.ST_ACCEPTED
        rec.save(update_fields=["status", "updated_at"])
        TransportDispatchRecipient.objects.filter(job_id=job.pk, status=TransportDispatchRecipient.ST_PENDING).update(
            status=TransportDispatchRecipient.ST_SUPERSEDED
        )
    winner = User.objects.get(pk=transporter_user_id)
    tvr = job.tvr
    others = (
        TransportDispatchRecipient.objects.filter(job_id=job.pk)
        .exclude(transporter_id=transporter_user_id)
        .select_related("transporter")
    )
    for r in others:
        if r.transporter_id != transporter_user_id:
            _email_transporter_superseded(request, job, r.transporter, winner)
    _email_user_assigned(request, tvr, job, winner)
    _email_op_assigned_client(request, tvr, job, winner)
    rate_path = rating_page_path(job.pk)
    if tvr.user:
        create_inbox_notification(
            tvr.user,
            KIND_TRANSPORT_ASSIGNED_CLIENT,
            "Un transportator a acceptat cererea ta",
            f"{winner.get_full_name() or winner.username} a preluat transportul pentru cererea #{tvr.pk}.",
            link_url=rate_path,
            metadata={"tvr_id": tvr.pk, "job_id": job.pk},
        )
    create_inbox_notification(
        winner,
        KIND_TRANSPORT_ASSIGNED_OPERATOR,
        "Ai acceptat o cerere de transport",
        f"Cerere #{tvr.pk}: datele clientului au fost trimise pe email.",
        link_url=reverse_safe("transport_operator_panel"),
        metadata={"tvr_id": tvr.pk, "job_id": job.pk},
    )
    return True, "Ai acceptat cererea. Am trimis datele către client și ție."


def decline_job(request, job_id: int, transporter_user_id: int) -> tuple[bool, str]:
    with transaction.atomic():
        try:
            job = TransportDispatchJob.objects.select_for_update().get(pk=job_id)
        except TransportDispatchJob.DoesNotExist:
            return False, "Cererea nu există."
        if job.status != TransportDispatchJob.STATUS_OPEN:
            return False, "Cererea nu mai acceptă răspunsuri."
        try:
            rec = TransportDispatchRecipient.objects.select_for_update().get(
                job_id=job.pk,
                transporter_id=transporter_user_id,
                status=TransportDispatchRecipient.ST_PENDING,
            )
        except TransportDispatchRecipient.DoesNotExist:
            return False, "Nu ești în lista pentru această cerere."
        rec.status = TransportDispatchRecipient.ST_DECLINED
        rec.save(update_fields=["status", "updated_at"])
        pending = TransportDispatchRecipient.objects.filter(
            job_id=job.pk, status=TransportDispatchRecipient.ST_PENDING
        ).count()
    if pending == 0:
        job.status = TransportDispatchJob.STATUS_EXHAUSTED
        job.save(update_fields=["status", "updated_at"])
        if job.tvr.user and job.tvr.user.email:
            try:
                send_mail(
                    email_subject_for_user(
                        job.tvr.user.username,
                        "EU-Adopt — Nu mai există transportatori disponibili",
                    ),
                    "Toți transportatorii contactați au refuzat sau nu mai sunt disponibili.\n",
                    settings.DEFAULT_FROM_EMAIL,
                    [job.tvr.user.email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("email exhausted job=%s", job.pk)
        cu = job.tvr.user
        if cu:
            create_inbox_notification(
                cu,
                KIND_TRANSPORT_EXHAUSTED,
                "Transport: nu mai sunt transportatori disponibili",
                f"Toți transportatorii contactați au refuzat cererea #{job.tvr_id} sau nu mai sunt disponibili.",
                link_url=reverse_safe("transport"),
                metadata={"tvr_id": job.tvr_id, "job_id": job.pk},
            )
    return True, "Ai refuzat cererea."


def cancel_job_by_user(request, job_id: int, user_id: int) -> tuple[bool, str]:
    """Anulare de la client: dacă încă e deschisă → anulare totală; dacă era asignată → re-ofertă."""
    with transaction.atomic():
        job = TransportDispatchJob.objects.select_for_update().filter(pk=job_id).first()
        if not job:
            return False, "Cererea nu există."
        tvr = job.tvr
        if not tvr.user_id or tvr.user_id != user_id:
            return False, "Nu poți anula această cerere."
        if job.status in (TransportDispatchJob.STATUS_CANCELLED, TransportDispatchJob.STATUS_COMPLETED, TransportDispatchJob.STATUS_EXPIRED):
            return False, "Cererea este deja închisă."
        if job.status == TransportDispatchJob.STATUS_OPEN:
            job.status = TransportDispatchJob.STATUS_CANCELLED
            job.save(update_fields=["status", "updated_at"])
            if tvr.user:
                create_inbox_notification(
                    tvr.user,
                    KIND_TRANSPORT_CANCELLED_USER,
                    "Cererea de transport a fost anulată",
                    f"Cererea #{tvr.pk} a fost anulată înainte de preluare.",
                    link_url=reverse_safe("transport"),
                    metadata={"tvr_id": tvr.pk, "job_id": job.pk},
                )
            return True, "Cererea a fost anulată."
        was_assigned = job.status == TransportDispatchJob.STATUS_ASSIGNED and job.assigned_transporter_id
        job.status = TransportDispatchJob.STATUS_OPEN
        job.assigned_transporter = None
        job.assigned_at = None
        job.reopen_count += 1
        job.save(update_fields=["status", "assigned_transporter", "assigned_at", "reopen_count", "updated_at"])
        TransportDispatchRecipient.objects.filter(job_id=job.pk).exclude(
            status=TransportDispatchRecipient.ST_DECLINED
        ).update(status=TransportDispatchRecipient.ST_PENDING)
    if was_assigned:
        users = [r.transporter for r in TransportDispatchRecipient.objects.filter(job_id=job.pk).select_related("transporter")]
        for u in users:
            if u:
                _email_transporter_new_offer(request, tvr, job, u)
        _notify_transporters_dispatch_invite(request, tvr, job, users)
    if tvr.user:
        create_inbox_notification(
            tvr.user,
            KIND_TRANSPORT_REOPENED,
            "Cererea de transport a fost retrimisă",
            f"După anulare, cererea #{tvr.pk} a fost redeschisă și trimisă din nou transportatorilor.",
            link_url=reverse_safe("transport"),
            metadata={"tvr_id": tvr.pk, "job_id": job.pk},
        )
    return True, "Cererea a fost reprogramată și retrimisă transportatorilor."


def cancel_assignment_by_transporter(request, job_id: int, transporter_user_id: int) -> tuple[bool, str]:
    """După accept, transportatorul renunță — re-ofertă."""
    with transaction.atomic():
        job = TransportDispatchJob.objects.select_for_update().filter(pk=job_id).first()
        if not job:
            return False, "Cererea nu există."
        if job.assigned_transporter_id != transporter_user_id:
            return False, "Nu ești transportatorul asignat."
        job.status = TransportDispatchJob.STATUS_OPEN
        job.assigned_transporter = None
        job.assigned_at = None
        job.reopen_count += 1
        job.save(update_fields=["status", "assigned_transporter", "assigned_at", "reopen_count", "updated_at"])
        TransportDispatchRecipient.objects.filter(job_id=job.pk).exclude(
            status=TransportDispatchRecipient.ST_DECLINED
        ).update(status=TransportDispatchRecipient.ST_PENDING)
    users = [r.transporter for r in TransportDispatchRecipient.objects.filter(job_id=job.pk).select_related("transporter")]
    for u in users:
        _email_transporter_new_offer(request, job.tvr, job, u)
    _notify_transporters_dispatch_invite(request, job.tvr, job, users)
    if job.tvr.user and job.tvr.user.email:
        try:
            send_mail(
                email_subject_for_user(
                    job.tvr.user.username,
                    "EU-Adopt — Transportul a fost reprogramat",
                ),
                "Transportatorul a anulat preluarea. Cererea a fost retrimisă către transportatori.\n",
                settings.DEFAULT_FROM_EMAIL,
                [job.tvr.user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("notify user reopen job=%s", job.pk)
    if job.tvr.user:
        create_inbox_notification(
            job.tvr.user,
            KIND_TRANSPORT_REOPENED,
            "Transport reprogramat",
            "Transportatorul a renunțat la preluare; cererea a fost retrimisă către alți transportatori.",
            link_url=reverse_safe("transport"),
            metadata={"tvr_id": job.tvr_id, "job_id": job.pk},
        )
    return True, "Ai renunțat; cererea a fost retrimisă."


def maybe_expire_job(job: TransportDispatchJob) -> bool:
    if job.status != TransportDispatchJob.STATUS_OPEN or not job.expires_at:
        return False
    if job.expires_at >= timezone.now():
        return False
    job.status = TransportDispatchJob.STATUS_EXPIRED
    job.save(update_fields=["status", "updated_at"])
    _email_user_job_expired(job)
    return True


def _email_user_job_expired(job: TransportDispatchJob) -> None:
    tvr = job.tvr
    u = tvr.user
    if u:
        create_inbox_notification(
            u,
            KIND_TRANSPORT_EXPIRED,
            "Cererea de transport a expirat",
            f"Cererea #{tvr.pk} (job #{job.pk}) nu a fost acceptată la timp.",
            link_url=reverse_safe("transport"),
            metadata={"tvr_id": tvr.pk, "job_id": job.pk},
        )
    if not u or not u.email:
        return
    extra = ""
    if (tvr.urgency_window or "") == TransportVeterinaryRequest.URGENCY_TODAY:
        extra = (
            "\nPentru opțiunea „transport azi”, poți trimite o nouă cerere cu data/ora actualizată din pagina Transport.\n"
        )
    subj = email_subject_for_user(
        u.username,
        "EU-Adopt — Cererea de transport a expirat (nimeni nu a acceptat la timp)",
    )
    body = (
        "Bună ziua,\n\n"
        f"Cererea #{tvr.pk} (job #{job.pk}) nu mai este activă — perioada alocată a expirat fără accept.\n"
        f"{extra}\n"
        "Poți depune o nouă cerere din pagina Transport.\n\n"
        "Echipa EU-Adopt"
    )
    try:
        send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [u.email], fail_silently=False)
    except Exception:
        logger.exception("email job_expired job=%s", job.pk)


def rating_page_path(job_id: int) -> str:
    return reverse("transport_dispatch_rate", kwargs={"job_id": job_id})


def submit_rating(
    job: TransportDispatchJob,
    from_user: User,
    to_user: User,
    direction: str,
    stars: int,
    comment: str,
) -> TransportTripRating:
    if stars < 1 or stars > 5:
        stars = 5
    existing = TransportTripRating.objects.filter(
        job=job, from_user=from_user, direction=direction
    ).first()
    if existing:
        return existing
    visible = direction == TransportTripRating.DIR_USER_TO_OP
    r = TransportTripRating.objects.create(
        job=job,
        from_user=from_user,
        to_user=to_user,
        direction=direction,
        stars=stars,
        comment=(comment or "")[:2000],
        visible_to_public_profile=visible,
    )
    if direction == TransportTripRating.DIR_USER_TO_OP:
        try:
            top = to_user.transport_operator_profile
        except Exception:
            top = None
        if top:
            top.rating_sum += stars
            top.rating_count += 1
            top.save(update_fields=["rating_sum", "rating_count", "updated_at"])
    _maybe_mark_job_completed(job)
    return r


def _maybe_mark_job_completed(job: TransportDispatchJob) -> None:
    if job.status != TransportDispatchJob.STATUS_ASSIGNED:
        return
    tvr = job.tvr
    op = job.assigned_transporter
    if not tvr.user_id or not op:
        return
    has_client = TransportTripRating.objects.filter(
        job=job,
        direction=TransportTripRating.DIR_USER_TO_OP,
        from_user_id=tvr.user_id,
    ).exists()
    has_op = TransportTripRating.objects.filter(
        job=job,
        direction=TransportTripRating.DIR_OP_TO_USER,
        from_user_id=op.pk,
    ).exists()
    if has_client and has_op:
        job.status = TransportDispatchJob.STATUS_COMPLETED
        job.save(update_fields=["status", "updated_at"])
        rate_path = rating_page_path(job.pk)
        create_inbox_notification(
            tvr.user,
            KIND_TRANSPORT_COMPLETED,
            "Transport marcat ca finalizat",
            f"Ambele părți au lăsat evaluare pentru cererea #{tvr.pk}.",
            link_url=rate_path,
            metadata={"tvr_id": tvr.pk, "job_id": job.pk},
        )
        create_inbox_notification(
            op,
            KIND_TRANSPORT_COMPLETED,
            "Transport marcat ca finalizat",
            f"Ambele părți au lăsat evaluare pentru cererea #{tvr.pk}.",
            link_url=rate_path,
            metadata={"tvr_id": tvr.pk, "job_id": job.pk},
        )
