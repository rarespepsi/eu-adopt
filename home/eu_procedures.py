"""
Proceduri produs: .ro (ecosistem complet) vs hub EU (.com / țări).

Același Django + aceeași bază de animale. Diferențele de flux (adopție,
navbar comercial, Servicii/Shop, transport în adopție) se citesc de aici —
nu împrăștiate ca `if eu_site_active` ad-hoc în view-uri.

UI limbi (etichete EN): `eu_ui_labels` / `eu_site_active`.
Blocare rute /shop|/servicii: tot `eu_site` middleware (aliniază cu flag-urile de aici).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SiteProcedures:
    """Flag-uri de procedură — o sursă de adevăr pentru RO vs EU."""

    is_eu: bool

    # Catalog / PT
    pt_country_filter: bool
    # Animalele pleacă din RO; pe EU filtram / etichetăm țara de destinație / listare
    animals_origin_romania: bool
    # EU: fără benzile cursive P1/P3 — casetele P2 umplu înălțimea
    pt_hide_marquee_strips: bool

    # Adopție — EU = prezentare + intermediere (cerere → mail ONG → stabilesc între ei)
    adoption_simple_intermediation: bool
    adoption_skip_pickup_choice: bool
    adoption_transport_in_flow: bool
    adoption_bonus_enabled: bool

    # Transport (pagină publică)
    transport_destination_country_field: bool
    # EU: cerere pe mail la transport@eu-adopt.ro (fără dispatch colaboratori)
    transport_email_inbox: bool

    # Suprafață comercială RO (navbar + coș); pe EU ascunse / blocate
    nav_servicii: bool
    nav_shop: bool
    nav_site_cart: bool


# .ro — flux complet (Servicii, Shop, transport în adopție, bonus, etc.)
RO_PROCEDURES = SiteProcedures(
    is_eu=False,
    pt_country_filter=False,
    animals_origin_romania=True,
    pt_hide_marquee_strips=False,
    adoption_simple_intermediation=False,
    adoption_skip_pickup_choice=False,
    adoption_transport_in_flow=True,
    adoption_bonus_enabled=True,
    transport_destination_country_field=False,
    transport_email_inbox=False,
    nav_servicii=True,
    nav_shop=True,
    nav_site_cart=True,
)

# Hub EU — catalog + intermediere adopție; fără ecosistemul comercial RO
EU_PROCEDURES = SiteProcedures(
    is_eu=True,
    pt_country_filter=True,
    animals_origin_romania=True,
    pt_hide_marquee_strips=True,
    adoption_simple_intermediation=True,
    adoption_skip_pickup_choice=True,
    adoption_transport_in_flow=False,
    adoption_bonus_enabled=False,
    transport_destination_country_field=True,
    transport_email_inbox=True,
    nav_servicii=False,
    nav_shop=False,
    nav_site_cart=False,
)


def procedures_for_eu_flag(eu_active: bool) -> SiteProcedures:
    return EU_PROCEDURES if eu_active else RO_PROCEDURES


def procedures_for_request(request) -> SiteProcedures:
    return procedures_for_eu_flag(bool(getattr(request, "eu_site_active", False)))


def procedures_context(request=None, *, eu_active: bool | None = None) -> dict[str, Any]:
    """
    Context template: `site_proc` (obiect) + `site_proc_*` bool-uri plate
    pentru condiții scurte în HTML.
    """
    if eu_active is None:
        if request is None:
            proc = RO_PROCEDURES
        else:
            proc = procedures_for_request(request)
    else:
        proc = procedures_for_eu_flag(bool(eu_active))
    flat = {f"site_proc_{k}": v for k, v in asdict(proc).items()}
    return {"site_proc": proc, **flat}
