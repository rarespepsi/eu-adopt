# EU UI i18n — tipar (EN master → alte limbi)

**Scop:** UI pe domenii EU (`.com` / `.de` / `.fr` / `.es`) fără texte RO hardcodate. Conținutul din DB (descrieri animale) rămâne limba autorului.

## Tipar

1. **Cheie** în `home/eu_ui_labels.py` (`_EN["key"] = "English…"`).
2. **Template:** `{% if eu_site_active %}{{ eu_ui.key }}{% else %}Text RO{% endif %}`.
3. **Logică Python** (flash, burtieră, stări): `is_eu_site_host(request.get_host())` sau `request.eu_site_active` / `get_language().startswith("en")`.
4. **Navbar:** deja `home/eu_nav_labels.py` (24 limbi) — același model pentru body UI când adaugi DE/FR/ES.
5. **Trăsături:** `home/pet_traits.py` — EN când limba activă e `en`.

## Fișiere tipice atinse

| Zonă | Fișiere |
|------|---------|
| Pack EN | `home/eu_ui_labels.py` |
| Context | `home/eu_site.py` → `eu_ui`, `eu_force_english` |
| HOME | `home_v2.html`, `views._get_home_burtiera_text`, `data.A2_QUOTE_POOL_EN` |
| PT | `pt.html`, `pt_p2_card.html`, JS label-uri din `data-pt-lbl-*` |
| Transport | `transport.html` + mesaje submit în `views.py` |
| Fișă animal | `pets-single.html` |
| Cont / chrome | `account.html`, `site_guide_widget.html`, `base.html` PWA, `login_required_modal.html` |
| 404 / Contact / Termeni hub | `404.html`, `contact.html`, `termeni.html` |

## Următorul pas multi-limbă

- Copiază `_EN` → `_DE` / `_FR` / `_ES` (sau `eu_ui_pack(lang)`).
- `eu_site_context_for_request` alege pack după `eu_site_lang`.
- Pe `.com` reactivezi selectorul când pack-ul limbii e complet (`eu_force_english` doar până atunci).
- Traducere asistată: LibreTranslate self-hosted pe Hetzner (fără abonament) pentru generat pack-uri, nu ca MT live pe fiecare request.

## Nu traduce aici

- Descrieri / note din `AnimalListing` (DB) — UI chrome da; conținut la cerere / câmp separat.
- Documente legale full — hub EN + notă; text legal RO rămâne obligatoriu până la versiune EN oficială.
