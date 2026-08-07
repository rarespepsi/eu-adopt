# EU-Adopt — domenii (strategie UX aug 2026)

## Ierarhie

| Host | Rol |
|------|-----|
| **eu-adopt.ro** (+ www) | Site principal RO — public, neschimbat |
| **euadopt.com** (+ www) | **Singurul hub EU** — EN + selector limbi |
| **euadopt.de / .fr / .es** (+ www) | **301 →** `.com` + `?eu_lang=de\|fr\|es` (limba din TLD) |
| **euadopt.eu**, **euadopt.org**, **eu-adopt.com**, **eu-adopt.eu** (+ www) | **301 →** `euadopt.com` |

O singură aplicație Django, o DB, un admin. Animalele = din RO.

## Flag-uri env (Hetzner)

| Env | Rol |
|-----|-----|
| `EUADOPT_EU_PRODUCT_SKIN=1` | Activează limbi + meniu EU pe `.com` |
| `EUADOPT_NON_RO_STAFF_ONLY=1` | Public = Coming soon pe `.com`; doar staff/superuser |

La lansare publică EU: `EUADOPT_NON_RO_STAFF_ONLY=0`.

## SEO

- **canonical** → `https://eu-adopt.ro{path}` (anti-duplicate)
- **hreflang**: `ro` → `.ro`, `en` + `x-default` → `.com`

## Cod

- Registru: `home/euadopt_domains.py`
- Limbă / SEO helpers: `home/eu_site.py`
- Middleware redirect: `euadopt_final/eu_site_middleware.py`
- Gate staff: `euadopt_final/eu_non_ro_staff_gate_middleware.py`

## Decizii produs (meniu, publi, limbi)

→ **`docs/EUADOPT_EU_PRODUCT_DECISIONS.md`** · regulă Cursor `EU_SITE_PRODUCT_MEMORAT.mdc`
