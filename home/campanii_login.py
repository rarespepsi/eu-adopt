"""După login: unii PF merg direct la formularul de campanii sterilizare."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse


def campanii_login_landing_emails() -> frozenset[str]:
    raw = getattr(settings, "CAMPANII_LOGIN_LANDING_EMAILS", None)
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())
    return frozenset(str(e).strip().lower() for e in raw if str(e).strip())


def is_campanii_login_landing_user(user) -> bool:
    email = (getattr(user, "email", None) or "").strip().lower()
    return bool(email) and email in campanii_login_landing_emails()


def is_default_post_login_next(next_url: str) -> bool:
    path = (next_url or "").strip()
    if not path or path == "/":
        return True
    home = reverse("home")
    return path.rstrip("/") == home.rstrip("/")


def landing_after_login(user, next_url: str) -> str:
    """Respectă ?next= explicit; altfel campanii-only → fișa cont cu formular deschis."""
    nxt = (next_url or "").strip() or "/"
    if is_campanii_login_landing_user(user) and is_default_post_login_next(nxt):
        return reverse("account") + "?campanie=1"
    return nxt
