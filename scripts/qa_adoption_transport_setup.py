"""
Aliniere date DB pentru QA: adopție (inimioare Servicii) + dispatch transport.

Condiții din cod:
- Inimioare: județ adoptator (UserProfile.judet sau company_judet) trebuie setat;
  oferta trebuie să aibă același județ pe profilul colaboratorului (company_judet sau judet),
  normalizat cu casefold (vezi home.views._norm_county_str / _offer_collab_county_norm).
- Transport: TransportOperatorProfile aprobat + transport_national; județ ȘI oraș cerere
  trebuie să coincidă cu profilul transportatorului (_norm), vezi home.transport_dispatch.

Rulare (din rădăcina proiectului):
  python scripts/qa_adoption_transport_setup.py           # aplică zona canonică
  python scripts/qa_adoption_transport_setup.py --dry-run
  python scripts/qa_adoption_transport_setup.py --magazin-remote   # dm în alt județ → fără inimioare magazin în zona QA (Iași)

După aliniere: rulează opțional seed oferte/anunțuri:
  python scripts/seed_portfolio.py
"""
from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")

import django

django.setup()

from django.contrib.auth import get_user_model

from home.models import TransportOperatorProfile, UserProfile

User = get_user_model()

# Zonă unică QA: adoptatorul lasă formularul cu aceste valori (prefill din profil).
# Iași — aliniat la dropdown-uri site + verificare transport / dispatch cu `rares`.
QA_COUNTY = "Iași"
QA_CITY = "Iași"

# PF / conturi care pot juca rolul adoptatorului (județ persoană).
PF_ADOPTERS = ("dpf", "e2e_pf")

# ONG privat care poate adopta (test M8): același județ pe profil.
ONG_PRIVATE_ADOPTER = ("radu",)

# Colaboratori: ofertele iau județul din company_* pe profil.
COLLAB_BONUS_LOCAL = ("nccristescu", "dg1", "dg2", "dm")

# Transportator: trebuie să coincidă județ + oraș cu TVR.
TRANSPORT_USER = "rares"


def _get_user(username: str):
    return User.objects.filter(username__iexact=username.strip()).first()


def apply_pf_zone(username: str, county: str, city: str) -> str:
    u = _get_user(username)
    if not u:
        return f"SKIP missing user {username!r}"
    prof, _ = UserProfile.objects.get_or_create(user=u)
    prof.judet = county
    prof.oras = city
    prof.save(update_fields=["judet", "oras", "updated_at"])
    return f"OK PF zone {username}: judet={county!r} oras={city!r}"


def apply_org_private_adopter_zone(username: str, county: str, city: str) -> str:
    u = _get_user(username)
    if not u:
        return f"SKIP missing user {username!r}"
    prof, _ = UserProfile.objects.get_or_create(user=u)
    prof.company_judet = county
    prof.company_oras = city
    prof.judet = county
    prof.oras = city
    prof.save(update_fields=["company_judet", "company_oras", "judet", "oras", "updated_at"])
    return f"OK ONG/privat zone {username}: company + persoană = {county} / {city}"


def apply_collab_company_zone(username: str, county: str, city: str) -> str:
    u = _get_user(username)
    if not u:
        return f"SKIP missing user {username!r}"
    prof, _ = UserProfile.objects.get_or_create(user=u)
    prof.company_judet = county
    prof.company_oras = city
    prof.save(update_fields=["company_judet", "company_oras", "updated_at"])
    return f"OK collab company zone {username}: {county} / {city}"


def apply_transport_operator(county: str, city: str, dry_run: bool) -> list[str]:
    out: list[str] = []
    u = _get_user(TRANSPORT_USER)
    if not u:
        out.append(f"SKIP missing user {TRANSPORT_USER!r}")
        return out
    prof, _ = UserProfile.objects.get_or_create(user=u)
    if not dry_run:
        prof.judet = county
        prof.oras = city
        prof.company_judet = county
        prof.company_oras = city
        prof.save(
            update_fields=["judet", "oras", "company_judet", "company_oras", "updated_at"]
        )
    out.append(
        f"{'WOULD SET' if dry_run else 'OK'} transport profile {TRANSPORT_USER}: judet/oras + company = {county} / {city}"
    )
    if dry_run:
        out.append("  (dry-run: TransportOperatorProfile not written)")
        return out
    top, _ = TransportOperatorProfile.objects.update_or_create(
        user=u,
        defaults={
            "approval_status": TransportOperatorProfile.APPROVAL_APPROVED,
            "transport_national": True,
            "transport_international": False,
            "max_caini": 4,
            "max_pisici": 4,
        },
    )
    out.append(
        f"OK TransportOperatorProfile user_id={u.pk}: status={top.approval_status}, national={top.transport_national}"
    )
    return out


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="QA: align county/city for adoption bonus + transport dispatch.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only.")
    parser.add_argument(
        "--magazin-remote",
        action="store_true",
        help="Mută doar colaboratorul 'dm' în Timiș/Timișoara (fără inimioare canal magazin pentru adoptatori din zona QA / Iași).",
    )
    args = parser.parse_args()
    dry = args.dry_run

    lines: list[str] = []
    county = QA_COUNTY
    city = QA_CITY
    shop_county, shop_city = ("Timiș", "Timișoara") if args.magazin_remote else (county, city)

    for uname in PF_ADOPTERS:
        if dry:
            lines.append(f"WOULD {apply_pf_zone(uname, county, city)}")
        else:
            lines.append(apply_pf_zone(uname, county, city))

    for uname in ONG_PRIVATE_ADOPTER:
        if dry:
            lines.append(f"WOULD {apply_org_private_adopter_zone(uname, county, city)}")
        else:
            lines.append(apply_org_private_adopter_zone(uname, county, city))

    for uname in COLLAB_BONUS_LOCAL:
        c, ct = (shop_county, shop_city) if uname == "dm" and args.magazin_remote else (county, city)
        if dry:
            lines.append(f"WOULD apply_collab_company_zone({uname!r}, {c!r}, {ct!r})")
        else:
            lines.append(apply_collab_company_zone(uname, c, ct))

    lines.extend(apply_transport_operator(county, city, dry))

    print("\n".join(lines))
    print("\nDone. Oferte [seed]: python scripts/seed_portfolio.py (dacă lipsesc).")


if __name__ == "__main__":
    main()
