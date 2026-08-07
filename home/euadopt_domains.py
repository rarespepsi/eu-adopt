"""
Registru domenii EU-Adopt — sursă unică pentru ALLOWED_HOSTS, CSRF, redirect 301.

Portfolio Hostico (confirmat): eu-adopt.ro/com/eu + euadopt.com/de/es/eu/fr/org.
Strategie UX (aug 2026): .ro separat; tot restul → euadopt.com (Țară: + ?eu_lang=).
Nu adăuga TLD-uri neconfirmate (ex. .it) până nu există în registrul de mai jos.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class DomainRole(str, Enum):
    RO_PRIMARY = "ro_primary"  # eu-adopt.ro — site RO, fără redirect
    ACTIVE = "active"  # hub EU (euadopt.com) — același Django
    REDIRECT_301 = "redirect_301"  # tot non-.ro non-hub → euadopt.com


@dataclass(frozen=True)
class DomainEntry:
    host: str
    role: DomainRole
    note: str = ""
    redirect_to: str = ""
    # La 301 către .com: limba din TLD (ex. de → ?eu_lang=de). Gol = fără param.
    redirect_lang: str = ""


# --- Registru confirmat cumpărat (apex + www) ---
EUADOPT_DOMAIN_REGISTRY: tuple[DomainEntry, ...] = (
    DomainEntry("eu-adopt.ro", DomainRole.RO_PRIMARY, "România — principal, nemodificat"),
    DomainEntry("www.eu-adopt.ro", DomainRole.RO_PRIMARY, "România — principal"),
    DomainEntry("euadopt.com", DomainRole.ACTIVE, "Hub EU unic — EN + selector limbi"),
    DomainEntry("www.euadopt.com", DomainRole.ACTIVE, ""),
    # Țară → .com + limba TLD
    DomainEntry(
        "euadopt.de",
        DomainRole.REDIRECT_301,
        "DE → .com + limba germană",
        redirect_to="euadopt.com",
        redirect_lang="de",
    ),
    DomainEntry(
        "www.euadopt.de",
        DomainRole.REDIRECT_301,
        "",
        redirect_to="www.euadopt.com",
        redirect_lang="de",
    ),
    DomainEntry(
        "euadopt.fr",
        DomainRole.REDIRECT_301,
        "FR → .com + limba franceză",
        redirect_to="euadopt.com",
        redirect_lang="fr",
    ),
    DomainEntry(
        "www.euadopt.fr",
        DomainRole.REDIRECT_301,
        "",
        redirect_to="www.euadopt.com",
        redirect_lang="fr",
    ),
    DomainEntry(
        "euadopt.es",
        DomainRole.REDIRECT_301,
        "ES → .com + limba spaniolă",
        redirect_to="euadopt.com",
        redirect_lang="es",
    ),
    DomainEntry(
        "www.euadopt.es",
        DomainRole.REDIRECT_301,
        "",
        redirect_to="www.euadopt.com",
        redirect_lang="es",
    ),
    # Alias hub → .com
    DomainEntry("euadopt.eu", DomainRole.REDIRECT_301, "Alias → .com", redirect_to="euadopt.com"),
    DomainEntry("www.euadopt.eu", DomainRole.REDIRECT_301, "", redirect_to="www.euadopt.com"),
    DomainEntry("euadopt.org", DomainRole.REDIRECT_301, "Alias → .com", redirect_to="euadopt.com"),
    DomainEntry("www.euadopt.org", DomainRole.REDIRECT_301, "", redirect_to="www.euadopt.com"),
    # Cratimă → fără cratimă (.com)
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
        "Cratimă → hub .com",
        redirect_to="euadopt.com",
    ),
    DomainEntry(
        "www.eu-adopt.eu",
        DomainRole.REDIRECT_301,
        "",
        redirect_to="www.euadopt.com",
    ),
)

# Nu sunt în cont (Hostico): euadopt.it, eu-adopt.org, euadopt.ro — nu le adăuga.


def registry_by_host() -> dict[str, DomainEntry]:
    return {e.host.lower(): e for e in EUADOPT_DOMAIN_REGISTRY}


def hyphen_redirect_map() -> dict[str, str]:
    """Map host → redirect_to (toate rolurile REDIRECT_301)."""
    out: dict[str, str] = {}
    for e in EUADOPT_DOMAIN_REGISTRY:
        if e.role == DomainRole.REDIRECT_301 and e.redirect_to:
            out[e.host.lower()] = e.redirect_to.lower()
    return out


def redirect_lang_for_host(host: str | None) -> str | None:
    h = (host or "").strip().lower().split(":")[0]
    e = registry_by_host().get(h)
    if e and e.redirect_lang:
        return e.redirect_lang.strip().lower()
    return None


def inject_query_param(full_path: str, key: str, value: str) -> str:
    """Adaugă/înlocuiește un query param pe path (+ query) fără a pierde restul."""
    path = full_path or "/"
    if not path.startswith("/"):
        path = "/" + path
    parts = urlsplit(path)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != key]
    q.append((key, value))
    return urlunsplit(("", "", parts.path or "/", "", urlencode(q)))


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
        "Host | Rol | Redirect -> | Lang | Nota",
        "--- | --- | --- | --- | ---",
    ]
    for e in EUADOPT_DOMAIN_REGISTRY:
        redir = e.redirect_to or "-"
        lang = e.redirect_lang or "-"
        note = _ascii_safe(e.note) if e.note else "-"
        lines.append(f"{e.host} | {e.role.value} | {redir} | {lang} | {note}")
    return "\n".join(lines)


def nginx_server_names_active() -> str:
    names = [e.host for e in EUADOPT_DOMAIN_REGISTRY if e.role in (DomainRole.RO_PRIMARY, DomainRole.ACTIVE)]
    return " ".join(names)


def nginx_server_names_redirect() -> str:
    names = [e.host for e in EUADOPT_DOMAIN_REGISTRY if e.role == DomainRole.REDIRECT_301]
    return " ".join(names)
