"""
Prospecte firme-mamă — retail / distribuție pentru animale de companie (România + op. în RO).

- Un singur rând per CUI (fără puncte de lucru multiple).
- account_kind=collaborator, collaborator_subtype=magazin.
- contact_phone / contact_email: din surse oficiale (site-uri); la --apply se completează
  sau se actualizează telefonul; emailul public se pune doar dacă lipsea sau era placeholder.

Exemplu:
  python manage.py import_pet_retail_holding_prospects
  python manage.py import_pet_retail_holding_prospects --apply
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from django.core.management.base import BaseCommand

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import PLACEHOLDER_EMAIL_SUFFIX, is_placeholder_lead_email


def _digits_cui(raw: str) -> str:
    return re.sub(r"\D", "", (raw or "").replace("RO", "").replace("ro", ""))[:32]


def _norm_phone(raw: str | None) -> str:
    t = re.sub(r"[\s.-]", "", (raw or "").strip())
    if not t:
        return ""
    return t[:40]


def _resolve_email(row: dict[str, Any], cui: str) -> str:
    ce = (row.get("contact_email") or "").strip()
    if ce and "@" in ce and "." in ce.split("@", 1)[-1]:
        return ce[:254].lower()
    return f"pet-holding-{cui}{PLACEHOLDER_EMAIL_SUFFIX}"


# contact_* = surse oficiale (site contact / pagini legale), verificate manual înainte de invitații.
HOLDINGS: list[dict[str, Any]] = [
    {
        "company_legal_name": "PET PRODUCT S.R.L.",
        "company_cui": "11156707",
        "org_display_name": "Animax / Maxi Pet (Pet Network)",
        "display_name": "Pet Product SRL — retail pet (Animax, Maxi Pet)",
        "judet": "București",
        "oras": "Sector 6",
        "company_judet": "București",
        "company_oras": "Sector 6",
        "company_address": "Bd. Preciziei nr. 1, Preciziei Business Center, Tronson 1, Et. 2",
        "contact_phone": "0731777797",
        "contact_email": "contact@animax.ro",
        "notes": "Animale de companie — holding retail (Animax + Maxi Pet), același CUI în surse publice. Tel/email: pagini publice Animax.",
    },
    {
        "company_legal_name": "VABRO RETAIL S.R.L.",
        "company_cui": "16871191",
        "org_display_name": "ZooCenter / Zoomania (retail)",
        "display_name": "Vabro Retail SRL — ZooCenter",
        "judet": "Prahova",
        "oras": "Ploiești",
        "company_judet": "Prahova",
        "company_oras": "Ploiești",
        "company_address": "Str. Afinelor nr. 11 bis (sediu social); sediu central DN72 km8 Aricestii Rahtivani — surse zoocenter.ro",
        "contact_phone": "0733400270",
        "contact_email": "relatiiclienti@zoomania.ro",
        "notes": "Animale de companie — rețea ZooCenter; contact Zoomania.ro în surse publice. Verificare manuală.",
    },
    {
        "company_legal_name": "PETMART ONLINE S.R.L.",
        "company_cui": "32167601",
        "org_display_name": "PetMart.ro",
        "display_name": "Petmart Online SRL — comerț online pet",
        "judet": "Ilfov",
        "oras": "Buftea",
        "company_judet": "Ilfov",
        "company_oras": "Buftea",
        "company_address": "ELI PARK 4, Str. Speranței nr. 10, Buftea (sediu din pagina Date firmă PetMart)",
        "contact_phone": "0372905900",
        "contact_email": "clienti@petmart.ro",
        "notes": "Animale de companie — magazin online + puncte farmacie fizice în București (detalii pe site).",
    },
    {
        "company_legal_name": "PROFIPET COM S.R.L.",
        "company_cui": "7454780",
        "org_display_name": "Profipet — distribuție B2B",
        "display_name": "Profipet Com SRL — import/distribuție pet",
        "judet": "Prahova",
        "oras": "Ploiești",
        "company_judet": "Prahova",
        "company_oras": "Ploiești",
        "company_address": "Str. Afinelor nr. 11 Bis",
        "contact_phone": "0244513868",
        "contact_email": "sales@profipet.ro",
        "notes": "Animale de companie — distribuție en-gros către pet shop / cabinete. Tel/email surse publice Profipet.",
    },
    {
        "company_legal_name": "VETECO INTERSERVICES S.R.L.",
        "company_cui": "12506754",
        "org_display_name": "Veteco — canal veterinar / pet B2B",
        "display_name": "Veteco Interservices SRL",
        "judet": "București",
        "oras": "Sector 1",
        "company_judet": "București",
        "company_oras": "Sector 1",
        "company_address": "Șos. Odăi 439 (surse listă firme / site)",
        "contact_phone": "0213177100",
        "contact_email": "office@veteco.ro",
        "notes": "Animale de companie — en-gros produse veterinare / pet (B2B). Contact: veteco.com policies.",
    },
    {
        "company_legal_name": "UNITED PETFOOD ROMANIA S.R.L.",
        "company_cui": "11304153",
        "org_display_name": "United Petfood — producție / distribuție hrană",
        "display_name": "United Petfood Romania SRL",
        "judet": "București",
        "oras": "Sector 3",
        "company_judet": "București",
        "company_oras": "Sector 3",
        "company_address": "Calea Vitan nr. 240A (surse publice)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — producție/distribuție hrană câini/pisici. Contact: formular unitedpetfood.eu/ro/contact.",
    },
    {
        "company_legal_name": "THOR PETFOOD DISTRIBUTION S.R.L.",
        "company_cui": "33362830",
        "org_display_name": "TopPetShop / Thor Petfood",
        "display_name": "Thor Petfood Distribution SRL",
        "judet": "București",
        "oras": "Sector 2",
        "company_judet": "București",
        "company_oras": "Sector 2",
        "company_address": "Șos. Colentina nr. 16, bl. B1, et. 3, ap. 25",
        "contact_phone": "0756164575",
        "contact_email": "contact@toppetshop.ro",
        "notes": "Animale de companie — import/distribuție + toppetshop.ro. Contact surse publice.",
    },
    {
        "company_legal_name": "zooplus SE (operează în România)",
        "company_cui": "30866743",
        "org_display_name": "zooplus.ro",
        "display_name": "zooplus SE — magazin online RO (TVA RO)",
        "judet": "",
        "oras": "",
        "company_judet": "",
        "company_oras": "",
        "company_address": "Entitate înregistrată în Germania; cod TVA românesc RO30866743 (imprint zooplus.ro). Centru logistic în Polonia.",
        "contact_phone": "0317801264",
        "contact_email": "service@zooplus.ro",
        "notes": "Animale de companie — retailer online cu TVA RO. Sediu social München — nu e SRL românesc; CUI stocat = cifre din cod TVA RO pentru deduplicare în listă.",
    },
    {
        "company_legal_name": "PETPLANET CARE & NUTRITION S.R.L.",
        "company_cui": "41671828",
        "org_display_name": "EuroHrana.ro",
        "display_name": "Petplanet Care & Nutrition SRL — EuroHrana",
        "judet": "București",
        "oras": "Sector 3",
        "company_judet": "București",
        "company_oras": "Sector 3",
        "company_address": "Drumul Balta Arin nr. 6-24, clădirea 2C, biroul 8 (surse publice EuroHrana)",
        "contact_phone": "0741315863",
        "contact_email": "contact@eurohrana.ro",
        "notes": "Animale de companie — magazin online EuroHrana. CUI din surse publice listă firme.",
    },
    # --- extindere: producători / importatori / distribuitori majori (animale de companie) ---
    {
        "company_legal_name": "ROYAL CANIN ROMANIA S.R.L.",
        "company_cui": "23330741",
        "org_display_name": "Royal Canin",
        "display_name": "Royal Canin Romania SRL — distribuție hrană premium",
        "judet": "București",
        "oras": "Sector 1",
        "company_judet": "București",
        "company_oras": "Sector 1",
        "company_address": "Str. Av. Popișteanu nr. 54A, Expo Business Park (surse publice)",
        "contact_phone": "",
        "contact_email": "info.rou@royalcanin.com",
        "notes": "Animale de companie — distribuitor Royal Canin în RO. Email din surse oficiale brand.",
    },
    {
        "company_legal_name": "NESTLE ROMÂNIA S.R.L.",
        "company_cui": "8184502",
        "org_display_name": "Nestlé (inclusiv PetCare / Purina)",
        "display_name": "Nestlé România SRL — FMCG + petcare",
        "judet": "București",
        "oras": "Sector 2",
        "company_judet": "București",
        "company_oras": "Sector 2",
        "company_address": "Str. George Constantinescu nr. 3 (surse publice)",
        "contact_phone": "0212044000",
        "contact_email": "contact@ro.nestle.com",
        "notes": "Animale de companie — grup mare; include linii petcare/Purina. Contact site Nestlé RO.",
    },
    {
        "company_legal_name": "MARS ROMANIA S.R.L.",
        "company_cui": "5427470",
        "org_display_name": "Mars (Pedigree, Whiskas, Nutro etc.)",
        "display_name": "Mars România SRL — FMCG + pet brands",
        "judet": "București",
        "oras": "Sector 1",
        "company_judet": "București",
        "company_oras": "Sector 1",
        "company_address": "Str. Av. Popișteanu nr. 54A, Expo Business Park (surse publice)",
        "contact_phone": "0214077150",
        "contact_email": "mars@mhmr.ro",
        "notes": "Animale de companie — Mars pet brands în RO. Tel/email din comunicate/surse publice.",
    },
    {
        "company_legal_name": "MARAVET S.R.L.",
        "company_cui": "10231304",
        "org_display_name": "Maravet (Covetrus)",
        "display_name": "Maravet SRL — distribuție veterinară / pet B2B",
        "judet": "Maramureș",
        "oras": "Cicârlău",
        "company_judet": "Maramureș",
        "company_oras": "Cicârlău",
        "company_address": "Sat Cicârlău, Str. Vasile Lucaciu nr. 4 (surse listă firme)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — en-gros medicamente veterinare / pet; grup Covetrus. Contact: site maravet.ro.",
    },
    {
        "company_legal_name": "COVETRUS SE EUROPE HOLDING S.R.L.",
        "company_cui": "33831316",
        "org_display_name": "Covetrus (holding RO)",
        "display_name": "Covetrus SE Europe Holding SRL",
        "judet": "București",
        "oras": "Sector 3",
        "company_judet": "București",
        "company_oras": "Sector 3",
        "company_address": "Bd. Corneliu Coposu 6-8, et. 8 (surse publice)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — holding regional Covetrus. Completare contact din site corporate.",
    },
    {
        "company_legal_name": "JOSERA S.R.L.",
        "company_cui": "22821198",
        "org_display_name": "Josera Petfood România",
        "display_name": "Josera SRL — import/distribuție Josera",
        "judet": "Brașov",
        "oras": "Brașov",
        "company_judet": "Brașov",
        "company_oras": "Brașov",
        "company_address": "Str. Școlii 9A (surse listă firme)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — import/distribuție mărci Josera. Contact: josera.ro.",
    },
    {
        "company_legal_name": "PETFOOD TRADE S.R.L.",
        "company_cui": "50122063",
        "org_display_name": "Petfood Trade / MAVSY",
        "display_name": "Petfood Trade SRL",
        "judet": "București",
        "oras": "Sector 1",
        "company_judet": "București",
        "company_oras": "Sector 1",
        "company_address": "București (înregistrare 2024 — verificare adresă în ONRC)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — CAEN retail pet în surse listă firme. Firmă nouă (2024).",
    },
    {
        "company_legal_name": "BARF PET FOOD S.R.L.",
        "company_cui": "39318566",
        "org_display_name": "BARF Pet Food",
        "display_name": "Barf Pet Food SRL",
        "judet": "București",
        "oras": "Sector 2",
        "company_judet": "București",
        "company_oras": "Sector 2",
        "company_address": "București (surse listă firme)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — hrană tip BARF / nișă pet. Verificare contact.",
    },
    {
        "company_legal_name": "REAL PET FOOD S.R.L.",
        "company_cui": "31001332",
        "org_display_name": "Real Pet Food",
        "display_name": "Real Pet Food SRL — Timișoara",
        "judet": "Timiș",
        "oras": "Timișoara",
        "company_judet": "Timiș",
        "company_oras": "Timișoara",
        "company_address": "Timișoara (surse listă firme)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — pet food (surse listă firme).",
    },
    {
        "company_legal_name": "BEST PET FOOD S.R.L.",
        "company_cui": "32819730",
        "org_display_name": "Best Pet Food",
        "display_name": "Best Pet Food SRL",
        "judet": "București",
        "oras": "Sector 4",
        "company_judet": "București",
        "company_oras": "Sector 4",
        "company_address": "București (surse listă firme)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — pet food (surse listă firme).",
    },
    {
        "company_legal_name": "VET EXPERT DISTRIBUTION S.R.L.",
        "company_cui": "17480787",
        "org_display_name": "Vet Expert Distribution",
        "display_name": "Vet Expert Distribution SRL",
        "judet": "București",
        "oras": "Sector 1",
        "company_judet": "București",
        "company_oras": "Sector 1",
        "company_address": "Str. Rucăr nr. 22 (surse listă firme)",
        "contact_phone": "",
        "contact_email": "",
        "notes": "Animale de companie — distribuție produse veterinare / pet (B2B).",
    },
]


class Command(BaseCommand):
    help = "Import / sincronizare prospecte firme-mamă pet (1 rând/CUI + contacte publice)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Scrie în DB (create/update); fără flag, simulare.",
        )

    def handle(self, *args, **options):
        dry = not bool(options.get("apply"))
        created = 0
        updated = 0
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        seen_cui: set[str] = set()

        for row in HOLDINGS:
            cui = _digits_cui(row["company_cui"])
            if not cui or len(cui) < 5:
                self.stdout.write(self.style.ERROR(f"CUI invalid: {row!r}"))
                continue
            if cui in seen_cui:
                self.stdout.write(self.style.WARNING(f"Sărit duplicat în listă: CUI {cui}"))
                continue
            seen_cui.add(cui)

            phone_new = _norm_phone(row.get("contact_phone"))
            email_new = _resolve_email(row, cui)
            has_public_email = not email_new.endswith(PLACEHOLDER_EMAIL_SUFFIX)

            existing = StaffOnboardingLead.objects.filter(company_cui=cui).first()

            if dry:
                act = "UPDATE" if existing else "CREATE"
                self.stdout.write(
                    f"[dry-run] {act} CUI={cui} | {row.get('company_legal_name')} | "
                    f"tel={phone_new or '—'} | email={'(public)' if has_public_email else '(placeholder)'}"
                )
                continue

            note_sync = f"[import_pet_retail {stamp}] contact sync tel={phone_new or '—'} email={email_new if has_public_email else 'placeholder'}"

            if existing:
                upd: list[str] = []
                if phone_new:
                    existing.phone = phone_new
                    upd.append("phone")
                em_old = (existing.email or "").strip()
                if has_public_email and (not em_old or is_placeholder_lead_email(em_old)):
                    existing.email = email_new
                    upd.append("email")
                n = (existing.notes or "").strip()
                existing.notes = (n + "\n" + note_sync if n else note_sync)[:12000]
                upd.append("notes")
                if upd:
                    existing.save(update_fields=upd)
                    updated += 1
                self.stdout.write(self.style.SUCCESS(f"Actualizat CUI={cui} | {row.get('company_legal_name')}"))
                continue

            payload = {
                "email": email_new,
                "phone": phone_new,
                "display_name": (row["display_name"] or "")[:200],
                "org_display_name": (row["org_display_name"] or "")[:255],
                "username_suggested": "",
                "first_name": "",
                "last_name": "",
                "account_kind": StaffOnboardingLead.KIND_COLLAB,
                "collaborator_subtype": StaffOnboardingLead.COLLAB_MAGAZIN,
                "vet_prospect_kind": "",
                "judet": (row.get("judet") or "")[:120],
                "oras": (row.get("oras") or "")[:120],
                "company_legal_name": (row["company_legal_name"] or "")[:255],
                "company_cui": cui[:32],
                "company_cui_has_ro": False,
                "company_reg_com": "",
                "company_address": (row.get("company_address") or "")[:255],
                "company_representative": "",
                "company_judet": (row.get("company_judet") or row.get("judet") or "")[:120],
                "company_oras": (row.get("company_oras") or row.get("oras") or "")[:120],
                "is_public_shelter": False,
                "segments": [],
                "marketing_emails_requested": False,
                "notes": ((row.get("notes") or "") + "\n" + note_sync).strip()[:12000],
                "status": StaffOnboardingLead.ST_READY,
            }
            StaffOnboardingLead.objects.create(created_by=None, **payload)
            created += 1
            self.stdout.write(self.style.SUCCESS(f"Creat CUI={cui} | {row.get('company_legal_name')}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Gata. {'Simulare (dry-run).' if dry else f'Create: {created}, actualizate: {updated}'}"
            )
        )
        if dry:
            self.stdout.write(self.style.NOTICE("Rulează cu --apply pentru a scrie în baza de date."))
