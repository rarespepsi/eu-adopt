---
# Handoff agent — ultima pauză
**Data/ora (RO):** 2026-08-25 ~16:00
**Sursă:** laptop · eu-adopt / main
**User:** salvează pe desk, commit, push

## Ce s-a făcut (sesiune 24–25 aug)
- **Animale pierdute/găsite:** hartă, bibliotecă pe județ, Adaugă, Ale mele, filtre — live
- **Semnalează abuz (A5.2):** hartă full-page; formular pe județ (DSVSA / BPA / Ambele); contacte DSVSA + IPJ; OG27/GDPR/112; mail formal Reply-To user; max **3 sesizări/zi**; nume/email/telefon din cont (readonly); adresă stradă obligatorie în formular
- **SOS pe HOME:** lăsat neschimbat (fără animație)
- **Val invitații automate:** verificat Hetzner — azi **100/100 sent** OK (4×25 la 9/11/13/15 RO)

## Fișiere cheie abuz
- `home/abuz_contacts.py`, `home/abuz_mail.py`
- `templates/anunturi/semnaleaza_abuz.html`
- migrări `0088_abuse_report`, `0089_abuse_report_fields`
- prelaunch public: `/semnaleaza-abuz/`

## Git
- Branch: main
- Ultimele commit-uri abuz: `913f7e7` → `5cc4949` → `4102c68` (+ handoff/backup după)
- Push: da (la zi cu origin după acest pas)

## Deploy Hetzner
- da — live SHA așteptat ~`4102c68` (sau HEAD după commit handoff)
- Producție: https://eu-adopt.ro · doar Hetzner

## Pentru agent laptop
- `git log -5 --oneline`
- citește `docs/AGENT_HANDOFF_LATEST.md`
- test: https://eu-adopt.ro/semnaleaza-abuz/ · https://eu-adopt.ro/animale-pierdute/
- val invite: log `/var/log/euadopt-invite-wave.log` (max 100/zi)

## Următorul pas
- User testează formularul abuz pe live
- Continuă valul invite (cron deja OK)
- SOS animație pe A5.2: **nu** (user a zis lasă)
---
