---
# Handoff agent — ultima pauză / salvare
**Data/ora (RO):** 2026-07-20 01:10
**Sursă:** Cursor · eu-adopt / main
**User:** `1977 ok` — commit + salvare Desktop; filtru adăposturi confirmat „foarte frumos”

## Ce s-a făcut
- Director `/adaposturi/`: filtru **Județ** (stânga), titlu + lead centrate
- Persistare filtru în URL `?judet=…` + clipire select
- Card → detaliu cu `?from_judet=` → buton **← Înapoi** (înapoi la lista filtrată)
- Pe lista filtrată: **← Toate adăposturile** resetează filtrul
- TEMP: ~30 casete demo layout (de scos la lansare / la cerere)
- Detaliu adăpost desktop: promo stivuite jos, casetă sus, fundal Intra

## Fișiere atinse
- `templates/anunturi/adaposturi_directory.html` — filtru, demo, Înapoi/Toate
- `templates/anunturi/adapost_detail.html` — label Înapoi / Toate + layout coloană
- `home/shelter_views.py` — demo rows, `from_judet`, back URL/label
- `home/shelter_directory.py` — `org_county`
- `home/ro_location.py` — `all_counties()`
- `home/tests/test_shelter_directory.py`

## Git
- Branch: main
- Commit(uri) relevante: `c61d23a` (Înapoi/Toate) · `25f804e` (URL+clipire) · `cb072ea` (demo+stânga) · …
- Push: da

## Deploy Hetzner
- da · SHA live **`c61d23a`**

## Salvare Desktop
- `%USERPROFILE%\Desktop\EU-Adopt-backups\good-releases\` — ZIP rotație 3 (inclusiv `good_*_c61d23a.zip`)

## Pentru agent laptop
- `git log -5 --oneline`
- citește `docs/AGENT_HANDOFF_LATEST.md`
- Test: https://eu-adopt.ro/adaposturi/ — filtru → adăpost → Înapoi → Toate adăposturile
- Scoate DEMO 30 casete când user cere

## Următorul pas
- La cerere: scoate casetele demo
- Orice edit site = `1977` + OK
---
