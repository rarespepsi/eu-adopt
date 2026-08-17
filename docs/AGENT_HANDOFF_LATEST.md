---
# Handoff agent — ultima salvare
**Data/ora (RO):** 2026-08-17 18:48
**Sursă:** laptop · eu-adopt / main
**User:** ZIP + git pentru Facebook Page tokens

## Ce s-a făcut
- Token Facebook System User (`Euadoptserver`) în `.env` local + Hetzner (aceleași 6 chei; **nu e în git**)
- Cod: System User → Page token via `GET /me/accounts` (New Page Experience, eroare 190/2069032)
- Live: commit **83e78a5** pe Hetzner; smoke OK
- Citire postări RO: OK. Cron oglindire RO → DE/FR/ES/COM pornit (user: lasă catch-up)
- Unele oglindiri OK; altele eșuate `(#200) publish_actions deprecated` (POST `/feed`+link)
- Idee viitor (nu implementată): user leagă pagina FB (OAuth Meta, cheie automată) → postări site și pe pagina lui

## Fișiere atinse (în git)
- `home/facebook_markets.py` — resolve Page token + cache
- `home/facebook_page_post.py` — comentariu
- `home/tests/test_facebook_page_post.py` — teste resolve + izolare env

## Git
- Branch: main
- Commit Facebook: **83e78a5**
- Push: da
- Deploy H: da (17 aug 2026)

## Deploy Hetzner
- da · `.\scripts\deploy_hetzner_from_pc.ps1`
- SHA live: **83e78a5**
- Flag: `/var/lib/euadopt/EXPECTED_RELEASE.txt`

## Pentru agent laptop
- `git log -3 --oneline`
- citește acest handoff
- `.env` nu se comite; tokenurile Facebook rămân doar în `.env` local + `/opt/eu-adopt/.env`

## Următorul pas
- Oglindirea continuă (user a zis să meargă)
- Legare pagină FB per user = idee viitor, fără cod
---
