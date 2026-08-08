"""
Registru domenii EU-Adopt — sursă unică pentru ALLOWED_HOSTS, CSRF, redirect 301.

Portfolio Hostico: eu-adopt.ro/com/eu + euadopt.com/de/es/eu/fr/org.
Strategie B (aug 2026): .ro separat; .com hub; .de/.fr/.es active (limba TLD);
.eu/.org + cratimă → 301 la .com.
Nu adăuga TLD-uri neconfirmate (ex. .it).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class DomainRole(str, Enum):
    RO_PRIMARY = "ro_primary"  # eu-adopt.ro — site RO, fără redirect
    ACTIVE = "active"  # .com hub + .de/.fr/.es țară
    REDIRECT_301 = "redirect_301"  # .eu/.org + cratimă → euadopt.com


@dataclass(frozen=True)
class DomainEntry:
    host: str
    role: DomainRole
    note: str = ""
    redirect_to: str = ""
    # Opțional la REDIRECT_301 (ex. legacy); țările ACTIVE nu folosesc asta.
    redirect_lang: str = ""


# --- Registru confirmat cumpărat (apex + www) ---
EUADOPT_DOMAIN_REGISTRY: tuple[DomainEntry, ...] = (
    DomainEntry("eu-adopt.ro", DomainRole.RO_PRIMARY, "România — principal, nemodificat"),
    DomainEntry("www.eu-adopt.ro", DomainRole.RO_PRIMARY, "România — principal"),
    DomainEntry("euadopt.com", DomainRole.ACTIVE, "Hub EU — EN + selector limbi"),
    DomainEntry("www.euadopt.com", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.de", DomainRole.ACTIVE, "DE — limba germană, URL rămâne .de"),
    DomainEntry("www.euadopt.de", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.fr", DomainRole.ACTIVE, "FR — limba franceză"),
    DomainEntry("www.euadopt.fr", DomainRole.ACTIVE, ""),
    DomainEntry("euadopt.es", DomainRole.ACTIVE, "ES — limba spaniolă"),
    DomainEntry("www.euadopt.es", DomainRole.ACTIVE, ""),
    # Alias hub → .com
    DomainEntry("euadopt.eu", DomainRole.REDIRECT_301, "Alias → .com", redirect_to="euadopt.com"),
    DomainEntry("www.euadopt.eu", DomainRole.REDIRECT_301, "", redirect_to="www.euadopt.com"),
    DomainEntry("euadopt.org", DomainRole.REDIRECT_301, "Alias → .com", redirect_to="euadopt.com"),
    DomainEntry("www.euadopt.org", DomainRole.REDIRECT_301, "", redirect_to="www.euadopt.com"),
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
    return urlunsplit(("", "", parts.path or "/", urlencode(q), ""))


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
