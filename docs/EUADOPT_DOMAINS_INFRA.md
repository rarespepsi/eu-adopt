# EU-Adopt — domenii (strategie B — aug 2026)

## Ierarhie

| Host | Rol |
|------|-----|
| **eu-adopt.ro** (+ www) | Site principal RO — public, neschimbat |
| **euadopt.com** (+ www) | Hub EU — EN + selector limbi |
| **euadopt.de / .fr / .es** (+ www) | **Active** — URL rămâne pe TLD; limba DE/FR/ES |
| **euadopt.eu**, **euadopt.org**, **eu-adopt.com**, **eu-adopt.eu** (+ www) | **301 →** `euadopt.com` |

O singură aplicație Django, o DB, un admin. Animalele = din RO.

## Flag-uri env (Hetzner)

| Env | Rol |
|-----|-----|
| `EUADOPT_EU_PRODUCT_SKIN=1` | Activează limbi + meniu EU pe `.com` / `.de` / `.fr` / `.es` |
| `EUADOPT_NON_RO_STAFF_ONLY=1` | Public = Coming soon pe EU; doar staff/superuser |

## SEO

- **canonical** → `https://eu-adopt.ro{path}`
- **hreflang**: ro / en / de / fr / es + x-default → `.com`

## Cod

- Registru: `home/euadopt_domains.py`
- Limbă / SEO: `home/eu_site.py`
- Middleware: `euadopt_final/eu_site_middleware.py`
- Coming soon i18n: `home/eu_coming_soon.py`
