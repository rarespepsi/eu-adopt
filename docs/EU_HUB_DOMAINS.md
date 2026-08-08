# Hub EU — strategie B (domenii țară active)

**Portfolio Hostico:** `eu-adopt.ro/com/eu` + `euadopt.com/de/es/eu/fr/org`.

## Mapare

| Domeniu | Rol |
|---------|-----|
| **eu-adopt.ro** (+ www) | România — site complet |
| **euadopt.com** (+ www) | Hub EU — EN + selector limbi |
| **euadopt.de / .fr / .es** (+ www) | **Active** — limba TLD, URL rămâne |
| **euadopt.eu / .org**, **eu-adopt.com / .eu** (+ www) | **301 →** `euadopt.com` |

## DNS

A/AAAA către Hetzner pentru toate hosturile.

## Nginx

`deploy/hetzner/nginx-euadopt-all-domains.conf` — proxy toate hosturile; Django face 301 doar pe aliasuri.

## Cod

- Registru: `home/euadopt_domains.py`
- Teste: `python manage.py test home.tests.test_eu_site`
