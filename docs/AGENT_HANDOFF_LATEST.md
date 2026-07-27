---
# Handoff agent — corecție adopție .com / EU
**Data/ora (RO):** 2026-07-27 10:15
**Sursă:** desktop · eu-adopt / main
**User:** 1977 ok — corecție flux adopție EU + commit/push/deploy

## Ce s-a făcut
- Demo animals: **fără buton „Vreau să adopt”** (ascuns complet).
- Detecție DEMO întărită: owner din listă + keyword-uri (`demo`, `[seed]`, `seed_` by default).
- `.com`/EU: la trimitere adopție **nu mai apare traseul Servicii/bonus/transport**; mesaj simplu de confirmare.
- `.com`/EU: nu mai setează sesiune bonus servicii la cererea de adopție.
- Salvare în acest fișier de handoff (cerut de user).

## Fișiere atinse
- `home/demo_listings.py`
- `home/views.py`
- `templates/anunturi/pets-single.html`
- `home/eu_ui_labels.py`
- `home/tests/test_demo_animal_adoption.py`
- `docs/AGENT_HANDOFF_LATEST.md`

## Git
- Branch: `main`
- Commit: *(după commit-ul acestei corecții)*
- Push: *(după push-ul acestui commit)*

## Deploy Hetzner
- Da (după push): `.\scripts\deploy_hetzner_from_pc.ps1`

## Verificare rapidă
- `.com` demo pet: fără buton adopție.
- `.com` pet real: „Vreau să adopt” trimite cerere scurtă și **nu** mai redirecționează spre Servicii.
- `.ro`: fluxul existent rămâne neschimbat.

## Următorul pas
- Dacă user mai cere: curățare suplimentară texte RO rămase pe `.com` în fluxuri secundare.
---
