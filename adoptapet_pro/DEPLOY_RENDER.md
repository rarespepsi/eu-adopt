# Ghid deploy EU Adopt pe Render

## Ce trebuie să faci tu

### Pasul 1: Cont GitHub

1. Creează cont pe **https://github.com** (dacă nu ai)
2. Instalează **Git** pe computer: https://git-scm.com/download/win
3. Deschide **PowerShell** în folderul proiectului (`adoptapet_pro`)

### Pasul 2: Pune proiectul pe GitHub

În PowerShell, rulează:

```powershell
cd C:\Users\USER\Desktop\adoptapet_pro

# Inițializează Git (dacă nu e deja)
git init

# Adaugă toate fișierele
git add .

# Salvă
git commit -m "EU Adopt - pregătit pentru deploy"

# Creează un repo nou pe GitHub (manual): https://github.com/new
# Nume: eu-adopt sau adoptapet-pro
# Fără README, fără .gitignore (ai deja)

# Conectează și trimite (înlocuie USER și REPO cu ale tale)
git remote add origin https://github.com/USER/REPO.git
git branch -M main
git push -u origin main
```

### Pasul 3: Cont Render

1. Mergi la **https://render.com**
2. Sign up cu **GitHub** (conectează contul)
3. Autorizează Render să acceseze repository-urile tale

### Pasul 4: Creează PostgreSQL

1. În Render: **New** → **PostgreSQL**
2. Nume: `eu-adopt-db`
3. Region: **Frankfurt** (sau cel mai apropiat)
4. Plan: **Free**
5. **Create Database**
6. Copiază **Internal Database URL** (o vei folosi la Web Service)

### Pasul 5: Creează Web Service

1. **New** → **Web Service**
2. Conectează repository-ul **eu-adopt** (sau cum l-ai numit)
3. Setări:
   - **Name:** `eu-adopt`
   - **Region:** Frankfurt
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn platforma.wsgi:application`

### Pasul 6: Variabile de mediu (Environment Variables)

În Web Service → **Environment** → **Add Environment Variable**:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | *(copy from PostgreSQL - Internal Database URL)* |
| `SECRET_KEY` | *(generează unul: https://djecrety.ir/ sau un string random lung)* |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `eu-adopt.onrender.com,eu-adopt.ro,www.eu-adopt.ro` |
| `RENDER` | `true` |

**Email** (opțional – pentru cereri adopție): vezi **GHID_EMAIL.md**. Variabile: `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`.

### Pasul 7: Deploy

1. Click **Create Web Service**
2. Așteaptă 5–10 minute (build + deploy)
3. Site-ul va fi live la `https://eu-adopt.onrender.com`

### Pasul 8: Migrări și superuser

După primul deploy reușit:

1. În Render: Web Service → **Shell**
2. Rulează:
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Pasul 9: Conectează domeniul eu-adopt.ro

1. În Render: Web Service → **Settings** → **Custom Domains**
2. **Add Custom Domain** → `eu-adopt.ro`
3. Render îți va arăta valorile DNS de setat (ex: A Record, CNAME)
4. Mergi la **ROTLD** (pentru .ro): https://portal.rotld.ro – autentificare cu parola primită la înregistrare
5. Găsești zona DNS pentru eu-adopt.ro și adaugi înregistrările (valorile Render):

| Hostname | Tip | Target / Value |
|----------|-----|----------------|
| `www` | CNAME | `eu-adopt.onrender.com` |
| `@` (root) | **A record** | `216.24.57.1` |

*Pentru root (@), unele provideri DNS (inclusiv ROTLD) nu acceptă CNAME – folosești A record cu IP-ul de mai sus.*
6. Așteaptă propagarea DNS (până la 48h, de obicei < 1h)
7. În Render: adaugă și `www.eu-adopt.ro` ca custom domain
8. Actualizează `ALLOWED_HOSTS` să includă `eu-adopt.ro,www.eu-adopt.ro`

---

## Notă despre poze (media)

Pe planul **Free** al Render, pozele încărcate de utilizatori **se pierd la fiecare redeploy** (disco ephemeral). Pentru producție serioasă, va trebui integrare cu **Cloudinary** sau **AWS S3**. Pentru testare și lansare inițială, funcționează așa.

---

## Dacă pagina se încarcă foarte lent sau nu se încarcă (cold start)

Pe planul **Free**, Render oprește serviciul după ~15 min de inactivitate. La primul acces după ce s-a oprit, „trezirea” poate dura **30 sec – 2 minute** (sau chiar mai mult).

**Soluție gratuită – UptimeRobot (ține site-ul treaz):**
1. Mergi la **https://uptimerobot.com** și creează cont gratuit
2. **Add New Monitor**
3. **Monitor Type:** HTTP(s)
4. **URL:** `https://eu-adopt.onrender.com/health/`
5. **Monitoring Interval:** 5 minute (sau 10 min pe plan free)
6. **Create Monitor**

UptimeRobot va face request la site la fiecare 5–10 min → serviciul rămâne treaz → paginile se încarcă rapid.

**Alternativă:** încarcă din nou pagina după 1–2 min – cold start-ul poate dura.

---

## Dacă ceva nu merge

- **Build failed:** verifică că `requirements.txt` e în root
- **Application failed to start:** verifică Start Command și logs
- **Static files lipsesc:** build command trebuie să ruleze `collectstatic`
- **502 Bad Gateway / timeout:** așteaptă 1–2 min – serviciul free pornește la primul request
