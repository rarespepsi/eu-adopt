---
# Handoff agent — savepoint EU produs
**Data/ora (RO):** 2026-07-23 ~14:25
**Sursă:** laptop · eu-adopt / main
**User:** 1977 ok — memorează + salvează, apoi implementare pași EU

## Ce s-a făcut (înainte de pașii de produs)

- Decizii produs EU memorate: `docs/EUADOPT_EU_PRODUCT_DECISIONS.md` + `.cursor/rules/EU_SITE_PRODUCT_MEMORAT.mdc`
- Steag PNG (nu emoji/inițiale): commit **`ed19a1b`** (deja pe main + live)
- Savepoint: commit memorare (acest handoff) **înainte** de meniu EU / Reclama RO-EU

## Fișiere atinse (memorare)

- `docs/EUADOPT_EU_PRODUCT_DECISIONS.md`
- `.cursor/rules/EU_SITE_PRODUCT_MEMORAT.mdc`
- `docs/AGENT_HANDOFF_LATEST.md`
- `docs/EUADOPT_DOMAINS_INFRA.md` (link la decizii)

## Git

- Branch: main
- Savepoint produs: SHA după commit `docs: memorize EU product decisions…`
- Rollback cod pre-meniu: **`ed19a1b`** (flags) sau savepoint docs

## Deploy Hetzner

- Flaguri live deja: `ed19a1b`
- După Pas 1 meniu: deploy separat

## Pentru agent laptop

- Citește `docs/EUADOPT_EU_PRODUCT_DECISIONS.md`
- Ordine: (1) meniu +Transport −Adăpost (2) Reclama RO/EU (3) click+limbă text (4) i18n UI (5) sloturi (6) scoate coming soon după .ro full
- `.ro` = nu atinge layout fără nevoie; blocat

## Următorul pas

- Pas 1: navbar EU — Transport vizibil, Adăpost/ONG ascuns (+ block URL shelter pe EU)
---
