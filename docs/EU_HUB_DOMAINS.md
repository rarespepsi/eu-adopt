# Hub EU — un singur site pe .com (aug 2026)

**Portfolio Hostico:** `eu-adopt.ro/com/eu` + `euadopt.com/de/es/eu/fr/org`.

## Mapare

| Domeniu | Rol |
|---------|-----|
| **eu-adopt.ro** (+ www) | România — site complet (fără redirect) |
| **euadopt.com** (+ www) | **Hub EU unic** — EN + selector limbi |
| **euadopt.de / .fr / .es** (+ www) | **301 →** `.com` + `?eu_lang=` (DE/FR/ES) |
| **euadopt.eu / .org**, **eu-adopt.com / .eu** (+ www) | **301 →** `euadopt.com` |

## DNS

A/AAAA către Hetzner pentru **toate** hosturile (inclusiv cele care doar redirecționează).

## Nginx

- `deploy/hetzner/nginx-euadopt-all-domains.conf` — proxy toate hosturile; Django face 301
- HTTPS: certbot pe fiecare host sau SAN; redirect HTTPS separat pe server

## Cod

- Registru: `home/euadopt_domains.py`
- Middleware: `euadopt_final/eu_site_middleware.py`
- Teste: `python manage.py test home.tests.test_eu_site`
