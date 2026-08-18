"""Sanitize ?next= after login/signup.

Crawlers follow Intra ↔ Creează cont and nest next= until nginx 504s.
Real destinations (pets, I Love, donations, account) stay intact.
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

# Pet + query (from/back) is typically < 200 chars. Nested crawler URLs are kilobytes.
MAX_NEXT_LEN = 600
_UNWRAP_DEPTH = 8

_AUTH_EXACT = frozenset(
    {
        "/login",
        "/signup",
        "/inscriere",
        "/logout",
    }
)
_AUTH_PREFIXES = (
    "/login/",
    "/signup/",
)


def path_is_auth(path: str) -> bool:
    p = (path or "/").split("?")[0]
    p = p.rstrip("/") or "/"
    if p in _AUTH_EXACT:
        return True
    raw = path.split("?")[0]
    return any(raw.startswith(pref) for pref in _AUTH_PREFIXES)


def sanitize_post_login_next(raw: str | None) -> str:
    """Return a same-site path (+ optional query) safe after login, or ''."""
    value = unquote((raw or "").strip())
    for _ in range(_UNWRAP_DEPTH):
        if not value:
            return ""
        if len(value) > MAX_NEXT_LEN:
            return ""
        if not value.startswith("/") or value.startswith("//"):
            return ""
        if "\n" in value or "\r" in value or "\\" in value:
            return ""
        parsed = urlparse(value)
        path = parsed.path or "/"
        if parsed.scheme or parsed.netloc:
            return ""
        if path_is_auth(path):
            inner = parse_qs(parsed.query).get("next", [""])[0]
            value = unquote(inner).strip() if inner else ""
            continue
        out = path
        if parsed.query:
            out = f"{path}?{parsed.query}"
        if len(out) > MAX_NEXT_LEN:
            return path if len(path) <= MAX_NEXT_LEN else ""
        return out
    return ""


def apply_sanitized_next_to_querydict(q) -> None:
    """In-place: keep a safe next, drop a looping/oversized one."""
    if "next" not in q:
        return
    clean = sanitize_post_login_next(q.get("next") or "")
    if clean:
        q["next"] = clean
    else:
        q.pop("next", None)
