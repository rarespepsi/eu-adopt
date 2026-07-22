"""
Registru domenii EU-Adopt — sursă unică pentru ALLOWED_HOSTS, CSRF, redirect 301.

Actualizat din portfolio cumpărat (Hostico, iul 2026). Nu adăuga TLD-uri neconfirmate
(ex. .it) până nu există în registrul de mai jos.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class DomainRole(str, Enum):
    RO_PRIMARY = "ro_primary"  # eu-adopt.ro — site RO, fără redirect
    ACTIVE = "active"  # euadopt.* — același Django, același conținut ca .ro (faza infra)
    REDIRECT_301 = "redirect_301"  # eu-adopt.* (non-RO) → euadopt.*


@dataclass(frozen=True)
class DomainEntry:
    host: str
    role: DomainRole
    note: str = ""
    redirect_to: str = ""


# --- Registru confirmat cumpărat (apex + www unde e cazul) ---
EUADOPT_DOMAIN_REGISTRY: tuple[DomainEntry, ...] = (
    DomainEntry("eu-adopt.ro", DomainRole.RO_PRIMARY, "România — principal, nemodificat"),
    DomainEntry("www.eu-adopt.ro", DomainRole.RO_PRIMARY, "România — principal"),
    DomainEntry("euadopt.com", DomainRole.ACTIVE, "Hub / internațional — fără cratimă"),
    DomainEntry("www.euadopt.com", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.eu", DomainRole.ACTIVE, ""),
    DomainEntry("www.euadopt.eu", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.org", DomainRole.ACTIVE, ""),
    DomainEntry("www.euadopt.org", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.de", DomainRole.ACTIVE, "Germania — faza infra = același site"),
    DomainEntry("www.euadopt.de", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.fr", DomainRole.ACTIVE, "Franța"),
    DomainEntry("www.euadopt.fr", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.es", DomainRole.ACTIVE, "Spania"),
    DomainEntry("www.euadopt.es", DomainRole.ACTIVE, ""),
    DomainEntry(
        "eu-adopt.com",
        DomainRole.REDIRECT_301,
        "Dublaj cu cratimă",
        redirect_to="euadopt.com",
    ),
    DomainEntry(
        "www.eu-adopt.com",
        DomainRole.REDIRECT_301,
        "",
        redirect_to="www.euadopt.com",
    ),
    DomainEntry(
        "eu-adopt.eu",
        DomainRole.REDIRECT_301,
        "",
        redirect_to="euadopt.eu",
    ),
    DomainEntry(
        "www.eu-adopt.eu",
        DomainRole.REDIRECT_301,
        "",
        redirect_to="www.euadopt.eu",
    ),
)

# Nu sunt în cont (iul 2026): euadopt.it, eu-adopt.org, euadopt.ro — nu le adăuga.


def registry_by_host() -> dict[str, DomainEntry]:
    return {e.host.lower(): e for e in EUADOPT_DOMAIN_REGISTRY}


def hyphen_redirect_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for e in EUADOPT_DOMAIN_REGISTRY:
        if e.role == DomainRole.REDIRECT_301 and e.redirect_to:
            out[e.host.lower()] = e.redirect_to.lower()
    return out


def allowed_hosts_from_registry(*extra: str) -> list[str]:
    hosts = sorted({e.host.lower() for e in EUADOPT_DOMAIN_REGISTRY})
    for h in extra:
        h = (h or "").strip().lower()
        if h and h not in hosts:
            hosts.append(h)
    return hosts


def csrf_trusted_origins_from_registry() -> list[str]:
    origins: list[str] = []
    for e in EUADOPT_DOMAIN_REGISTRY:
        if e.role in (DomainRole.RO_PRIMARY, DomainRole.ACTIVE, DomainRole.REDIRECT_301):
            origins.append(f"https://{e.host.lower()}")
    return sorted(set(origins))


def active_primary_hosts() -> frozenset[str]:
    return frozenset(
        e.host.lower()
        for e in EUADOPT_DOMAIN_REGISTRY
        if e.role in (DomainRole.RO_PRIMARY, DomainRole.ACTIVE)
    )


def is_romania_primary_host(host: str | None) -> bool:
    h = (host or "").strip().lower().split(":")[0]
    return h in ("eu-adopt.ro", "www.eu-adopt.ro")


def _ascii_safe(text: str) -> str:
    """Console-safe (Windows cp1252): diacritice -> ASCII aproximativ."""
    if not text:
        return text
    repl = str.maketrans(
        "ăâîșțĂÂÎȘȚ",
        "aaistAAIST",
    )
    return text.translate(repl).replace("—", "-")


def format_registry_table() -> str:
    lines = [
        "Host | Rol | Redirect -> | Nota",
        "--- | --- | --- | ---",
    ]
    for e in EUADOPT_DOMAIN_REGISTRY:
        redir = e.redirect_to or "-"
        note = _ascii_safe(e.note) if e.note else "-"
        lines.append(f"{e.host} | {e.role.value} | {redir} | {note}")
    return "\n".join(lines)


def nginx_server_names_active() -> str:
    names = [e.host for e in EUADOPT_DOMAIN_REGISTRY if e.role in (DomainRole.RO_PRIMARY, DomainRole.ACTIVE)]
    return " ".join(names)


def nginx_server_names_redirect() -> str:
    names = [e.host for e in EUADOPT_DOMAIN_REGISTRY if e.role == DomainRole.REDIRECT_301]
    return " ".join(names)
