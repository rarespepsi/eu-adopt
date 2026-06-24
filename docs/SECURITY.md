# Securitate EU-Adopt

Checklist și proceduri pentru server (Hetzner) și aplicație Django.

## Aplicație (Django)

| Măsură | Stare |
|--------|--------|
| `DEBUG=0` în producție | `.env` pe server |
| `DJANGO_SECRET_KEY` unic | `.env` (nu în git) |
| HTTPS + HSTS + cookie-uri secure | `DJANGO_SECURE_SSL=1` |
| CSRF, SecurityMiddleware, clickjacking | `settings.py` |
| Mod pre-launch (login obligatoriu) | `EUADOPT_PRELAUNCH_MODE=1` |
| Rate-limit login | `AUTH_LOGIN_RATE_LIMIT_PER_15MIN` (implicit 15 / 15 min / IP) |
| Rate-limit reset parolă | `AUTH_FORGOT_PASSWORD_RATE_LIMIT_PER_HOUR` (implicit 5 / oră / IP) |
| Restricție `/admin/` opțională | `EUADOPT_ADMIN_ALLOW_IP=IP1,IP2` în `.env` |

### Variabile `.env` (securitate)

```env
DJANGO_DEBUG=0
DJANGO_SECURE_SSL=1
DJANGO_HSTS_PRELOAD=1
EUADOPT_PRELAUNCH_MODE=1
# Opțional: doar IP-ul tău de birou/acasă pentru Django admin
EUADOPT_ADMIN_ALLOW_IP=xxx.xxx.xxx.xxx
```

## Server (Hetzner)

| Măsură | Script |
|--------|--------|
| UFW (22, 80, 443) | `deploy/hetzner/harden_server.sh` |
| fail2ban SSH | același script |
| Headere nginx | `deploy/hetzner/apply_nginx_security.sh` |
| SSH fără parolă (după test cheie) | `EUADOPT_SSH_HARDEN=1 bash .../harden_server.sh` |
| Backup DB rotație 3 | `deploy/hetzner/backup_db_rotate.sh` + cron |
| Actualizări OS | `unattended-upgrades` |

### Prima rulare hardening

```bash
# Pe server, după git pull:
bash /opt/eu-adopt/deploy/hetzner/harden_server.sh

# După ce confirmi că te conectezi cu cheie SSH (fără parolă):
EUADOPT_SSH_HARDEN=1 bash /opt/eu-adopt/deploy/hetzner/harden_server.sh
```

## Înainte de fiecare deploy

1. `pip-audit -r requirements.txt` (local)
2. `python manage.py check --deploy` (cu env de producție simulat sau pe server)
3. `.\scripts\deploy_hetzner_from_pc.ps1` (backup local + DB + pull)

## Dependențe

Menține Django la ultimul patch din seria 6.0.x (`requirements.txt`). La upgrade: teste + deploy.

## Ce nu înlocuiește antivirusul

Pe VPS Linux nu e nevoie de antivirus desktop. Protecția vine din firewall, SSH dur, patch-uri, backup-uri, rate-limit și parole puternice staff.

## Opțional (viitor)

- Cloudflare (WAF + DDoS) în fața domeniului
- 2FA pentru conturi staff
- `pip-audit` în CI
- CSP strict (Content-Security-Policy) — test gradual, poate afecta scripturi inline
