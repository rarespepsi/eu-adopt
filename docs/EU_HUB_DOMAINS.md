# Hub EU — domenii fără cratimă (principal)

**Actualizat:** portfolio Hostico — principal **`euadopt.*`**, dublaj **`eu-adopt.*`** → **301**.

## Mapare domenii

| Domeniu principal | Rol |
|-------------------|-----|
| **eu-adopt.ro** | România — site complet (singurul `.ro` din cont) |
| **euadopt.com**, **euadopt.eu**, **euadopt.org** (+ `www`) | Hub EU — selector **24 limbi UE + EN** |
| **euadopt.de**, **euadopt.fr**, **euadopt.es** (+ `www`) | Aceeași formă EU, limba forțată (DE / FR / ES) |

| Dublaj (301 → principal) | Țintă |
|------------------------|--------|
| eu-adopt.com, www | euadopt.com / www |
| eu-adopt.eu, www | euadopt.eu / www |

**Notă:** nu ai `euadopt.ro` — **`.ro` rămâne `eu-adopt.ro`** (fără redirect).

Redirect: **nginx** (recomandat) + **fallback Django** (`EU_HYPHEN_REDIRECT_MAP` în `home/eu_site.py`).

## DNS

Punctează A/AAAA către Hetzner pentru toate hosturile active (principal + dublaj, ca să poți face 301).

## Nginx

- `deploy/hetzner/nginx-eu-adopt-eu-hub.conf` — proxy pentru `euadopt.*`
- Blocuri HTTPS + `return 301` pentru `eu-adopt.com` / `.eu` către `euadopt.*`

## Cod

- `EUADOPT_EU_HUB_HOSTS` — override listă hub
- Teste: `python manage.py test home.tests.test_eu_site`

## Următorii pași

- Traducere fișe animale (Google + cache)
- Signup org EU simplificat
