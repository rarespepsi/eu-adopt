"""
Flux 2: postări manuale de pe pagina Facebook RO → traducere → DE/FR/ES/COM.

- RO este singura sursă Facebook.
- DE/FR/ES/COM nu sunt niciodată poll-uite / republicate.
- Postările auto (delivery RO cu facebook_post_id) sunt skipped_auto.
- Mirror oprit până EUADOPT_FACEBOOK_RO_MIRROR_ENABLED=1 + tokenuri piețe.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from home.facebook_markets import (
    FACEBOOK_MIRROR_TARGET_MARKETS,
    configured_markets,
    facebook_ro_mirror_enabled,
    facebook_ro_mirror_max_per_run,
    facebook_ro_mirror_since,
    market_creds,
)
from home.facebook_page_post import (
    KIND_RO_MIRROR,
    STATUS_PENDING,
    _graph_request,
    ensure_deliveries,
    process_delivery,
    refresh_outbound_aggregate,
)

logger = logging.getLogger(__name__)


def _is_our_auto_ro_post(fb_post_id: str) -> bool:
    from home.models import FacebookOutboundDelivery

    pid = (fb_post_id or "").strip()
    if not pid:
        return False
    return FacebookOutboundDelivery.objects.filter(
        market="ro",
        facebook_post_id=pid,
        status="posted",
    ).exists()


def fetch_ro_page_posts(*, limit: int = 25) -> tuple[list[dict[str, Any]], str | None]:
    """
    Test / producție: GET /{PAGE_ID_RO}/posts cu permisiunile existente.
    Returnează (posts, error_message). Nu loghează tokenul.
    """
    creds = market_creds("ro")
    if not creds.configured:
        return [], "RO page credentials missing"
    try:
        raw = _graph_request(
            page_id=creds.page_id,
            access_token=creds.access_token,
            path="posts",
            method="GET",
            params={
                "fields": "id,message,created_time,permalink_url,full_picture",
                "limit": str(max(1, min(int(limit), 50))),
            },
        )
        data = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(data, list):
            return [], "Răspuns posts fără data[]"
        return data, None
    except Exception as exc:
        logger.exception("fetch_ro_page_posts failed")
        return [], str(exc)[:500]


def _parse_fb_time(raw: str | None):
    if not raw:
        return None
    dt = parse_datetime(raw)
    if dt is None:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt


def ingest_ro_posts(posts: list[dict[str, Any]]) -> dict[str, int]:
    """Înregistrează postări RO noi; marchează auto / istorice (≤ since) ca skipped."""
    from home.models import FacebookRoInboundPost

    stats = {"new": 0, "skipped_auto": 0, "skipped_before_since": 0, "existing": 0}
    since = facebook_ro_mirror_since()
    for item in posts or []:
        pid = str(item.get("id") or "").strip()
        if not pid:
            continue
        existing = FacebookRoInboundPost.objects.filter(source_fb_post_id=pid).first()
        if existing:
            stats["existing"] += 1
            continue
        fb_created = _parse_fb_time(item.get("created_time"))
        message = (item.get("message") or "")[:10000]
        permalink = (item.get("permalink_url") or "")[:500]
        picture_url = (item.get("full_picture") or "")[:1000]
        if _is_our_auto_ro_post(pid):
            FacebookRoInboundPost.objects.create(
                source_fb_post_id=pid,
                message=message,
                permalink=permalink,
                picture_url=picture_url,
                fb_created_time=fb_created,
                status=FacebookRoInboundPost.STATUS_SKIPPED_AUTO,
                skip_reason="outbound_auto_ro",
            )
            stats["skipped_auto"] += 1
            continue
        # Nu republica istoric: tot ce e înainte de activare (sau fără created_time când since e setat).
        if since is not None and (fb_created is None or fb_created <= since):
            FacebookRoInboundPost.objects.create(
                source_fb_post_id=pid,
                message=message,
                permalink=permalink,
                picture_url=picture_url,
                fb_created_time=fb_created,
                status=FacebookRoInboundPost.STATUS_SKIPPED_AUTO,
                skip_reason="before_mirror_since",
            )
            stats["skipped_before_since"] += 1
            continue
        FacebookRoInboundPost.objects.create(
            source_fb_post_id=pid,
            message=message,
            permalink=permalink,
            picture_url=picture_url,
            fb_created_time=fb_created,
            status=FacebookRoInboundPost.STATUS_PENDING,
        )
        stats["new"] += 1
    return stats


def baseline_existing_ro_posts(*, max_pages: int = 10, page_size: int = 50) -> dict[str, int]:
    """
    Marchează postările RO deja publice ca omise (baseline la activare).
    Nu creează delivery / nu publică pe DE/FR/ES/COM.
    """
    from home.models import FacebookRoInboundPost

    stats = {"fetched": 0, "baselined": 0, "existing": 0, "pages": 0, "error": ""}
    creds = market_creds("ro")
    if not creds.configured:
        stats["error"] = "RO credentials missing"
        return stats

    after = None
    for _ in range(max(1, max_pages)):
        params: dict[str, Any] = {
            "fields": "id,message,created_time,permalink_url,full_picture",
            "limit": str(max(1, min(int(page_size), 100))),
        }
        if after:
            params["after"] = after
        try:
            raw = _graph_request(
                page_id=creds.page_id,
                access_token=creds.access_token,
                path="posts",
                method="GET",
                params=params,
            )
        except Exception as exc:
            stats["error"] = str(exc)[:300]
            break
        data = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(data, list) or not data:
            break
        stats["pages"] += 1
        stats["fetched"] += len(data)
        for item in data:
            pid = str(item.get("id") or "").strip()
            if not pid:
                continue
            existing = FacebookRoInboundPost.objects.filter(source_fb_post_id=pid).first()
            if existing:
                if existing.status == FacebookRoInboundPost.STATUS_PENDING:
                    existing.status = FacebookRoInboundPost.STATUS_SKIPPED_AUTO
                    existing.skip_reason = existing.skip_reason or "baseline_pre_activation"
                    existing.save(update_fields=["status", "skip_reason", "updated_at"])
                    stats["baselined"] += 1
                else:
                    stats["existing"] += 1
                continue
            FacebookRoInboundPost.objects.create(
                source_fb_post_id=pid,
                message=(item.get("message") or "")[:10000],
                permalink=(item.get("permalink_url") or "")[:500],
                picture_url=(item.get("full_picture") or "")[:1000],
                fb_created_time=_parse_fb_time(item.get("created_time")),
                status=FacebookRoInboundPost.STATUS_SKIPPED_AUTO,
                skip_reason="baseline_pre_activation",
            )
            stats["baselined"] += 1
        paging = raw.get("paging") if isinstance(raw, dict) else None
        cursors = paging.get("cursors") if isinstance(paging, dict) else None
        after = (cursors or {}).get("after") if isinstance(cursors, dict) else None
        if not after:
            break
    return stats


def enqueue_mirror_for_inbound(inbound, *, schedule: bool = False) -> Any:
    """Creează sursă ro_mirror + delivery doar pe DE/FR/ES/COM (fără RO)."""
    from home.models import FacebookOutboundPost

    targets = [
        m
        for m in FACEBOOK_MIRROR_TARGET_MARKETS
        if m in configured_markets(for_mirror_targets=True)
    ]
    if not targets:
        return None

    row, _ = FacebookOutboundPost.objects.get_or_create(
        kind=KIND_RO_MIRROR,
        object_id=int(inbound.pk),
        defaults={"status": STATUS_PENDING},
    )
    ensure_deliveries(row, markets=targets)
    inbound.outbound = row
    inbound.save(update_fields=["outbound", "updated_at"])
    if schedule:
        for d in row.deliveries.filter(status=STATUS_PENDING):
            process_delivery(d.pk)
    return row


def process_pending_inbounds(*, limit: int | None = None) -> dict[str, int]:
    from home.models import FacebookRoInboundPost

    stats = {"mirrored": 0, "failed": 0, "posted_deliveries": 0}
    if not facebook_ro_mirror_enabled():
        return stats
    targets = configured_markets(for_mirror_targets=True)
    if not targets:
        return stats

    qs = FacebookRoInboundPost.objects.filter(
        status=FacebookRoInboundPost.STATUS_PENDING
    ).order_by("fb_created_time", "pk")
    max_n = limit if limit is not None else facebook_ro_mirror_max_per_run()
    qs = qs[:max_n]

    for inbound in qs:
        try:
            if not (inbound.message or "").strip() and not (inbound.picture_url or "").strip():
                inbound.status = FacebookRoInboundPost.STATUS_FAILED
                inbound.error = "Fără mesaj / imagine"
                inbound.save(update_fields=["status", "error", "updated_at"])
                stats["failed"] += 1
                continue
            row = enqueue_mirror_for_inbound(inbound, schedule=False)
            if row is None:
                inbound.status = FacebookRoInboundPost.STATUS_FAILED
                inbound.error = "Nicio piață mirror configurată"
                inbound.save(update_fields=["status", "error", "updated_at"])
                stats["failed"] += 1
                continue
            for d in row.deliveries.filter(status__in=("pending", "failed")).order_by("market"):
                if d.status == "failed":
                    d.status = "pending"
                    d.save(update_fields=["status", "updated_at"])
                result = process_delivery(d.pk)
                if result.ok:
                    stats["posted_deliveries"] += 1
            refresh_outbound_aggregate(row)
            inbound.status = FacebookRoInboundPost.STATUS_PROCESSED
            inbound.error = ""
            inbound.save(update_fields=["status", "error", "updated_at", "outbound"])
            stats["mirrored"] += 1
        except Exception as exc:
            logger.exception("process inbound %s", inbound.pk)
            inbound.status = FacebookRoInboundPost.STATUS_FAILED
            inbound.error = str(exc)[:500]
            inbound.save(update_fields=["status", "error", "updated_at"])
            stats["failed"] += 1
    return stats


def run_ro_mirror_poll(*, limit: int | None = None) -> dict[str, Any]:
    """
    Poll RO posts + mirror pe piețele configurate.
    Dacă mirror e off: doar poate fi folosit pentru test fetch (nu mirror).
    """
    out: dict[str, Any] = {
        "enabled": facebook_ro_mirror_enabled(),
        "fetch_error": None,
        "ingest": {},
        "mirror": {},
    }
    posts, err = fetch_ro_page_posts(limit=limit or facebook_ro_mirror_max_per_run())
    if err:
        out["fetch_error"] = err
        return out
    out["ingest"] = ingest_ro_posts(posts)
    if facebook_ro_mirror_enabled():
        out["mirror"] = process_pending_inbounds(limit=limit)
    return out
