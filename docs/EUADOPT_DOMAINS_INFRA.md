# EU-Adopt — domenii (arhitectură stabilită iul 2026)

## Ierarhie

| Host | Rol |
|------|-----|
| **eu-adopt.ro** (+ www) | Site principal RO — public |
| **euadopt.com** (+ www) | Hub EU — EN + **toate limbile UE** (selector) |
| **euadopt.de / .fr / .es** (+ www) | Același catalog; limba DE/FR/ES (schimbare manuală posibilă) |
| **euadopt.eu**, **euadopt.org**, **eu-adopt.com**, **eu-adopt.eu** (+ www) | **301** → `euadopt.com` / `www.euadopt.com` |

O singură aplicație Django, o DB, un admin. Animalele = din RO.

## Flag-uri env (Hetzner)

| Env | Rol |
|-----|-----|
| `EUADOPT_EU_PRODUCT_SKIN=1` | Activează limbi + meniu EU pe hosturi non-.ro |
| `EUADOPT_NON_RO_STAFF_ONLY=1` | Public = Coming soon pe `.com`/`.de`/`.fr`/`.es`; doar staff/superuser |

La lansare publică EU: `EUADOPT_NON_RO_STAFF_ONLY=0`.

## SEO

- **canonical** → `https://eu-adopt.ro{path}` (anti-duplicate)
- **hreflang**: ro / en / de / fr / es + x-default → `.com`

## Cod

- Registru: `home/euadopt_domains.py`
- Limbă / SEO helpers: `home/eu_site.py`
- Middleware redirect: `euadopt_final/eu_site_middleware.py`
- Gate staff: `euadopt_final/eu_non_ro_staff_gate_middleware.py`
