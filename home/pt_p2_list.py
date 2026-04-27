"""
Lista P2 pentru pagina PT (/pets/): aceeași logică pentru render inițial și /pets/p2-more/.
"""
PT_P2_PAGE_SIZE = 24
from itertools import cycle

from .data import DEMO_DOGS, DEMO_DOG_IMAGE
from .models import AnimalListing
from .pet_age_bands import AGE_LABELS_ORDERED, BAND_CHOICES_UI, BAND_FILTER_GET_VALUES, build_age_band_filter_q


def _adoption_state_label(state: str) -> str:
    mapping = {
        AnimalListing.ADOPTION_STATE_FREE: "Liber",
        AnimalListing.ADOPTION_STATE_OPEN: "Spre adopție",
        AnimalListing.ADOPTION_STATE_IN_PROGRESS: "În curs de adopție",
        AnimalListing.ADOPTION_STATE_ADOPTED: "Adoptat",
    }
    return mapping.get((state or "").strip(), "Liber")


def _pt_p2_annotate_ask_plic(p2_list, request):
    """Card PT: plic lângă inimă — doar dacă userul ar putea trimite mesaj din fișă către owner."""
    for row in p2_list:
        row["show_pt_ask_plic"] = False
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return
    ap = getattr(user, "account_profile", None)
    viewer_can_adopt = bool(ap.can_adopt_animals) if ap else True
    if not viewer_can_adopt:
        return
    uid = int(user.pk)
    for row in p2_list:
        oid = row.get("owner_id")
        if oid is None:
            continue
        try:
            if int(oid) == uid:
                continue
        except (TypeError, ValueError):
            continue
        st = (row.get("adoption_state") or "").strip()
        if st == AnimalListing.ADOPTION_STATE_ADOPTED:
            continue
        row["show_pt_ask_plic"] = True


def pt_pets_page_context(request):
    """
    Construiește p2_list + câmpurile de filtru pentru șablonul PT.
    Returnează dict cu cheia p2_list (listă dict-uri pet) și restul pentru template.
    """
    selected_judet = (request.GET.get("judet") or "").strip()
    selected_marime = (request.GET.get("marime") or "").strip()
    selected_varsta = (request.GET.get("varsta") or "").strip()
    selected_varsta_band = (request.GET.get("varsta_band") or "").strip().lower()
    if selected_varsta_band not in BAND_FILTER_GET_VALUES:
        selected_varsta_band = ""
    selected_sex = (request.GET.get("sex") or "").strip()
    selected_species = (request.GET.get("species") or "").strip().lower()
    if selected_species not in {"dog", "cat", "other"}:
        selected_species = ""

    selected_traits = request.GET.getlist("traits")
    if len(selected_traits) == 1 and "," in selected_traits[0]:
        selected_traits = [t.strip() for t in selected_traits[0].split(",") if t.strip()]
    allowed_traits = {
        "trait_jucaus",
        "trait_iubitor",
        "trait_protector",
        "trait_energic",
        "trait_linistit",
        "trait_bun_copii",
        "trait_bun_caini",
        "trait_bun_pisici",
        "trait_obisnuit_casa",
        "trait_obisnuit_lesa",
        "trait_nu_latla",
        "trait_apartament",
        "trait_se_adapteaza",
        "trait_tolereaza_singur",
        "trait_necesita_experienta",
    }
    selected_traits = [t for t in selected_traits if t in allowed_traits]

    filter_active = any(
        [
            selected_judet,
            selected_marime,
            selected_varsta,
            selected_varsta_band,
            selected_sex,
            selected_species,
        ]
    ) or bool(selected_traits)

    judet_choices = [
        "Alba",
        "Arad",
        "Argeș",
        "Bacău",
        "Bihor",
        "Bistrița-Năsăud",
        "Botoșani",
        "Brăila",
        "Brașov",
        "București",
        "Buzău",
        "Călărași",
        "Caraș-Severin",
        "Cluj",
        "Constanța",
        "Covasna",
        "Dâmbovița",
        "Dolj",
        "Galați",
        "Giurgiu",
        "Gorj",
        "Harghita",
        "Hunedoara",
        "Ialomița",
        "Iași",
        "Ilfov",
        "Maramureș",
        "Mehedinți",
        "Mureș",
        "Neamț",
        "Olt",
        "Prahova",
        "Sălaj",
        "Satu Mare",
        "Sibiu",
        "Suceava",
        "Teleorman",
        "Timiș",
        "Tulcea",
        "Vâlcea",
        "Vaslui",
        "Vrancea",
    ]
    marime_choices = ["mica", "medie", "mare"]
    varsta_choices = list(AGE_LABELS_ORDERED)
    sex_choices = ["m", "f"]

    qs_base = AnimalListing.objects.filter(is_published=True)

    p2_list = []
    if not filter_active:
        db_pets = list(qs_base.order_by("-created_at")[:200])
        if db_pets:
            for listing in db_pets:
                p2_list.append(
                    {
                        "pk": listing.pk,
                        "nume": listing.name or "—",
                        "imagine": listing.photo_1,
                        "imagine_2": listing.photo_2,
                        "imagine_3": listing.photo_3,
                        "imagine_fallback": DEMO_DOG_IMAGE,
                        "adoption_state": listing.adoption_state,
                        "adoption_state_label": _adoption_state_label(listing.adoption_state),
                        "owner_id": listing.owner_id,
                        "traits": [],
                    }
                )
        else:
            for d in DEMO_DOGS:
                p2_list.append(
                    {
                        "pk": d["id"],
                        "nume": d["nume"],
                        "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
                        "traits": (d.get("traits") or [])[:2],
                    }
                )

        n = len(p2_list)
        need = (4 - n % 4) % 4
        if need and p2_list:
            for i, d in enumerate(cycle(DEMO_DOGS)):
                if i >= need:
                    break
                p2_list.append(
                    {
                        "pk": d["id"],
                        "nume": d["nume"],
                        "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
                        "traits": (d.get("traits") or [])[:2],
                    }
                )

        if p2_list and len(p2_list) <= 12:
            extra = 24
            for i, d in enumerate(cycle(DEMO_DOGS)):
                if i >= extra:
                    break
                p2_list.append(
                    {
                        "pk": d["id"],
                        "nume": d["nume"],
                        "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
                        "traits": (d.get("traits") or [])[:2],
                    }
                )
    else:
        qs = qs_base
        if selected_judet:
            qs = qs.filter(county__iexact=selected_judet)
        if selected_marime:
            qs = qs.filter(size__iexact=selected_marime)
        band_q = build_age_band_filter_q(selected_varsta_band, selected_species, selected_marime)
        if band_q is not None:
            qs = qs.filter(band_q)
        if selected_varsta:
            qs = qs.filter(age_label__iexact=selected_varsta)
        if selected_sex:
            qs = qs.filter(sex__iexact=selected_sex)
        if selected_species:
            qs = qs.filter(species__iexact=selected_species)

        db_candidates = list(qs.order_by("-created_at")[:200])
        if db_candidates:
            if selected_traits:
                scored = []
                for listing in db_candidates:
                    match_count = 0
                    for tr in selected_traits:
                        if getattr(listing, tr, False):
                            match_count += 1
                    scored.append((listing, match_count))

                scored.sort(key=lambda x: (x[1], x[0].created_at), reverse=True)
                positive = [obj for obj, cnt in scored if cnt > 0]
                ordered = positive if positive else [obj for obj, _ in scored]
            else:
                ordered = db_candidates

            for listing in ordered:
                p2_list.append(
                    {
                        "pk": listing.pk,
                        "nume": listing.name or "—",
                        "imagine": listing.photo_1,
                        "imagine_2": listing.photo_2,
                        "imagine_3": listing.photo_3,
                        "imagine_fallback": DEMO_DOG_IMAGE,
                        "adoption_state": listing.adoption_state,
                        "adoption_state_label": _adoption_state_label(listing.adoption_state),
                        "owner_id": listing.owner_id,
                        "traits": [],
                    }
                )

        n = len(p2_list)
        need = (4 - n % 4) % 4
        if need and p2_list:
            snapshot = list(p2_list)
            for i, d in enumerate(cycle(snapshot)):
                if i >= need:
                    break
                p2_list.append(d)

        if p2_list and len(p2_list) < 24:
            snapshot = list(p2_list)
            for d in cycle(snapshot):
                if len(p2_list) >= 24:
                    break
                p2_list.append(d)

    _pt_p2_annotate_ask_plic(p2_list, request)

    return {
        "p2_list": p2_list,
        "selected_judet": selected_judet,
        "selected_marime": selected_marime,
        "selected_varsta": selected_varsta,
        "selected_varsta_band": selected_varsta_band,
        "selected_sex": selected_sex,
        "selected_species": selected_species,
        "judet_choices": judet_choices,
        "marime_choices": marime_choices,
        "varsta_choices": varsta_choices,
        "varsta_band_choices": BAND_CHOICES_UI,
        "sex_choices": sex_choices,
    }
