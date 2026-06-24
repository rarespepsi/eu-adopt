# EU-Adopt — deploy PRE-LAUNCH pe Hetzner (Ubuntu)

**VPS referință:** `178.104.31.52` (ubuntu-4gb-nbg1-3)  
**Domeniu:** `https://eu-adopt.ro`  
**Local PC:** dezvoltare | **Hetzner:** populare adăposturi + ONG

---

## 1. Variabile `.env` pe server (`/opt/eu-adopt/.env`)

```env
DJANGO_SECRET_KEY=<generează_cheie_lungă>
DJANGO_DEBUG=0
DJANGO_SECURE_SSL=1
DATABASE_URL=postgresql://euadopt:PAROLA@localhost:5432/euadopt

EUADOPT_SITE_BASE_URL=https://eu-adopt.ro

SITE_PUBLIC=1
EUADOPT_PRELAUNCH_MODE=1
EUADOPT_POPULATION_ONBOARDING=1
EUADOPT_SMS_OTP_ENABLED=0
EUADOPT_SMS_OTP_DEV_CODE=528419

EMAIL_HOST=smtppro.zoho.eu
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=contact@eu-adopt.ro
EMAIL_HOST_PASSWORD=<app_password_zoho>
DEFAULT_FROM_EMAIL=EU-Adopt Team <contact@eu-adopt.ro>

EUADOPT_STAFF_INVITE_EMAIL_ENABLED=0
```

---

## 2. Instalare inițială (o singură dată)

```bash
# ca root sau cu sudo
apt update && apt upgrade -y
apt install -y python3.12-venv python3-pip nginx postgresql certbot python3-certbot-nginx git

sudo -u postgres psql -c "CREATE USER euadopt WITH PASSWORD 'PAROLA';"
sudo -u postgres psql -c "CREATE DATABASE euadopt OWNER euadopt;"

adduser --disabled-password --gecos "" euadopt
sudo -u euadopt git clone https://github.com/rarespepsi/eu-adopt.git /opt/eu-adopt
cd /opt/eu-adopt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# creează .env (secțiunea 1)
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
mkdir -p media
chown -R euadopt:euadopt /opt/eu-adopt
```

Copiază fișierele din `deploy/hetzner/`:

```bash
cp deploy/hetzner/euadopt.service /etc/systemd/system/
cp deploy/hetzner/nginx-eu-adopt.conf /etc/nginx/sites-available/eu-adopt
ln -sf /etc/nginx/sites-available/eu-adopt /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
systemctl daemon-reload
systemctl enable --now euadopt
certbot --nginx -d eu-adopt.ro -d www.eu-adopt.ro
```

---

## 3. Update după `git push`

**Recomandat (backup DB automat + rotație 3):**

```bash
bash /opt/eu-adopt/deploy/hetzner/deploy_update.sh
```

**Din PC (copie bună locală + backup DB + deploy):**

```powershell
.\scripts\deploy_hetzner_from_pc.ps1
```

Detalii rollback: `docs/BACKUP_ROLLBACK.md`

**Manual (fără backup DB):**

```bash
cd /opt/eu-adopt && sudo -u euadopt bash -c '
  source venv/bin/activate
  git pull
  pip install -r requirements.txt
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
'
systemctl restart euadopt
```

---

## 4. DNS (după test pe server)

La registrar:

- `A` `@` → `178.104.31.52`
- `A` sau `CNAME` `www` → `178.104.31.52`

Înainte de DNS: test `curl -H "Host: eu-adopt.ro" http://127.0.0.1/login/`

---

## 5. Cine are acces în populare

| Rol | Login | După login |
|-----|-------|------------|
| **Adăpost / ONG** (`ROLE_ORG`) | Da (invitație email) | Acasă, PT, MyPet, Contact, Cont |
| **Staff** | Da | Complet |
| **PF / Colaborator** | Nu | — |
| **Anonim** | Doar login + signup organizație (invitație) | — |

Fără adopții, Shop, Transport, Servicii, I Love.

---

## 6. La lansare publică

Vezi `docs/POPULARE_ADAPOST_ONG.md` checklist L1–L5.
