# EU UI i18n — tipar (EN master → limbi hub + TLD)

**Scop:** UI pe domenii EU (`.com` / `.de` / `.fr` / `.es`) fără texte RO hardcodate. Conținutul din DB (descrieri animale) rămâne limba autorului; pe EU se poate traduce la afișare (UGC/Gemini).

## Tipar

1. **Cheie** în `home/eu_ui_labels.py` (`_EN["key"] = "English…"`).
2. **Traduceri variantă B** în `home/eu_ui_labels_i18n.json` (de/fr/es/it/pl/nl/pt/ro) — generare: `scripts/_gen_eu_ui_i18n.py`.
3. **Template:** `{% if eu_site_active %}{{ eu_ui.key }}{% else %}Text RO{% endif %}`.
4. **Logică Python:** `eu_ui_label(key, lang=...)` / `eu_or_ro(...)`.
5. **Proceduri produs:** `home/eu_procedures.py` → `site_proc` — vezi `docs/EU_RO_PROCEDURES.md`.
6. **Navbar:** `home/eu_nav_labels.py` (24 limbi).
7. **Hub `.com`:** selector cu 9 limbi (`EU_HUB_UI_LANGUAGE_CHOICES`); `.de/.fr/.es` forțează limba TLD + selector full.

## Fișiere tipice

| Zonă | Fișiere |
|------|---------|
| Pack EN + loader | `home/eu_ui_labels.py`, `home/eu_ui_labels_i18n.json` |
| Context | `home/eu_site.py` → `eu_ui`, `eu_site_languages` |
| Locale middleware | `euadopt_final/eu_site_middleware.py` |

## Regenerare pack-uri

```powershell
python scripts/_gen_eu_ui_i18n.py
```

Necesită `EUADOPT_GEMINI_API_KEY` în `.env`. Resume-safe (completează cheile lipsă).

## Nu traduce aici

- Descrieri / note din `AnimalListing` (DB) — UGC la afișare.
- Documente legale full — hub + notă; text legal RO rămâne obligatoriu până la versiune oficială.
