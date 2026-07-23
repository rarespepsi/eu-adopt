"""
Publicitate pe piețe: RO (.ro, clienți) vs EU (.com + oglindă pe .de/.fr/.es).
"""
from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings

PUB_MARKET_RO = "ro"
PUB_MARKET_EU = "eu"
PUB_MARKETS = frozenset({PUB_MARKET_RO, PUB_MARKET_EU})


def normalize_pub_market(raw: str | None) -> str:
    m = (raw or PUB_MARKET_RO).strip().lower()
    return m if m in PUB_MARKETS else PUB_MARKET_RO


def pub_market_for_request(request) -> str:
    """Pe host EU (skin activ) → eu; altfel ro. Fallback sigur: ro."""
    try:
        from home.eu_site import eu_product_skin_enabled, is_eu_site_host

        if eu_product_skin_enabled() and is_eu_site_host(request.get_host()):
            return PUB_MARKET_EU
    except Exception:
        pass
    return PUB_MARKET_RO


def localize_pub_link_for_market(link: str, market: str) -> str:
    """
    Pe piața EU: link absolut către eu-adopt.ro → doar path (rămâne pe domeniul curent).
    """
    u = (link or "").strip()
    if not u or normalize_pub_market(market) != PUB_MARKET_EU:
        return u
    try:
        p = urlparse(u)
    except Exception:
        return u
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    ro_hosts = {"eu-adopt.ro", "www.eu-adopt.ro"}
    # include settings if present
    for h in getattr(settings, "ALLOWED_HOSTS", []) or []:
        if isinstance(h, str) and "eu-adopt.ro" in h.lower():
            ro_hosts.add(h.lower().lstrip("."))
    if host in ro_hosts or host == "eu-adopt.ro":
        path = p.path or "/"
        if p.query:
            path = f"{path}?{p.query}"
        if p.fragment:
            path = f"{path}#{p.fragment}"
        return path
    return u
