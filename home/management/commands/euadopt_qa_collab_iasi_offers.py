"""
Setează județ/oraș Iași pe profilele colaboratorilor dm și dg1 și creează
câte 2 oferte active (magazin pentru dm, servicii pentru dg1) cu câmpurile
cerute de fluxul real (imagine, preț, discount, stoc, valabilitate, specii).

Șterge ofertele vechi cu același prefix [QA-Iasi] pentru acești useri, apoi recreează.

Rulare:
  python manage.py euadopt_qa_collab_iasi_offers
"""
from __future__ import annotations

import base64
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from home.models import CollaboratorServiceOffer, UserProfile

TITLE_PREFIX = "[QA-Iasi]"
# Aliniat la dropdown-uri site (ex. ro_county_select.html)
COUNTY = "Iași"
CITY = "Iași"


def _tiny_jpeg_upload(filename: str) -> SimpleUploadedFile:
    raw = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
    )
    return SimpleUploadedFile(filename, raw, content_type="image/jpeg")


def _set_profile_iasi(user) -> None:
    prof, _ = UserProfile.objects.get_or_create(user=user)
    prof.judet = COUNTY
    prof.oras = CITY
    prof.company_judet = COUNTY
    prof.company_oras = CITY
    prof.save(update_fields=["judet", "oras", "company_judet", "company_oras", "updated_at"])


def _clear_qa_offers(collaborator) -> int:
    n, _ = CollaboratorServiceOffer.objects.filter(
        collaborator=collaborator,
        title__startswith=TITLE_PREFIX,
    ).delete()
    return n


class Command(BaseCommand):
    help = "Profile dm+dg1 -> Iasi; 2 oferte magazin (dm) + 2 servicii (dg1) [QA-Iasi]."

    def handle(self, *args, **options):
        User = get_user_model()
        today = timezone.localdate()
        v_from = today - timedelta(days=1)
        v_until = today + timedelta(days=120)
        base_url = (getattr(settings, "SITE_BASE_URL", "") or "https://www.eu-adopt.ro").rstrip("/")

        u_dm = User.objects.filter(username__iexact="dm").first()
        u_dg1 = User.objects.filter(username__iexact="dg1").first()
        if not u_dm or not u_dg1:
            self.stderr.write("Missing user dm or dg1 in database.")
            return

        _set_profile_iasi(u_dm)
        _set_profile_iasi(u_dg1)
        self.stdout.write(f"Profile dm + dg1: county+city set (Iasi judet / localitate in DB).")

        nd = _clear_qa_offers(u_dm)
        ng = _clear_qa_offers(u_dg1)
        if nd or ng:
            self.stdout.write(f"Sters oferte vechi [QA-Iasi]: dm={nd}, dg1={ng}")

        M = CollaboratorServiceOffer
        img = _tiny_jpeg_upload

        # --- dm: magazin (2 produse, fisa completa) ---
        CollaboratorServiceOffer.objects.create(
            collaborator=u_dm,
            partner_kind=M.PARTNER_KIND_MAGAZIN,
            title=f"{TITLE_PREFIX} Hrana uscata caini 2kg",
            description="Produs demo magazin Iasi — complet: pret, discount, stoc, link, filtre caine.",
            external_url=f"{base_url}/",
            price_hint="89 lei",
            discount_percent=15,
            quantity_available=30,
            valid_from=v_from,
            valid_until=v_until,
            image=img("qa_iasi_dm_1.jpg"),
            species_dog=True,
            species_cat=False,
            species_other=False,
            target_species=M.TARGET_SPECIES_DOG,
            target_size=M.TARGET_SIZE_MEDIUM,
            target_sex=M.TARGET_SEX_ALL,
            target_age_band=M.TARGET_AGE_ADULT,
            target_sterilized=M.TARGET_STERIL_ALL,
            is_active=True,
        )
        CollaboratorServiceOffer.objects.create(
            collaborator=u_dm,
            partner_kind=M.PARTNER_KIND_MAGAZIN,
            title=f"{TITLE_PREFIX} Jucarie pisica interactiva",
            description="Al doilea produs demo magazin Iasi — tinta pisica.",
            external_url="https://example.com/produs-jucarie-pisica",
            price_hint="45 lei",
            discount_percent=20,
            quantity_available=50,
            valid_from=v_from,
            valid_until=v_until,
            image=img("qa_iasi_dm_2.jpg"),
            species_dog=False,
            species_cat=True,
            species_other=False,
            target_species=M.TARGET_SPECIES_CAT,
            target_size=M.TARGET_SIZE_SMALL,
            target_sex=M.TARGET_SEX_ALL,
            target_age_band=M.TARGET_AGE_ALL,
            target_sterilized=M.TARGET_STERIL_ALL,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("Creat 2 oferte magazin (dm)."))

        # --- dg1: servicii / grooming (2 oferte) ---
        CollaboratorServiceOffer.objects.create(
            collaborator=u_dg1,
            partner_kind=M.PARTNER_KIND_SERVICII,
            title=f"{TITLE_PREFIX} Tuns + spalat talie mica",
            description="Servicii grooming Iasi — demo complet: titlu, imagine, pret, discount, locuri, valabilitate.",
            external_url="",
            price_hint="120 lei",
            discount_percent=12,
            quantity_available=20,
            valid_from=v_from,
            valid_until=v_until,
            image=img("qa_iasi_dg1_1.jpg"),
            species_dog=True,
            species_cat=True,
            species_other=False,
            target_species=M.TARGET_SPECIES_ALL,
            target_size=M.TARGET_SIZE_ALL,
            target_sex=M.TARGET_SEX_ALL,
            target_age_band=M.TARGET_AGE_ALL,
            target_sterilized=M.TARGET_STERIL_ALL,
            is_active=True,
        )
        CollaboratorServiceOffer.objects.create(
            collaborator=u_dg1,
            partner_kind=M.PARTNER_KIND_SERVICII,
            title=f"{TITLE_PREFIX} Spa complet talie medie",
            description="Al doilea serviciu grooming Iasi — programare la telefon.",
            external_url="",
            price_hint="180 lei",
            discount_percent=18,
            quantity_available=15,
            valid_from=v_from,
            valid_until=v_until,
            image=img("qa_iasi_dg1_2.jpg"),
            species_dog=True,
            species_cat=False,
            species_other=False,
            target_species=M.TARGET_SPECIES_ALL,
            target_size=M.TARGET_SIZE_ALL,
            target_sex=M.TARGET_SEX_ALL,
            target_age_band=M.TARGET_AGE_ALL,
            target_sterilized=M.TARGET_STERIL_ALL,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("Creat 2 oferte servicii (dg1)."))
        self.stdout.write("Gata.")
