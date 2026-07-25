"""
Căi accesibile fără autentificare când PRELAUNCH_MODE este activ.

Vizitator anonim pe .ro (vizualizare): doar HOME (+ fișe animal pe link/QR).
PT / Servicii și restul site-ului cer login.
"""
from __future__ import annotations

import re

from django.conf import settings

# Fișă animal publicată — vizualizare anonimă (link Distribuie / QR).
_PRELAUNCH_PET_FICHA_RE = re.compile(r"^/pets/\d+/?$")
# URL frumos animal: /caini|pisici|altele/<slug>/
_PRELAUNCH_PET_SLUG_RE = re.compile(r"^/(caini|pisici|altele)/[a-z0-9\-]+/?$", re.I)

# Prefixe URL (path trebuie să înceapă cu una dintre aceste valori).
# NU adăuga "/" aici — ar deschide tot site-ul.
PRELAUNCH_ANONYMOUS_PREFIXES: tuple[str, ...] = (
    "/login/",
    "/pub/go/",
    "/inscriere/",
    "/signup/alege-tip/",
    "/signup/persoana-fizica/",
    "/signup/colaborator/",
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
    "/cont/editeaza/confirmare-email/",
    "/adaposturi/",
    "/admin/",
    "/static/",
    "/media/",
    "/admin-analysis/add-user/invite-inbound-webhook/",
)

# Doar HOME (și favicon) — path-uri exacte.
PRELAUNCH_ANONYMOUS_EXACT: frozenset[str] = frozenset(
    {
        "/favicon.ico",
        "/",
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
    if _PRELAUNCH_PET_SLUG_RE.match(p):
        return True
    return p.startswith(PRELAUNCH_ANONYMOUS_PREFIXES)


def is_prelaunch_public_request(request) -> bool:
    """Ca is_prelaunch_public_path, plus link invitație staff valid (?inv=)."""
    path = request.path or "/"
    if is_prelaunch_public_path(path):
        return True
    from home.staff_onboarding_invite import staff_invite_allows_signup_path

    return staff_invite_allows_signup_path(request)
