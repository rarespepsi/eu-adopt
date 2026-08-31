---
# Handoff agent — ultima pauză
**Data/ora (RO):** 2026-08-31 ~09:20
**Sursă:** laptop · eu-adopt / main
**User:** 1977 fix permanent CSRF campanie Servacov

## Ce s-a făcut
- **Fix CSRF campanie sterilizare (mobil):** `@ensure_csrf_cookie` pe `account_view`; endpoint `GET /cont/csrf-refresh/`; pe touch submit campanie via `fetch`+FormData cu token proaspăt; refresh la deschidere modal / revenire din galerie
- **Servacov:** încă 0 campanii; erori CSRF 31 aug dimineață (iPhone) — așteptare retest după deploy
- **Manual:** user va primi detalii campanie de la Servacov pentru publicare staff

## Fișiere atinse
- `home/views.py` — `account_view`, `account_csrf_refresh_view`
- `home/urls.py` — `cont/csrf-refresh/`
- `templates/anunturi/account.html` — JS CSRF campanie mobil
- `home/tests/test_csrf_failure.py` — teste account CSRF

## Git / Deploy
- Commit + push main → deploy H obligatoriu

## Următorul pas
- Servacov retestează pe iPhone (Safari/Chrome) Cont → campanie + link
- Dacă OK: confirmare; altfel loguri + campanie manuală cu detaliile primite
---
