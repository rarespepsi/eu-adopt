"""
Piețe Facebook EU-Adopt (RO/DE/FR/ES/COM).

Tokenurile stau doar în .env (Page token sau System User token —
aceeași cheie de env). Pentru New Page Experience, Graph cere Page token:
dacă în env e System User token, luăm tokenul de pagină din GET /me/accounts.
Nu loga / nu afișa tokenuri.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)

# Cache: (sha256(env_token), page_id) → page access token. Nu stocăm env tokenul brut ca cheie.
_page_token_cache: dict[tuple[str, str], str] = {}
_accounts_fetched_for: set[str] = set()
_accounts_fail_until: dict[str, float] = {}
_page_token_lock = threading.Lock()
_ACCOUNTS_FAIL_TTL_SEC = 60.0
_ACCOUNTS_TIMEOUT_SEC = 12

FACEBOOK_MARKETS: tuple[str, ...] = ("ro", "de", "fr", "es", "com")
# Mirror FB: doar din RO către aceste piețe (niciodată invers).
FACEBOOK_MIRROR_TARGET_MARKETS: tuple[str, ...] = ("de", "fr", "es", "com")

MARKET_LANG: dict[str, str] = {
    "ro": "ro",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "com": "en",
}

MARKET_LANG_NAME: dict[str, str] = {
    "ro": "Romanian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "com": "English",
}


@dataclass(frozen=True)
class FacebookMarketCreds:
    market: str
    page_id: str
    # Nu loga / nu afișa tokenul.
    access_token: str

    @property
    def configured(self) -> bool:
        return bool(self.page_id and self.access_token)


def facebook_auto_post_enabled() -> bool:
    return bool(getattr(settings, "FACEBOOK_AUTO_POST_ENABLED", False))


def facebook_graph_version() -> str:
    v = (getattr(settings, "FACEBOOK_GRAPH_API_VERSION", "") or "v21.0").strip()
    return v if v.startswith("v") else f"v{v}"


def facebook_max_posts_per_day() -> int:
    return max(1, int(getattr(settings, "FACEBOOK_MAX_POSTS_PER_DAY", 10) or 10))


def facebook_ro_mirror_enabled() -> bool:
    return bool(getattr(settings, "FACEBOOK_RO_MIRROR_ENABLED", False))


def facebook_ro_mirror_max_per_run() -> int:
    return max(1, int(getattr(settings, "FACEBOOK_RO_MIRROR_MAX_PER_RUN", 10) or 10))


def facebook_ro_mirror_since():
    """
    Momentul de activare: postări RO cu created_time <= since nu se oglindesc.
    Returnează datetime aware sau None.
    """
    raw = (getattr(settings, "FACEBOOK_RO_MIRROR_SINCE", "") or "").strip()
    if not raw:
        return None
    from datetime import datetime

    from django.utils import timezone
    from django.utils.dateparse import parse_datetime

    dt = parse_datetime(raw)
    if dt is None:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt



def _env_page_id(market: str) -> str:
    m = (market or "").strip().lower()
    if m == "ro":
        # Compat: EUADOPT_FACEBOOK_PAGE_ID sau _RO
        return (
            (getattr(settings, "FACEBOOK_PAGE_ID_RO", "") or "").strip()
            or (getattr(settings, "FACEBOOK_PAGE_ID", "") or "").strip()
        )
    return (getattr(settings, f"FACEBOOK_PAGE_ID_{m.upper()}", "") or "").strip()


def _env_token(market: str) -> str:
    m = (market or "").strip().lower()
    if m == "ro":
        return (
            (getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN_RO", "") or "").strip()
            or (getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN", "") or "").strip()
        )
    return (getattr(settings, f"FACEBOOK_PAGE_ACCESS_TOKEN_{m.upper()}", "") or "").strip()


def _token_sha(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def looks_like_facebook_token(token: str) -> bool:
    """Tokenurile Graph (System User / Page) încep de obicei cu EAA. Testele folosesc alt prefix."""
    return (token or "").startswith("EAA")


def clear_page_token_cache() -> None:
    """Doar teste / reload. Nu loghează valori."""
    with _page_token_lock:
        _page_token_cache.clear()
        _accounts_fetched_for.clear()
        _accounts_fail_until.clear()


def _graph_error_message(err_body: str) -> str:
    try:
        parsed = json.loads(err_body) if err_body else {}
    except json.JSONDecodeError:
        return (err_body or "")[:240]
    err = parsed.get("error") if isinstance(parsed, dict) else None
    if not isinstance(err, dict):
        return (err_body or "")[:240]
    msg = (err.get("message") or "").strip()
    code = err.get("code")
    sub = err.get("error_subcode")
    return f"{msg} code={code} subcode={sub}"[:300]


def _fetch_me_accounts_page_tokens(env_token: str) -> dict[str, str] | None:
    """
    GET /me/accounts. Returnează {page_id: page_token} sau None la eroare de rețea/Graph.
    Nu include tokenul în loguri / excepții.
    """
    version = facebook_graph_version()
    params = {
        "fields": "id,access_token",
        "limit": "50",
        "access_token": env_token,
    }
    url = f"https://graph.facebook.com/{version}/me/accounts?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=_ACCOUNTS_TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.warning("facebook /me/accounts HTTP %s: %s", e.code, _graph_error_message(err_body))
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        logger.warning("facebook /me/accounts failed: %s", type(e).__name__)
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        logger.warning("facebook /me/accounts: răspuns fără data[]")
        return None
    out: dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("id") or "").strip()
        tok = str(row.get("access_token") or "").strip()
        if pid and tok:
            out[pid] = tok
    return out


def resolve_page_access_token(page_id: str, env_token: str) -> str:
    """
    Dacă env_token e System User, întoarce Page Access Token pentru page_id.
    La eroare / pagină lipsă / token de test: env_token neschimbat.
    """
    page_id = (page_id or "").strip()
    env_token = (env_token or "").strip()
    if not page_id or not env_token or not looks_like_facebook_token(env_token):
        return env_token
    sha = _token_sha(env_token)
    cache_key = (sha, page_id)
    now = time.monotonic()
    with _page_token_lock:
        cached = _page_token_cache.get(cache_key)
        if cached:
            return cached
        if now < _accounts_fail_until.get(sha, 0):
            return env_token
        already = sha in _accounts_fetched_for
    if already:
        return env_token
    mapping = _fetch_me_accounts_page_tokens(env_token)
    with _page_token_lock:
        if mapping is None:
            _accounts_fail_until[sha] = time.monotonic() + _ACCOUNTS_FAIL_TTL_SEC
            return env_token
        _accounts_fetched_for.add(sha)
        for pid, tok in mapping.items():
            _page_token_cache[(sha, pid)] = tok
        return _page_token_cache.get(cache_key, env_token)


def market_creds(market: str) -> FacebookMarketCreds:
    m = (market or "").strip().lower()
    page_id = _env_page_id(m)
    env_token = _env_token(m)
    return FacebookMarketCreds(
        market=m,
        page_id=page_id,
        access_token=resolve_page_access_token(page_id, env_token),
    )


def configured_markets(*, for_mirror_targets: bool = False) -> list[str]:
    """Piețe cu page_id + token setate. RO e inclusă dacă auto-post e activ."""
    if for_mirror_targets:
        candidates = FACEBOOK_MIRROR_TARGET_MARKETS
    else:
        if not facebook_auto_post_enabled():
            return []
        candidates = FACEBOOK_MARKETS
    out: list[str] = []
    for m in candidates:
        if _env_page_id(m) and _env_token(m):
            out.append(m)
    return out


def market_lang(market: str) -> str:
    return MARKET_LANG.get((market or "").strip().lower(), "en")
