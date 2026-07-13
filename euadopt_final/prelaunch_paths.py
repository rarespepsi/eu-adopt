"""
Căi accesibile fără autentificare când PRELAUNCH_MODE este activ.

Variantă strictă: fără înregistrare publică (/signup/ în afară de activare cont).
"""
from __future__ import annotations

import re

from django.conf import settings

# Fișă animal publicată — vizualizare anonimă (link Distribuie / QR), fără listă PT.
_PRELAUNCH_PET_FICHA_RE = re.compile(r"^/pets/\d+/?$")

# Prefixe URL (path trebuie să înceapă cu una dintre aceste valori).
PRELAUNCH_ANONYMOUS_PREFIXES: tuple[str, ...] = (
    "/login/",
    "/pub/go/",
    "/login/forgot-password/",
    "/login/reset-password/",
    "/signup/organizatie/",
    "/signup/verificare-sms/",
    "/signup/retrimite-sms/",
    "/signup/persoana-fizica/sms/",
    "/signup/verificare-email/",
    "/signup/retrimite-email/",
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
    if getattr(settings, "POPULATION_SUPERUSER_ONLY_LOGIN", False) and p.startswith(
        "/signup/organizatie/"
    ):
        return False
    if _PRELAUNCH_PET_FICHA_RE.match(p):
        return True
    return p.startswith(PRELAUNCH_ANONYMOUS_PREFIXES)


def is_prelaunch_public_request(request) -> bool:
    """Ca is_prelaunch_public_path, plus link invitație staff valid (?inv=)."""
    path = request.path or "/"
    if is_prelaunch_public_path(path):
        return True
    from home.staff_onboarding_invite import staff_invite_allows_signup_path

    return staff_invite_allows_signup_path(request)
