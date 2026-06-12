"""
Căi accesibile fără autentificare când PRELAUNCH_MODE este activ.

Variantă strictă: fără înregistrare publică (/signup/ în afară de activare cont).
"""
from __future__ import annotations

# Prefixe URL (path trebuie să înceapă cu una dintre aceste valori).
PRELAUNCH_ANONYMOUS_PREFIXES: tuple[str, ...] = (
    "/login/",
    "/signup/verify-email/",
    "/signup/complete-login/",
    "/signup/check-activation-status/",
    "/admin/",
    "/static/",
    "/media/",
    "/admin-analysis/add-user/invite-inbound-webhook/",
)

PRELAUNCH_ANONYMOUS_EXACT: frozenset[str] = frozenset(
    {
        "/favicon.ico",
    }
)


def is_prelaunch_public_path(path: str) -> bool:
    """True dacă anonimul poate accesa path-ul în mod PRE-LAUNCH."""
    p = (path or "/").split("?", 1)[0]
    if not p.startswith("/"):
        p = "/" + p
    if p in PRELAUNCH_ANONYMOUS_EXACT:
        return True
    return p.startswith(PRELAUNCH_ANONYMOUS_PREFIXES)
