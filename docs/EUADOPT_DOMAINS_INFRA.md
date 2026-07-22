# EU-Adopt — activare domenii (faza infra)

## Lista domeniilor (cumpărate, iul 2026)

| Host | Rol |
|------|-----|
| eu-adopt.ro, www.eu-adopt.ro | **RO principal** — fără redirect, nemodificat |
| euadopt.com, www.euadopt.com | **Activ** — același site ca .ro |
| euadopt.eu, www.euadopt.eu | **Activ** |
| euadopt.org, www.euadopt.org | **Activ** |
| euadopt.de, www.euadopt.de | **Activ** |
| euadopt.fr, www.euadopt.fr | **Activ** |
| euadopt.es, www.euadopt.es | **Activ** |
| eu-adopt.com, www.eu-adopt.com | **301** → euadopt.com / www |
| eu-adopt.eu, www.eu-adopt.eu | **301** → euadopt.eu / www |

**Nu sunt în cont:** euadopt.it, eu-adopt.org, euadopt.ro — nu configurate.

Afișare live din cod:

```bash
python manage.py euadopt_domains_list
```

Sursă: `home/euadopt_domains.py` → `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.

## Faza curentă (infra)

- `EUADOPT_EU_PRODUCT_SKIN=0` (implicit) — **nu** schimbă meniuri/limbi/rute pe non-.ro
- Redirect 301 cu cratimă (păstrează cale + query) în Django + nginx
- **eu-adopt.ro** rămâne site-ul românesc complet

Skin EU (meniu scurt, limbi): `EUADOPT_EU_PRODUCT_SKIN=1` — etapa următoare.

## DNS (Hostico → Hetzner)

Pentru fiecare host din tabel: **A** (și **AAAA** dacă folosești) → `178.104.31.52`.

## Hetzner

1. `git pull` + deploy obișnuit
2. `bash /opt/eu-adopt/deploy/hetzner/setup_euadopt_ssl_all_domains.sh`
3. Dupa certbot: ajusteaza caile certificatelor in `deploy/hetzner/nginx-euadopt-hyphen-redirect-443.conf` (certbot poate folosi un singur `-d` principal), apoi `include` fisierul in sites-enabled sau copiaza blocurile `return 301` pe :443
4. Verifică redirect HTTPS: eu-adopt.com → euadopt.com (nu toate spre .com)

## Verificări

```bash
curl -I https://eu-adopt.ro/
curl -I https://euadopt.fr/pets/
curl -I https://eu-adopt.com/contact/?x=1   # → euadopt.com, păstrează ?x=1
```

Autentificare: același user pe orice domeniu activ (sesiune per domeniu, același DB).
