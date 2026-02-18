# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Backup general EU Adopt – februarie 2026

**Fișier pentru recuperare. NU conține parole. Citește acest fișier într-o conversație nouă dacă ai nevoie de orientare.**

---

## Proiect
- **Nume:** EU Adopt
- **Folder local:** `c:\Users\USER\Desktop\adoptapet_pro`
- **Root Directory pe Render:** `adoptapet_pro`
- **GitHub:** https://github.com/rarespepsi/eu-adopt

---

## Link-uri
| Ce | URL |
|----|-----|
| Site | https://eu-adopt.ro |
| Alternativ | https://eu-adopt.onrender.com |
| Admin | https://eu-adopt.ro/admin/ |
| Health | https://eu-adopt.onrender.com/health/ |
| Render | https://dashboard.render.com |
| UptimeRobot | https://uptimerobot.com |
| Cloudinary | https://console.cloudinary.com |

---

## Render – setări Web Service eu-adopt

- **Root Directory:** `adoptapet_pro`
- **Build Command:** `./build.sh`
- **Start Command:** `bash start.sh`
- **Pre-Deploy Command** (dacă e disponibil): `python manage.py migrate --noinput && python manage.py seed_demo_pets`

---

## Variabile de mediu (chei, FĂRĂ valori)
- `DATABASE_URL` – din PostgreSQL → Info → Connection → Internal Database URL
- `SECRET_KEY` – generează pe https://djecrety.ir/
- `DEBUG` – `False`
- `ALLOWED_HOSTS` – `eu-adopt.onrender.com,eu-adopt.ro,www.eu-adopt.ro`
- `RENDER` – `true`
- Email (opțional): `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`

---

## Render – unde găsești ce
- **Projects** → **eu-adopt** → servicii (Web Service, PostgreSQL)
- **PostgreSQL (eu-adopt-db):** Info → Connection → URL-uri
- **Web Service (eu-adopt):** Settings, Environment, Manual Deploy

---

## Comenzi (PowerShell, din adoptapet_pro)

**cd în proiect:**
```
cd c:\Users\USER\Desktop\adoptapet_pro
```

**Creare admin:**
```
$env:DATABASE_URL="PASTE_EXTERNAL_URL"; python manage.py createsuperuser
```

**Reset parole admin:**
```
$env:DATABASE_URL="PASTE_EXTERNAL_URL"; python manage.py reset_admin_passwords ParolaNoua
```

**Push Git:**
```
& "C:\Program Files\Git\bin\git.exe" add .
& "C:\Program Files\Git\bin\git.exe" commit -m "mesaj"
& "C:\Program Files\Git\bin\git.exe" push origin main
```

*External URL = PostgreSQL → Info → Connection → External → Copy*

---

## Fișiere importante
- `build.sh` – pip, migrate, seed, collectstatic
- `start.sh` – migrate, seed, gunicorn
- `requirements.txt` – Django, pillow, gunicorn, whitenoise, dj-database-url, psycopg2-binary
- `anunturi/management/commands/seed_demo_pets.py` – animale demo
- `anunturi/management/commands/reset_admin_passwords.py` – reset parole admin
- **MODIFICARI.md** – istoric modificări (notează aici toate schimbările; pentru backup când site-ul merge)

---

## Probleme frecvente
| Eroare | Soluție |
|--------|---------|
| 502 / loading infinit | Cold start, așteaptă 1–2 min |
| relation anunturi_pet does not exist | Start Command = `bash start.sh` |
| Site gol, fără animale | Manual Deploy în Render |
| Parolă admin uitată | `reset_admin_passwords` cu External URL |

---

---

## Când site-ul merge – memorează setările pentru backup

Din când în când, când totul funcționează:
1. Verifică că setările din acest fișier și din **SETARI_BACKUP.md** sunt la zi.
2. Notează orice modificare nouă în **MODIFICARI.md**.
3. Fă **commit + push** pe GitHub (ex: „Backup setări – [dată]”). Astfel ai un punct de recuperare dacă ceva se strică.

---

*Fără parole. Actualizat feb. 2026.*
