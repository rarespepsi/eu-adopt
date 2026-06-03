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
    r"undeliverable|mail delivery failed",
    re.I,
)
_OPT_OUT_RE = re.compile(r"nu\s*contacta|nu\s*ma\s*contact|stop\s*contact|unsubscribe", re.I)


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


def _match_lead_by_from(from_email: str) -> StaffOnboardingLead | None:
    em = (from_email or "").strip().lower()
    if not em or is_placeholder_lead_email(em):
        return None
    return (
        StaffOnboardingLead.objects.filter(email__iexact=em, imported_user__isnull=True)
        .order_by("-updated_at")
        .first()
    )


def classify_inbound(from_email: str, subject: str, body: str, headers: dict[str, str]) -> str:
    """reply | bounce | opt_out | unknown"""
    subj = subject or ""
    body_l = (body or "").lower()
    from_l = (from_email or "").lower()
    if _BOUNCE_FROM.search(from_l) or _BOUNCE_SUBJ.search(subj):
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
) -> StaffOnboardingLead | None:
    addrs = list(to_addrs) + [headers.get("To") or "", headers.get("Cc") or "", headers.get("Reply-To") or ""]
    lid = _parse_lead_id_from_addresses(*addrs)
    if lid:
        return StaffOnboardingLead.objects.filter(pk=lid).first()
    lid = _parse_lead_id_from_headers(headers)
    if lid:
        return StaffOnboardingLead.objects.filter(pk=lid).first()
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
    lead = resolve_lead_for_inbound(from_addr, to_addrs, headers)
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
    if lead:
        applied = apply_inbound_to_lead(lead, kind, from_email=from_addr, subject=subject)
        if applied:
            _append_inbound_note(
                lead,
                f"[INBOUND {timezone.now():%Y-%m-%d %H:%M}] {kind} de la {from_addr}: {(subject or '')[:80]}",
            )
    inbound.save()
    return {
        "kind": kind,
        "lead_id": lead.pk if lead else None,
        "applied": applied,
        "inbound_id": inbound.pk,
    }


def poll_imap_inbox(*, max_messages: int = 40, mark_seen: bool = True) -> dict[str, int]:
    """Citește inbox IMAP Zoho (sau alt server) și procesează mesaje noi."""
    if not staff_invite_imap_configured():
        return {"error": 1, "message": "IMAP neconfigurat"}

    host = settings.STAFF_INVITE_IMAP_HOST.strip()
    port = int(getattr(settings, "STAFF_INVITE_IMAP_PORT", 993))
    user = settings.STAFF_INVITE_IMAP_USER.strip()
    password = settings.STAFF_INVITE_IMAP_PASSWORD.strip()
    folder = (getattr(settings, "STAFF_INVITE_IMAP_FOLDER", None) or "INBOX").strip()

    stats = {"processed": 0, "replies": 0, "bounces": 0, "opt_out": 0, "unknown": 0, "skipped_dup": 0, "no_lead": 0, "errors": 0}

    try:
        if port == 993:
            conn = imaplib.IMAP4_SSL(host, port)
        else:
            conn = imaplib.IMAP4(host, port)
        conn.login(user, password)
        conn.select(folder)
        typ, data = conn.search(None, "UNSEEN")
        if typ != "OK":
            conn.logout()
            return {**stats, "errors": 1}
        ids = (data[0] or b"").split()
        ids = ids[-max_messages:]
        for num in ids:
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
                ext_id = f"imap-{folder}-{num.decode() if isinstance(num, bytes) else num}"
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
                    continue
                stats["processed"] += 1
                k = result.get("kind") or "unknown"
                if k == StaffOnboardingInviteInbound.KIND_REPLY:
                    stats["replies"] += 1
                elif k == StaffOnboardingInviteInbound.KIND_BOUNCE:
                    stats["bounces"] += 1
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
