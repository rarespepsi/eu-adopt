# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Backup setări EU Adopt – februarie 2026

**Documentul acesta salvează toate setările care funcționează. Dacă mâine ceva nu merge, urmează pașii de aici.**

---

## Link-uri importante

| Ce | URL |
|----|-----|
| Site live | https://eu-adopt.ro |
| Alternativ | https://eu-adopt.onrender.com |
| Admin | https://eu-adopt.ro/admin/ |
| Health check | https://eu-adopt.onrender.com/health/ |
| Render dashboard | https://dashboard.render.com |
| GitHub | https://github.com/rarespepsi/eu-adopt |

---

## Render – Web Service eu-adopt

### Root Directory
`adoptapet_pro`

### Build Command
```
./build.sh
```
*Alternativ (dacă build.sh lipsește):*
```
pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py seed_demo_pets && python manage.py collectstatic --noinput
```

### Start Command
```
bash start.sh
```

### Pre-Deploy Command (dacă e disponibil, poate fi blocat pe Free)
```
python manage.py migrate --noinput && python manage.py seed_demo_pets
```

---

## Variabile de mediu (Environment) – chei obligatorii

| Key | Unde se ia valoarea |
|-----|----------------------|
| `DATABASE_URL` | PostgreSQL → Connection → **Internal Database URL** |
| `SECRET_KEY` | https://djecrety.ir/ – generează un string lung |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `eu-adopt.onrender.com,eu-adopt.ro,www.eu-adopt.ro` |
| `RENDER` | `true` |

### Variabile opționale (email)
| Key | Exemplu |
|-----|---------|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_HOST_USER` | email Gmail |
| `EMAIL_HOST_PASSWORD` | parola aplicație Gmail |
| `DEFAULT_FROM_EMAIL` | `contact.euadopt@gmail.com` |

---

## Fișiere cheie

### build.sh
```bash
#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py seed_demo_pets
python manage.py collectstatic --noinput
```

### start.sh
```bash
#!/usr/bin/env bash
set -e
python manage.py migrate --noinput
python manage.py seed_demo_pets
exec gunicorn platforma.wsgi:application
```

### requirements.txt
```
Django>=6.0
pillow>=12.0
gunicorn>=21.0
whitenoise>=6.6
dj-database-url>=2.1
psycopg2-binary>=2.9
```

---

## Comenzi utile (rulează în PowerShell din adoptapet_pro)

### Creare admin nou (cu External Database URL din Render)
```powershell
$env:DATABASE_URL="postgresql://user:parola@host.frankfurt-postgres.render.com/dbname"; python manage.py createsuperuser
```

### Reset parolă toți adminii
```powershell
$env:DATABASE_URL="postgresql://..."; python manage.py reset_admin_passwords ParolaNoua123
```

### Push pe GitHub
```powershell
cd c:\Users\USER\Desktop\adoptapet_pro
& "C:\Program Files\Git\bin\git.exe" add .
& "C:\Program Files\Git\bin\git.exe" commit -m "mesaj"
& "C:\Program Files\Git\bin\git.exe" push origin main
```

---

## Dacă site-ul nu merge

1. **502 / se încarcă la nesfârșit** → Cold start. Așteaptă 1–2 min sau configurează UptimeRobot pe /health/
2. **„relation anunturi_pet does not exist”** → Migrațiile nu au rulat. Verifică că Start Command = `bash start.sh`
3. **Site gol, fără animale** → Manual Deploy în Render (rulează seed_demo_pets)
4. **Nu știi parola admin** → `reset_admin_passwords` (vezi mai sus)

---

## Structură proiect
- `adoptapet_pro/` – root (Root Directory pe Render)
  - `manage.py`
  - `build.sh`, `start.sh`
  - `requirements.txt`
  - `platforma/` – settings, urls
  - `anunturi/` – app principal
  - `templates/`, `static/`

---

---

## Când site-ul merge – salvează setările pentru backup

Când site-ul merge bine, memorează starea:
1. Verifică Render (Build/Start, Environment) și actualizează acest fișier dacă ai schimbat ceva.
2. Notează modificările de cod în **MODIFICARI.md**.
3. Fă **commit + push** pe GitHub. Mesaj exemplu: „Backup setări feb 2026”.

Astfel, dacă ceva nu mai merge, poți reveni la o versiune care funcționa.

---

*Backup făcut: februarie 2026. Păstrează acest fișier în proiect.*
