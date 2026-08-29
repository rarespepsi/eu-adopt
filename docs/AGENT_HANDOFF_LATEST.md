---
# Handoff agent — ultima pauză
**Data/ora (RO):** 2026-08-29 ~17:12
**Sursă:** laptop · Remote Control · eu-adopt / main
**User:** 1977 ok — actualizează handoff (SSH mobil + Servacov)

## Ce s-a făcut
- **Mail suport Servacov** (29 aug): trimis pe Hetzner către `adapostrosioriidevede@gmail.com` (user `ScUrbisServconstructSrl`, pk=16) — upload campanie mobil + pași CSRF/cookie + mulțumiri
- **Diagnostic Servacov:** eroarea reală la Salvează campanie = **403 CSRF** (`403_csrf.html`), nu doar galerie; fix upload live `fb374b1` / MyPet `ebb5f55` (28 aug, agent mobil)
- **SSH pe PC laptop:** cheile `hetzner_euadopt` + `id_ed25519_euadopt` adăugate pe H în `/root/.ssh/authorized_keys`; `~\.ssh\config` Host `eu-adopt` / `hetzner` / `178.104.31.52` — agentul de pe telefon (Remote Control) poate termina deploy/SSH dacă laptopul e online

## Fișiere atinse (sesiune 28–29 aug)
- Upload mobil (deja live): `static/js/eu-mobile-photo-upload.js`, `templates/anunturi/account.html`, MyPet, collab oferte, animale pierdute
- CSRF (există, fără fix nou încă): `home/csrf_views.py`, `templates/403_csrf.html`
- PC (în afara repo): `C:\Users\USER\.ssh\config` + authorized_keys pe H

## Git
- Branch: main
- Commit-uri relevante: `ebb5f55` (MyPet upload) · `fb374b1` (campanii/servicii/avatar) · `7e71eef` (radio 30/zi)
- Push: da (cele de mai sus deja pe origin); acest handoff = doar doc local până la commit la cerere

## Deploy Hetzner
- Upload fix-uri: da (28 aug)
- Mail Servacov: da (SMTP pe H, 29 aug)
- Producție: https://eu-adopt.ro · doar Hetzner (`178.104.31.52`)

## SSH — obligatoriu pentru agent mobil / Remote Control
- Laptop trebuie **deschis + Remote Control** (comenzile rulează pe PC, nu pe telefon)
- Merge fără `-i`: `ssh root@178.104.31.52` sau `ssh eu-adopt` sau `ssh hetzner`
- Chei OK pe H: `id_ed25519` (cursor-euadopt-pc), `hetzner_euadopt` (user@Rares), `id_ed25519_euadopt` (eu-adopt-hetzner)
- Config: `C:\Users\USER\.ssh\config` (IdentityFile cele 3, IdentitiesOnly yes)
- Dacă „Permission denied”: verifică Remote Control + `ssh eu-adopt "echo ok"` pe laptop

## Pentru agent laptop / telefon
- `git log -5 --oneline`
- citește `docs/AGENT_HANDOFF_LATEST.md`
- Servacov: Cont → campanie sterilizare; dacă 403 CSRF → Safari/Chrome direct (nu WhatsApp), login, reload, Salvează
- Radio outreach: plafon 30/zi pe H `.env` (commit `7e71eef`)

## Următorul pas
- La cerere user + `1977`+OK: harden CSRF (refresh token la deschidere modal campanie; 403 pe `/cont/` cu buton spre Cont)
- Verificare opțională: cron radio 29 aug cu cap 30
- Nu atinge zone înghețate fără `1977` + OK
---
