"""
Faza C — procesare răspunsuri / bounce / opt-out pentru invitații Add USER.

Identificare lead:
- Reply-To / To: invite+{id}@domeniu
- Antet X-EUAdopt-Lead-Id
- Message-ID (In-Reply-To / References) față de log trimitere
- From = email prospect (dacă a răspuns direct la contact@)
"""
from __future__ import annotations

import email
import imaplib
import logging
import re
from datetime import timedelta
from email.header import decode_header
from email.utils import parseaddr

from django.conf import settings
from django.utils import timezone

from home.models import StaffOnboardingLead, StaffOnboardingInviteLog, StaffOnboardingInviteInbound
from home.staff_onboarding_csv import is_placeholder_lead_email

logger = logging.getLogger(__name__)

_LEAD_PLUS_RE = re.compile(r"invite\+(\d+)@", re.I)
_LEAD_HEADER_RE = re.compile(r"^X-EUAdopt-Lead-Id:\s*(\d+)\s*$", re.I | re.M)
_BOUNCE_FROM = re.compile(r"mailer-daemon|postmaster|mail delivery|noreply.*bounce", re.I)
_BOUNCE_SUBJ = re.compile(
    r"undelivered|delivery failed|failure notice|returned mail|delivery status|"
    r"undeliverable|mail delivery failed|could not be delivered|permanent error",
    re.I,
)
_OPT_OUT_RE = re.compile(r"nu\s*contacta|nu\s*ma\s*contact|stop\s*contact|unsubscribe", re.I)
# NDR Zoho/Yahoo: Final-Recipient: rfc822; user@domain
_BOUNCE_RECIPIENT_RE = re.compile(
    r"(?:Final-Recipient|Original-Recipient|X-Failed-Recipients)\s*:\s*"
    r"(?:rfc822\s*;\s*)?<?([^\s<>;]+@[^\s<>;]+)>?",
    re.I,
)
_LEAD_ID_IN_BODY_RE = re.compile(r"X-EUAdopt-Lead-Id:\s*(\d+)", re.I)
# NDR / auto-reply care propune o adresă alternativă
_SUGGESTED_EMAIL_RES = (
    re.compile(
        r"(?:try\s+(?:sending\s+)?(?:it\s+)?to|please\s+(?:try\s+)?(?:sending\s+)?to|"
        r"please\s+use|instead\s+(?:use|try|to)|send\s+(?:it\s+)?(?:instead\s+)?to|"
        r"new\s+(?:e-?mail|address)\s*(?:is|:)|correct\s+(?:e-?mail|address)\s*(?:is|:)|"
        r"forward(?:ed)?\s+to|redirect(?:ed)?\s+to|recipient(?:\s+has)?\s+changed(?:\s+to)?|"
        r"mailbox\s+has\s+moved(?:\s+to)?|use\s+this\s+(?:e-?mail|address)\s*(?:instead)?|"
        r"adresa\s+(?:corect[aă]|nou[aă])\s*(?:este|:)?|noua\s+adres[aă]\s*(?:este|:)?|"
        r"folosi[tț]i\s+(?:adresa|e-?mail(?:ul)?))\s*[:=]?\s*<?([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})>?",
        re.I,
    ),
    re.compile(
        r"(?:X-Actual-Recipient|Suggested-Recipient|X-Failed-Recipients-Alternate)\s*:\s*"
        r"(?:rfc822\s*;\s*)?<?([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})>?",
        re.I,
    ),
)
_GENERIC_EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_OUR_DOMAINS = frozenset({"eu-adopt.ro", "euadopt.ro"})


def staff_invite_reply_to_address(lead_id: int) -> str:
    override = (getattr(settings, "STAFF_INVITE_REPLY_TO", None) or "").strip()
    if override and "@" in override:
        local, _, domain = override.partition("@")
        return f"{local}+{lead_id}@{domain}"
    base = (getattr(settings, "EMAIL_HOST_USER", None) or "").strip()
    if not base or "@" not in base:
        base = "contact@eu-adopt.ro"
    local, _, domain = base.partition("@")
    prefix = (getattr(settings, "STAFF_INVITE_REPLY_LOCAL", None) or "invite").strip() or "invite"
    return f"{prefix}+{lead_id}@{domain}"


def staff_invite_imap_configured() -> bool:
    return bool(
        (getattr(settings, "STAFF_INVITE_IMAP_HOST", None) or "").strip()
        and (getattr(settings, "STAFF_INVITE_IMAP_USER", None) or "").strip()
        and (getattr(settings, "STAFF_INVITE_IMAP_PASSWORD", None) or "").strip()
    )


def _decode_mime_header(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    parts = decode_header(str(raw))
    out = []
    for frag, enc in parts:
        if isinstance(frag, bytes):
            out.append(frag.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(frag))
    return "".join(out).strip()


def _extract_body(msg: email.message.Message) -> str:
    chunks: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    chunks.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            chunks.append(payload.decode(msg.get_content_charset() or "utf-8", errors="replace"))
    text = "\n".join(chunks).strip()
    return text[:8000]


def _headers_dict(msg: email.message.Message) -> dict[str, str]:
    h = {}
    for key in ("From", "To", "Cc", "Subject", "In-Reply-To", "References", "Reply-To", "X-EUAdopt-Lead-Id"):
        if msg.get(key):
            h[key] = _decode_mime_header(msg.get(key))
    return h


def _parse_lead_id_from_addresses(*addrs: str) -> int | None:
    for raw in addrs:
        for m in _LEAD_PLUS_RE.finditer(raw or ""):
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def _parse_lead_id_from_headers(headers: dict[str, str]) -> int | None:
    xid = (headers.get("X-EUAdopt-Lead-Id") or "").strip()
    if xid.isdigit():
        return int(xid)
    for key in ("In-Reply-To", "References"):
        val = headers.get(key) or ""
        log = (
            StaffOnboardingInviteLog.objects.filter(message_id__in=[v.strip() for v in val.split() if v.strip()])
            .order_by("-sent_at")
            .first()
        )
        if log:
            return log.lead_id
    return None


def _match_lead_by_email(email_addr: str) -> StaffOnboardingLead | None:
    em = (email_addr or "").strip().lower()
    if not em or is_placeholder_lead_email(em):
        return None
    return (
        StaffOnboardingLead.objects.filter(email__iexact=em, imported_user__isnull=True)
        .order_by("-updated_at")
        .first()
    )


def _match_lead_by_from(from_email: str) -> StaffOnboardingLead | None:
    return _match_lead_by_email(parseaddr(from_email)[1] or from_email)


def extract_bounce_recipient_emails(body: str, subject: str = "") -> list[str]:
    """Extrage adresele eșuate din NDR (Final-Recipient etc.)."""
    text = f"{subject or ''}\n{body or ''}"
    out: list[str] = []
    seen: set[str] = set()
    for m in _BOUNCE_RECIPIENT_RE.finditer(text):
        em = (m.group(1) or "").strip().lower().rstrip(".")
        if not em or "@" not in em or em in seen:
            continue
        if is_placeholder_lead_email(em):
            continue
        seen.add(em)
        out.append(em)
    return out


def _normalize_candidate_email(raw: str) -> str:
    em = (raw or "").strip().lower().rstrip(".,;:>)")
    em = em.lstrip("<").rstrip(">")
    return em


def _is_our_system_email(em: str) -> bool:
    em = _normalize_candidate_email(em)
    if not em or "@" not in em:
        return True
    local, _, domain = em.partition("@")
    if domain in _OUR_DOMAINS:
        return True
    if local.startswith("invite+") or local in {"mailer-daemon", "postmaster", "noreply", "no-reply"}:
        return True
    return False


def extract_suggested_redirect_email(
    body: str,
    subject: str = "",
    *,
    failed_emails: list[str] | None = None,
    lead_email: str = "",
) -> str | None:
    """
    Din NDR: adresa nouă sugerată (dacă există), diferită de adresa eșuată / lead.
    Nu tratează „Please try again later” ca redirect.
    """
    from home.staff_invite_email_expand import is_plausible_invite_email

    text = f"{subject or ''}\n{body or ''}"
    failed = {_normalize_candidate_email(e) for e in (failed_emails or []) if e}
    lead_em = _normalize_candidate_email(lead_email)
    if lead_em:
        failed.add(lead_em)

    candidates: list[str] = []
    for rx in _SUGGESTED_EMAIL_RES:
        for m in rx.finditer(text):
            em = _normalize_candidate_email(m.group(1))
            if em:
                candidates.append(em)

    for em in candidates:
        if em in failed or _is_our_system_email(em):
            continue
        if not is_plausible_invite_email(em):
            continue
        return em
    return None


def apply_bounce_email_redirect(
    lead: StaffOnboardingLead,
    new_email: str,
    *,
    old_email: str = "",
    body: str = "",
    subject: str = "",
) -> dict:
    """
    Actualizează emailul prospectului + încearcă retransmitere invitație.
    Returnează dict: redirected, resend_outcome, reason, new_email.
    """
    from django.test import RequestFactory

    from home.staff_invite_daily_wave import _cron_staff_user
    from home.staff_invite_email_expand import is_plausible_invite_email
    from home.staff_onboarding_invite import staff_invite_process_one

    new_em = _normalize_candidate_email(new_email)
    old_em = _normalize_candidate_email(old_email) or _normalize_candidate_email(lead.email)
    out: dict = {
        "redirected": False,
        "new_email": new_em,
        "old_email": old_em,
        "resend_outcome": "",
        "reason": "",
    }
    if lead.imported_user_id:
        out["reason"] = "already_imported"
        return out
    if not is_plausible_invite_email(new_em):
        out["reason"] = "new_email_invalid"
        return out
    if new_em == old_em:
        out["reason"] = "same_email"
        return out

    notes = lead.invite_staff_notes or ""
    marker = f"[BOUNCE-REDIRECT] {old_em} → {new_em}"
    if marker in notes or f"→ {new_em}" in notes and "[BOUNCE-REDIRECT]" in notes:
        out["reason"] = "already_redirected"
        return out
    # Max 1 redirect automat per lead (evită bucle NDR).
    if "[BOUNCE-REDIRECT]" in notes:
        out["reason"] = "redirect_limit"
        return out

    other = (
        StaffOnboardingLead.objects.filter(email__iexact=new_em)
        .exclude(pk=lead.pk)
        .order_by("pk")
        .first()
    )
    if other:
        _append_inbound_note(
            lead,
            f"[BOUNCE-REDIRECT SKIP] {old_em} → {new_em} (deja pe lead #{other.pk})",
        )
        out["reason"] = "email_taken"
        return out

    lead.email = new_em[:254]
    # Scoate din bounced ca să poată fi retrimis; cooldown anulat o dată.
    lead.invite_mail_status = StaffOnboardingLead.INVITE_SENT
    lead.invite_email_last_sent_at = None
    lead.save(
        update_fields=["email", "invite_mail_status", "invite_email_last_sent_at", "updated_at"]
    )
    _append_inbound_note(
        lead,
        f"{marker} @ {timezone.now():%Y-%m-%d %H:%M} subj={(subject or '')[:60]}",
    )
    out["redirected"] = True

    staff = _cron_staff_user()
    request = RequestFactory().get("/", HTTP_HOST="www.eu-adopt.ro", secure=True)
    try:
        outcome = staff_invite_process_one(
            request,
            staff,
            lead,
            dispatch_kind=StaffOnboardingInviteLog.DISPATCH_BOUNCE_RD,
        )
    except Exception:
        logger.exception("bounce_redirect_resend lead_id=%s new=%s", lead.pk, new_em)
        outcome = "error"
    out["resend_outcome"] = outcome or ""
    if outcome not in ("sent", "simulated"):
        _append_inbound_note(
            lead,
            f"[BOUNCE-REDIRECT RESEND] outcome={outcome or 'empty'} — email actualizat, retrimitere la val/manual",
        )
    return out


def classify_inbound(from_email: str, subject: str, body: str, headers: dict[str, str]) -> str:
    """reply | bounce | opt_out | unknown"""
    subj = subject or ""
    body_l = (body or "").lower()
    from_l = (from_email or "").lower()
    if (
        _BOUNCE_FROM.search(from_l)
        or _BOUNCE_SUBJ.search(subj)
        or _BOUNCE_RECIPIENT_RE.search(body or "")
        or "mailbox not found" in body_l
        or "could not be delivered" in body_l
    ):
        return StaffOnboardingInviteInbound.KIND_BOUNCE
    if _OPT_OUT_RE.search(subj) or _OPT_OUT_RE.search(body_l):
        return StaffOnboardingInviteInbound.KIND_OPT_OUT
    if from_l and not _BOUNCE_FROM.search(from_l):
        return StaffOnboardingInviteInbound.KIND_REPLY
    return StaffOnboardingInviteInbound.KIND_UNKNOWN


def resolve_lead_for_inbound(
    from_email: str,
    to_addrs: list[str],
    headers: dict[str, str],
    *,
    body: str = "",
    subject: str = "",
    kind: str = "",
) -> StaffOnboardingLead | None:
    addrs = list(to_addrs) + [headers.get("To") or "", headers.get("Cc") or "", headers.get("Reply-To") or ""]
    # invite+{id}@ din antete / corp (NDR poate include mesajul original)
    lid = _parse_lead_id_from_addresses(*(addrs + [body or "", subject or ""]))
    if lid:
        lead = StaffOnboardingLead.objects.filter(pk=lid).first()
        if lead:
            return lead
    lid = _parse_lead_id_from_headers(headers)
    if lid:
        lead = StaffOnboardingLead.objects.filter(pk=lid).first()
        if lead:
            return lead
    m = _LEAD_ID_IN_BODY_RE.search(body or "")
    if m:
        lead = StaffOnboardingLead.objects.filter(pk=int(m.group(1))).first()
        if lead:
            return lead
    # Bounce Zoho: From=mailer-daemon, adresa reală e în Final-Recipient
    if kind == StaffOnboardingInviteInbound.KIND_BOUNCE or _BOUNCE_FROM.search((from_email or "").lower()):
        for em in extract_bounce_recipient_emails(body, subject):
            lead = _match_lead_by_email(em)
            if lead:
                return lead
            # fallback: ultimul log de trimitere către acel email
            log = (
                StaffOnboardingInviteLog.objects.filter(to_email__iexact=em)
                .order_by("-sent_at")
                .select_related("lead")
                .first()
            )
            if log and log.lead_id:
                return log.lead
    return _match_lead_by_from(from_email)


def _append_inbound_note(lead: StaffOnboardingLead, line: str) -> None:
    prev = (lead.invite_staff_notes or "").strip()
    lead.invite_staff_notes = f"{prev}\n{line}".strip() if prev else line
    lead.save(update_fields=["invite_staff_notes", "updated_at"])


def apply_inbound_to_lead(
    lead: StaffOnboardingLead,
    kind: str,
    *,
    from_email: str = "",
    subject: str = "",
    now=None,
) -> bool:
    """Actualizează lead; returnează True dacă s-a schimbat starea."""
    now = now or timezone.now()
    if lead.imported_user_id:
        return False
    if kind == StaffOnboardingInviteInbound.KIND_BOUNCE:
        if lead.invite_mail_status == StaffOnboardingLead.INVITE_BOUNCED:
            return False
        lead.invite_mail_status = StaffOnboardingLead.INVITE_BOUNCED
        lead.save(update_fields=["invite_mail_status", "updated_at"])
        return True
    if kind == StaffOnboardingInviteInbound.KIND_OPT_OUT:
        if lead.invite_mail_status == StaffOnboardingLead.INVITE_DO_NOT_CONTACT:
            return False
        lead.invite_mail_status = StaffOnboardingLead.INVITE_DO_NOT_CONTACT
        lead.save(update_fields=["invite_mail_status", "updated_at"])
        return True
    if kind == StaffOnboardingInviteInbound.KIND_REPLY:
        if lead.invite_mail_status in (
            StaffOnboardingLead.INVITE_REPLIED,
            StaffOnboardingLead.INVITE_DO_NOT_CONTACT,
            StaffOnboardingLead.INVITE_SIGNED_UP,
        ):
            return False
        lead.invite_mail_status = StaffOnboardingLead.INVITE_REPLIED
        lead.invite_replied_at = now
        lead.save(update_fields=["invite_mail_status", "invite_replied_at", "updated_at"])
        return True
    return False


def process_inbound_email(
    *,
    from_email: str,
    to_addrs: list[str] | None = None,
    subject: str = "",
    body: str = "",
    headers: dict[str, str] | None = None,
    source: str = StaffOnboardingInviteInbound.SOURCE_WEBHOOK,
    external_id: str = "",
) -> dict:
    """
    Procesează un mesaj primit. Returnează dict cu kind, lead_id, applied, skipped_reason.
    """
    headers = headers or {}
    to_addrs = to_addrs or []
    if external_id:
        if StaffOnboardingInviteInbound.objects.filter(source=source, external_id=external_id).exists():
            return {"skipped": True, "reason": "duplicate", "external_id": external_id}

    from_addr = parseaddr(from_email)[1] or (from_email or "").strip()
    kind = classify_inbound(from_addr, subject, body, headers)
    lead = resolve_lead_for_inbound(
        from_addr, to_addrs, headers, body=body or "", subject=subject or "", kind=kind
    )
    snippet = (subject or "")[:200]
    if body:
        snippet = f"{snippet} | {(body or '')[:300]}"

    inbound = StaffOnboardingInviteInbound(
        lead=lead,
        from_email=from_addr[:254] if from_addr else "",
        subject=(subject or "")[:255],
        kind=kind,
        source=source,
        external_id=(external_id or "")[:120],
        snippet=snippet[:500],
    )
    applied = False
    redirect_info: dict = {}
    if lead:
        if kind == StaffOnboardingInviteInbound.KIND_BOUNCE:
            failed = extract_bounce_recipient_emails(body or "", subject or "")
            suggested = extract_suggested_redirect_email(
                body or "",
                subject or "",
                failed_emails=failed,
                lead_email=lead.email or "",
            )
            if suggested:
                redirect_info = apply_bounce_email_redirect(
                    lead,
                    suggested,
                    old_email=lead.email or "",
                    body=body or "",
                    subject=subject or "",
                )
                if redirect_info.get("redirected"):
                    applied = True
                elif redirect_info.get("reason") in ("already_redirected", "redirect_limit", "same_email"):
                    applied = False
                else:
                    # fără redirect util → marchează bounced ca înainte
                    applied = apply_inbound_to_lead(
                        lead, kind, from_email=from_addr, subject=subject
                    )
                    if applied:
                        _append_inbound_note(
                            lead,
                            f"[INBOUND {timezone.now():%Y-%m-%d %H:%M}] {kind} de la {from_addr}: "
                            f"{(subject or '')[:80]} (sugerat {suggested}, skip={redirect_info.get('reason')})",
                        )
            else:
                applied = apply_inbound_to_lead(lead, kind, from_email=from_addr, subject=subject)
                if applied:
                    _append_inbound_note(
                        lead,
                        f"[INBOUND {timezone.now():%Y-%m-%d %H:%M}] {kind} de la {from_addr}: {(subject or '')[:80]}",
                    )
        else:
            applied = apply_inbound_to_lead(lead, kind, from_email=from_addr, subject=subject)
            if applied:
                _append_inbound_note(
                    lead,
                    f"[INBOUND {timezone.now():%Y-%m-%d %H:%M}] {kind} de la {from_addr}: {(subject or '')[:80]}",
                )
    inbound.save()
    result = {
        "kind": kind,
        "lead_id": lead.pk if lead else None,
        "applied": applied,
        "inbound_id": inbound.pk,
    }
    if redirect_info:
        result["redirected"] = bool(redirect_info.get("redirected"))
        result["redirect_email"] = redirect_info.get("new_email") or ""
        result["redirect_reason"] = redirect_info.get("reason") or ""
        result["resend_outcome"] = redirect_info.get("resend_outcome") or ""
    return result


def poll_imap_inbox(
    *,
    max_messages: int = 40,
    mark_seen: bool = True,
    mode: str = "unseen",
    since_days: int = 45,
) -> dict[str, int]:
    """Citește inbox IMAP Zoho (sau alt server) și procesează mesaje.

    mode:
      unseen — doar UNSEEN (cron normal)
      bounce_backlog — NDR-uri recente (inclusiv deja citite), doar bounce
    """
    if not staff_invite_imap_configured():
        return {"error": 1, "message": "IMAP neconfigurat"}

    host = settings.STAFF_INVITE_IMAP_HOST.strip()
    port = int(getattr(settings, "STAFF_INVITE_IMAP_PORT", 993))
    user = settings.STAFF_INVITE_IMAP_USER.strip()
    password = settings.STAFF_INVITE_IMAP_PASSWORD.strip()
    folder = (getattr(settings, "STAFF_INVITE_IMAP_FOLDER", None) or "INBOX").strip()
    mode = (mode or "unseen").strip().lower()
    since_days = max(1, min(int(since_days or 45), 120))

    stats = {
        "processed": 0,
        "replies": 0,
        "bounces": 0,
        "opt_out": 0,
        "unknown": 0,
        "skipped_dup": 0,
        "skipped_non_bounce": 0,
        "no_lead": 0,
        "errors": 0,
        "redirects": 0,
        "mode": mode,
    }

    try:
        if port == 993:
            conn = imaplib.IMAP4_SSL(host, port)
        else:
            conn = imaplib.IMAP4(host, port)
        conn.login(user, password)
        conn.select(folder)

        if mode == "bounce_backlog":
            since = (timezone.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
            # Filtrăm bounce în Python (criteriile OR IMAP diferă pe Zoho).
            typ, data = conn.search(None, f"(SINCE {since})")
        else:
            typ, data = conn.search(None, "UNSEEN")

        if typ != "OK":
            conn.logout()
            return {**stats, "errors": 1}
        ids = (data[0] or b"").split()
        if mode == "bounce_backlog":
            ids = list(reversed(ids))  # cele mai recente întâi
        else:
            ids = ids[-max_messages:]

        bounce_seen = 0
        for num in ids:
            if mode == "bounce_backlog" and bounce_seen >= max_messages:
                break
            try:
                typ, msg_data = conn.fetch(num, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                from_h = _decode_mime_header(msg.get("From"))
                subj = _decode_mime_header(msg.get("Subject"))
                to_h = _decode_mime_header(msg.get("To"))
                body = _extract_body(msg)
                headers = _headers_dict(msg)
                mid = (msg.get("Message-ID") or "").strip()
                if mid:
                    ext_id = f"msgid-{mid}"[:120]
                else:
                    ext_id = f"imap-{folder}-{num.decode() if isinstance(num, bytes) else num}"

                kind_preview = classify_inbound(
                    parseaddr(from_h)[1] or from_h, subj, body, headers
                )
                if mode == "bounce_backlog" and kind_preview != StaffOnboardingInviteInbound.KIND_BOUNCE:
                    stats["skipped_non_bounce"] += 1
                    continue
                if mode == "bounce_backlog":
                    bounce_seen += 1

                result = process_inbound_email(
                    from_email=from_h,
                    to_addrs=[to_h],
                    subject=subj,
                    body=body,
                    headers=headers,
                    source=StaffOnboardingInviteInbound.SOURCE_IMAP,
                    external_id=ext_id,
                )
                if result.get("skipped"):
                    stats["skipped_dup"] += 1
                    if mark_seen:
                        conn.store(num, "+FLAGS", "\\Seen")
                    continue
                stats["processed"] += 1
                k = result.get("kind") or "unknown"
                if k == StaffOnboardingInviteInbound.KIND_REPLY:
                    stats["replies"] += 1
                elif k == StaffOnboardingInviteInbound.KIND_BOUNCE:
                    stats["bounces"] += 1
                    if result.get("redirected"):
                        stats["redirects"] += 1
                elif k == StaffOnboardingInviteInbound.KIND_OPT_OUT:
                    stats["opt_out"] += 1
                else:
                    stats["unknown"] += 1
                if not result.get("lead_id"):
                    stats["no_lead"] += 1
                if mark_seen:
                    conn.store(num, "+FLAGS", "\\Seen")
            except Exception:
                logger.exception("staff_invite_imap message %s", num)
                stats["errors"] += 1
        conn.logout()
    except Exception as exc:
        logger.exception("staff_invite_imap poll failed")
        return {**stats, "errors": 1, "message": str(exc)[:500]}
    return stats


def inbound_stats_summary() -> dict:
    """Rezumat pentru panoul Add USER."""
    since = timezone.now() - timedelta(days=7)
    qs = StaffOnboardingInviteInbound.objects.filter(received_at__gte=since)
    return {
        "replies_7d": qs.filter(kind=StaffOnboardingInviteInbound.KIND_REPLY).count(),
        "bounces_7d": qs.filter(kind=StaffOnboardingInviteInbound.KIND_BOUNCE).count(),
        "opt_out_7d": qs.filter(kind=StaffOnboardingInviteInbound.KIND_OPT_OUT).count(),
        "imap_configured": staff_invite_imap_configured(),
        "reply_address_example": staff_invite_reply_to_address(1).replace("+1@", "+{id}@"),
    }
