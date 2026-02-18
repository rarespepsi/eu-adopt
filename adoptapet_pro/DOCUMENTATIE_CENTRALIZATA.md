# 📚 Documentație Centralizată – EU Adopt

**Toate informațiile importante despre proiect într-un singur loc.**

*Ultima actualizare: februarie 2026*

---

# 📋 Cuprins

1. [Informații Generale Proiect](#informații-generale-proiect)
2. [Wishlist & Viziune](#wishlist--viziune)
3. [Reguli UI Globale](#reguli-ui-globale)
4. [Setări Logo](#setări-logo)
5. [Backup & Deploy](#backup--deploy)
6. [Ghiduri Tehnice](#ghiduri-tehnice)
7. [Formulare & Funcționalități](#formulare--funcționalități)
8. [Istoric Modificări](#istoric-modificări)
9. [Agenda Proiecte](#agenda-proiecte)
10. [Reminder-uri](#reminder-uri)

---

# Informații Generale Proiect

## Proiect
- **Nume:** EU Adopt
- **Folder local:** `c:\Users\USER\Desktop\adoptapet_pro`
- **Root Directory pe Render:** `adoptapet_pro`
- **GitHub:** https://github.com/rarespepsi/eu-adopt

## Link-uri Importante

| Ce | URL |
|----|-----|
| Site live | https://eu-adopt.ro |
| Alternativ | https://eu-adopt.onrender.com |
| Admin | https://eu-adopt.ro/admin/ |
| Health check | https://eu-adopt.onrender.com/health/ |
| Render dashboard | https://dashboard.render.com |
| GitHub repo | https://github.com/rarespepsi/eu-adopt |
| UptimeRobot | https://uptimerobot.com |
| Cloudinary | https://console.cloudinary.com |

## Ce Există Acum (Baza)
- Django 6, app `anunturi`
- Model **Pet**: nume, rasă, tip (câine/pisică – de extins la **altele**: păsări, magari, etc.), vârstă, sex, mărime, descriere, imagine, status (adoptable / pending / adopted), tags
- Pagini: home, listă animale (`pets-all`), pagină animal (`pets/<id>/`), admin Django

---

# Wishlist & Viziune

## Context / De Ce Există Proiectul

- Fondatorul a fost **director la un adăpost public de câini din România**.
- **Realitatea din teren**: în România sunt multe padocuri (de stat sau private) care **nu au publicitate la adopție în adevăratul sens al cuvântului** – animalele există, dar nu sunt promovate cum trebuie.
- **Problema principală**: promovarea animalelor din adăpost pentru adopție – doar Facebook odată nu era suficient (vizibilitate limitată, un singur post, nu un „catalog” persistent).
- Site-ul vizează să rezolve asta: un loc unde animalele să fie promovate **continuu**, vizibile, ușor de găsit și de partajat – pentru orice adăpost care vrea să iasă din invizibilitate.
- **Obiectiv**: **centralizarea tuturor câinilor din țară dați spre adopție** – un singur punct unde adoptatorul poate vedea oferta din toate adăposturile.
- **Realitate**: mare parte din câinii dați spre adopție **nu sunt de rasă** – sunt **metiși / maidanezi**. Site-ul trebuie să reflecte asta (câmp rasă: Metis, Maidanez, eventual „mix” sau rase doar opțional), nu un catalog de rase pure.

## Clienți / Public Țintă

**Clienții** site-ului (membri care postează animale) sunt două categorii:

1. **Adăposturi din România** – publice sau private. Postează animalele din adăpost; devin membri ai platformei.
2. **Asociații de profil** – asociații cu profil (protecția animalelor, adopții, etc.). La fel, devin membri și postează animalele pe care le au în grijă.

**Beneficiari** (nu plătesc, dar folosesc site-ul): **adoptatorii** – persoane care caută un animal, folosesc filtre, descrieri, poze, link de partajat.

**Persoane fizice** – încă neclar cum le tratăm. Opțiuni:
- Nu le permitem la început – doar adăposturi + asociații
- Le permitem cu limită strictă – ex. max 1–3 animale per persoană
- Le permitem ca a treia categorie de membru
- Doar prin partener

*Decizie de luat după ce stabilim bine fluxul pentru adăposturi și asociații.*

## Model Membri – Listă de Membri, Gratuit / Plătit

- **Primele 6 luni: 100% gratuit** – nu se așteaptă clienți din prima; perioada de lansare și creștere, fără taxe.
- **După 6 luni: putem taxa** – limită gratuită (ex. până la **50 animale/lună**), peste care abonament plătit.
- **Transport asigurat de platformă** – platforma ia un procent/comision din suma pentru transport (sursă de venit).
- **Bandou de reclame** – reclame ale producătorilor de mâncare pentru animale, produse pentru animale, servicii veterinare, etc.

## Wish List – Funcționalități

### Pentru Promovare (Prioritate Mare)
- **Link unic per animal** – ușor de partajat pe Facebook, WhatsApp, e-mail
- **Filtre pe listă**: tip animal (Câine, Pisică, Altele), vârstă, mărime, sex, status
- **Căutare** după nume, rasă sau cuvinte din descriere
- **Pagină animal** cu poze, descriere, tags, status
- **SEO** – titluri/descrieri ok ca site-ul să apară la căutări

### Pentru Membri (Adăposturi și Asociații)
- **Conturi / membri** – fiecare vede și editează doar animalele ei
- **Verificare membri (obligatorie)**: certificat de înregistrare, copie buletin administrator, telefon, adresă
- **Adresă obligatorie, localizată pe Google Maps**
- **Limită gratuită** – ex. până la **50 animale postate pe lună** gratuit
- **Admin / panou membru** – adăugare/editare animale, poze, status
- **Import în bulk** – Excel/CSV cu animale
- **Raport simplu** – câte animale adoptable, pending, adopted

### Bandou / Reclame Parteneri
- Zone rezervate pentru **reclame ale producătorilor de mâncare** pentru animale, produse pentru animale, servicii veterinare, etc.
- Doar reclame legate de animale (mâncare, îngrijire, veterinar, etc.)

### Integrări / Partajare
- **Partajare în 1 click** – butoane Share pentru Facebook, WhatsApp
- (Opțional) **Export / preview pentru post Facebook**

### Facilități / Servicii
- **Transport** – ofertantul/adăpostul asigură transport
- **Transport în altă zonă – asigurat de platformă**
- **Preluare de la ofertant în cabinet veterinar**
- **Listă de transportatori** – național și internațional

### Donații
- **Donații în bani** – secțiune/pagină unde vizitatorii pot dona
- **Cei 3,5% din impozit** – informații și opțiune pentru redirectarea 3,5% din impozitul pe venit

### Limbi (Multilingv)
- **Site-ul să aibă limbile frecvente** – română, engleză, spaniolă, italiană, germană, rusă, etc.
- Româna rămâne limbă principală

### Calitate & Încredere
- **Poze multiple** per animal (galerie)
- **Status vizibil** – Adoptable / În procedură / Adoptat
- **Data actualizării** – „Actualizat la …” pe anunț
- **Date medicale obligatorii** – sterilizat, cipat, microcipat, vaccinuri
- **Validare imagini** – script/API care recunoaște animalul în poză
- **Control postări per membru** – flux de verificare înainte de publicare

## Prioritizare

| Prioritate | Ce |
|------------|-----|
| P0 (acum) | Filtre pe listă, link partajabil, site în română, contact clar; **juridice puternice** – termeni și condiții, disclaimer, excludere răspundere, acceptare explicită (bifă), validare avocat |
| P1 | Căutare, poze multiple, locație; **facilități pe pagină**; **loc pentru donații**; **limbi frecvente** (română, engleză, spaniolă, italiană, germană, rusă, etc.) – multilingv |
| P2 | **Membri** – cont per adăpost; **verificare foarte bună** (certificat înregistrare, copie buletin administrator, telefon, adresă, siguranță maximă); adresă Google Maps; date medicale; import bulk, raport simplu |
| P3 | **Control postări**; **validare imagini**; limită 50/lună + abonament; **listă transportatori**; **bandou reclame** (producători mâncare, produse animale); **concurs / laudă membru**; share, SEO, export |

---

# Reguli UI Globale

## Reguli Fundamentale pentru Interfața Site-ului

### 1. Sistem de Slot-uri (A0–A17)
- Website folosește sistemul de **SLOT-uri** identificate **A0–A17**.
- Fiecare slot poate fi controlat individual prin ID (A6, A9, etc.).

### 2. Structura Layout-ului
- **Structura layout-ului NU trebuie schimbată** decât dacă este explicit solicitat.
- Nu modifica pozițiile slot-urilor, coloanele sau structura grid-ului.

### 3. Tipuri de Conținut în Slot-uri
Toate slot-urile trebuie să suporte:
- **Imagine**
- **Video**
- **Animație**

### 4. Sidebar-uri Fixe
- **Sidebar-urile stânga și dreapta sunt FIXE (freeze)**.
- Nu se deplasează la scroll.
- Doar conținutul din **CENTRU** se scroll-ează.

### 5. Scroll Behavior
- **Doar conținutul CENTRAL** se scroll-ează.
- Sidebar-urile rămân fixe în poziție.

### 6. Înălțimi Standardizate pentru Sidebar-uri
- Slot-urile din sidebar-uri trebuie să aibă **înălțimi standardizate**.

### 7. Pagina HOME
- **Pagina HOME este o pagină de CĂUTARE / CATALOG**, nu o pagină informațională.
- Focus pe funcționalitate de căutare și listare animale.

### 8. Text în Slot-uri
- **Textul din slot-uri trebuie să fie scurt**.
- **Maximum 2–3 linii** de text per slot.

### 9. Reclame
- **Reclamele NU trebuie să împingă sau să redimensioneze conținutul central**.

### 10. Prioritate: Stabilitate Design
- **Stabilitatea design-ului are prioritate** față de efecte vizuale.

### 11. Control Individual al Slot-urilor
- Slot-urile pot fi controlate individual prin ID (A6, A9, etc.).

### 12. Modul VIP Stacked
- **Modul VIP stacked trebuie să fie suportat** fără schimbări de layout.

### 13. Responsive Design
- **Comportamentul responsive trebuie păstrat** pe ecrane mai mici.

---

# Setări Logo

## Configurație Generală Logo

### Dimensiuni Standard
- Container logo: 320px x 320px
- Imagine logo: 229px x 229px
- Stele: 260px x 260px (cerc)
- Fundal circular alb: raza 114.5px

### Stele
- 12 stele alternând galben (#FFD700) și albastru (#003399)
- Formă: 5 vârfuri
- Distribuție: uniformă pe cerc, raza 104px (viewBox 300x300)
- Poziționare: centrat pe logo

### Stiluri Generale
- `border-radius: 50%` pentru formă circulară
- `background-color: #FFFFFF` pentru fundal alb
- `box-shadow: 0 2px 8px rgba(0,0,0,0.15)` pentru umbrire
- `object-fit: contain` pentru imaginea logo-ului

## Pagina Home

### Poziție Logo
- Logo în hero: `left: 30px`, `top: 50%`, `transform: translateY(-50%)`
- Logo original (ascuns pe home): `left: -360px`, `top: 184px`
- Clasă body: `page-home`

### Text Identificare
- Text "1home" roșu pe sigla de pe pagina home (identificare)

## Pagina Animale

### Poziție Logo
- Similar cu pagina home (verifică CSS pentru `.the_logo_link`)
- Clasă body: `page-animale`

### Text Identificare
- Text "1animale" roșu pe sigla de pe pagina Animale (identificare)

### Observații
- Logo-ul este inclus în burtiera mică (strip banner) pe partea stângă
- Clasă CSS: `#burtiera_mica .burtiera_logo`

## Pagina Contact

### Logo 1 (Din Stânga)
- **Poziție**: `left: 983px` (29 cm de la marginea stângă)
- **Top**: `12px`
- **Clasă**: `.the_logo_link_contact_left`
- **ID**: `#logo_contact_left`
- **Text identificare**: "2contact" (roșu)
- **Stele**: Normal (fără oglindă)

### Logo 2 (Din Dreapta, Oglindit)
- **Poziție**: `right: -567px` (15 cm în afara containerului, pe partea dreaptă)
- **Top**: `12px`
- **Clasă**: `.the_logo_link_contact`
- **ID**: `#logo_contact`
- **Text identificare**: "1contact" (roșu, oglindit)
- **Transform**: `scaleX(-1)` (oglindă orizontală)
- **Stele**: Oglindite (`transform: translate(-50%, -50%) scaleX(-1)`)

### Observații Pagina Contact
- Logo-ul din header a fost șters din HTML (nu apare)
- Clasă body: `page-contact`
- Container: `#main_content .container` cu `overflow: visible !important`

## Texturi Provizorii pentru Identificare

### Stiluri Text Identificare
- Font size: 40px
- Font weight: bold
- Culoare: red (#FF0000)
- Fundal: rgba(255, 255, 255, 0.9)
- Padding: 10px 20px
- Border: 3px solid red
- Border radius: 10px
- Text shadow: 2px 2px 4px rgba(0,0,0,0.5)
- Z-index: 100
- Pointer events: none

### Texturi pe Pagini
- Home: "1home"
- Animale: "1animale"
- Contact Logo 1: "1contact"
- Contact Logo 2: "2contact"

**NOTĂ**: Aceste texturi sunt provizorii pentru comunicare și vor fi eliminate la finalizare.

## Fișiere Modificate

### Templates HTML
- `templates/anunturi/home.html` - Clasă body `page-home`, logo în hero
- `templates/anunturi/pets-all.html` - Clasă body `page-animale`
- `templates/anunturi/contact.html` - Clasă body `page-contact`, logo din header șters

### CSS
- `static/css/style.css` - Toate stilurile pentru logo-uri și texturi provizorii

---

# Backup & Deploy

## Render – Setări Web Service eu-adopt

- **Root Directory:** `adoptapet_pro`
- **Build Command:** `./build.sh`
- **Start Command:** `bash start.sh`
- **Pre-Deploy Command** (dacă e disponibil): `python manage.py migrate --noinput && python manage.py seed_demo_pets`

## Variabile de Mediu (Chei, FĂRĂ Valori)

| Key | Unde se ia valoarea |
|-----|----------------------|
| `DATABASE_URL` | PostgreSQL → Info → Connection → Internal Database URL |
| `SECRET_KEY` | https://djecrety.ir/ – generează un string lung |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `eu-adopt.onrender.com,eu-adopt.ro,www.eu-adopt.ro` |
| `RENDER` | `true` |
| `CLOUDINARY_URL` | Cloudinary Dashboard → Settings → Product Environment Credentials |
| `EMAIL_HOST` | `smtp.gmail.com` (opțional) |
| `EMAIL_HOST_USER` | Email Gmail (opțional) |
| `EMAIL_HOST_PASSWORD` | Parolă aplicație Gmail (opțional) |
| `DEFAULT_FROM_EMAIL` | `contact.euadopt@gmail.com` (opțional) |
| `SITE_PUBLIC` | `False` (pentru site în pregătire) sau `True` |
| `MAINTENANCE_SECRET` | Cod secret pentru acces când site-ul e în pregătire |

## Comenzi Utile (PowerShell, din adoptapet_pro)

### Creare admin nou
```powershell
$env:DATABASE_URL="PASTE_EXTERNAL_URL"; python manage.py createsuperuser
```

### Reset parolă toți adminii
```powershell
$env:DATABASE_URL="PASTE_EXTERNAL_URL"; python manage.py reset_admin_passwords ParolaNoua123
```

### Push pe GitHub
```powershell
cd c:\Users\USER\Desktop\adoptapet_pro
& "C:\Program Files\Git\bin\git.exe" add .
& "C:\Program Files\Git\bin\git.exe" commit -m "mesaj"
& "C:\Program Files\Git\bin\git.exe" push origin main
```

*External URL = PostgreSQL → Info → Connection → External → Copy*

## Fișiere Cheie

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
python-dotenv>=1.0
```

## Probleme Frecvente

| Eroare | Soluție |
|--------|---------|
| 502 / loading infinit | Cold start, așteaptă 1–2 min |
| relation anunturi_pet does not exist | Start Command = `bash start.sh` |
| Site gol, fără animale | Manual Deploy în Render |
| Parolă admin uitată | `reset_admin_passwords` cu External URL |

## Acces Doar Tu Când Site-ul E „În Pregătire”

Când `SITE_PUBLIC = False`, doar tu poți vedea site-ul de pe laptop (restul văd „Site în pregătire”).

### Pași

1. **Setează un cod secret** în `.env` sau pe Render:
   ```
   MAINTENANCE_SECRET=Ma1nt3nanc3-2025
   ```

2. **Pe laptop**, deschide o singură dată în browser:
   ```
   https://siteul-tau.ro/acces-pregatire/Ma1nt3nanc3-2025/
   ```

3. După ce intri pe acel link, se setează un **cookie** în browser. De atunci, **doar pe acel laptop** vei vedea site-ul normal.

- Cookie-ul e valabil **30 de zile**.
- **Nu partaja** link-ul (conține codul secret).

## Când Site-ul Merge – Salvează Setările pentru Backup

Când site-ul merge bine:
1. Verifică că setările din acest fișier sunt la zi.
2. Notează orice modificare nouă în secțiunea **Istoric Modificări**.
3. Fă **commit + push** pe GitHub (ex: „Backup setări – [dată]”).

---

# Ghiduri Tehnice

## Ghid Deploy pe Render

### Pasul 1: Cont GitHub
1. Creează cont pe **https://github.com**
2. Instalează **Git** pe computer: https://git-scm.com/download/win
3. Deschide **PowerShell** în folderul proiectului (`adoptapet_pro`)

### Pasul 2: Pune Proiectul pe GitHub
```powershell
cd C:\Users\USER\Desktop\adoptapet_pro
git init
git add .
git commit -m "EU Adopt - pregătit pentru deploy"
git remote add origin https://github.com/USER/REPO.git
git branch -M main
git push -u origin main
```

### Pasul 3: Cont Render
1. Mergi la **https://render.com**
2. Sign up cu **GitHub** (conectează contul)

### Pasul 4: Creează PostgreSQL
1. În Render: **New** → **PostgreSQL**
2. Nume: `eu-adopt-db`
3. Region: **Frankfurt**
4. Plan: **Free**
5. Copiază **Internal Database URL**

### Pasul 5: Creează Web Service
1. **New** → **Web Service**
2. Conectează repository-ul **eu-adopt**
3. Setări:
   - **Name:** `eu-adopt`
   - **Region:** Frankfurt
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `./build.sh`
   - **Start Command:** `bash start.sh`

### Pasul 6: Variabile de Mediu
Adaugă în Web Service → **Environment**:
- `DATABASE_URL` (din PostgreSQL)
- `SECRET_KEY` (generează pe https://djecrety.ir/)
- `DEBUG` = `False`
- `ALLOWED_HOSTS` = `eu-adopt.onrender.com,eu-adopt.ro,www.eu-adopt.ro`
- `RENDER` = `true`
- `CLOUDINARY_URL` (din Cloudinary Dashboard)

### Pasul 7: Deploy
1. Click **Create Web Service**
2. Așteaptă 5–10 minute (build + deploy)
3. Site-ul va fi live la `https://eu-adopt.onrender.com`

### Pasul 8: Superuser
1. În Render: Web Service → **Shell**
2. Rulează: `python manage.py createsuperuser`

### Pasul 9: Conectează Domeniul eu-adopt.ro
1. În Render: Web Service → **Settings** → **Custom Domains**
2. **Add Custom Domain** → `eu-adopt.ro`
3. Setează DNS la ROTLD (portal.rotld.ro):
   - `www` CNAME → `eu-adopt.onrender.com`
   - `@` A record → `216.24.57.1`

## Cloudflare pentru eu-adopt.ro

### Pași
1. Cont Cloudflare: https://dash.cloudflare.com/sign-up
2. Adaugă domeniul: **eu-adopt.ro**
3. Plan: **Free**
4. Notează nameserverele date de Cloudflare
5. Schimbă nameserverele la registrar (unde ai cumpărat domeniul)
6. În Cloudflare → DNS → Records:
   - **A record**: Name `@`, IPv4 `216.24.57.1`, Proxy DNS only
   - **CNAME**: Name `www`, Target `eu-adopt.onrender.com`, Proxy DNS only

## Ghid Configurare Email

### Varianta 1: Gmail (Cea Mai Simplă)

1. Creează un Gmail dedicat (ex: `euadopt.contact@gmail.com`)
2. Activează „Parola pentru aplicații”:
   - Mergi la: https://myaccount.google.com/security
   - **Verificare în 2 pași** – trebuie să fie **activată**
   - **Parole pentru aplicații** – Creează o parolă nouă
   - Copiază parola (șir de 16 caractere)

3. Variabile pe Render:
   | Key | Value |
   |-----|-------|
   | `EMAIL_HOST` | `smtp.gmail.com` |
   | `EMAIL_PORT` | `587` |
   | `EMAIL_USE_TLS` | `true` |
   | `EMAIL_HOST_USER` | `euadopt.contact@gmail.com` |
   | `EMAIL_HOST_PASSWORD` | `abcdefghijklmnop` (parola pentru aplicație) |
   | `DEFAULT_FROM_EMAIL` | `euadopt.contact@gmail.com` |

### Varianta 2: contact@eu-adopt.ro

Pentru adrese tip `contact@eu-adopt.ro` ai nevoie de:
1. Serviciu de email pe domeniu (Zoho Mail, Google Workspace, etc.)
2. Configurare DNS la ROTLD (înregistrări MX)
3. În Django/Render – folosești SMTP-ul furnizorului

## Ghid pentru Începători

### 1. Python
- Limbajul de programare în care e scrisă aplicația Django
- Comenzi: `python manage.py runserver`, `python manage.py migrate`

### 2. Cursor (IDE-ul)
- Editorul în care editezi codul
- **Ctrl+S** – salvează fișierul
- **Ctrl+Shift+P** – deschide paleta de comenzi

### 3. Terminal (PowerShell)
- Fereastra unde scrii comenzi text
- Comenzi: `cd`, `dir`, `python --version`, `pip install`

### 4. Git
- Sistem de control al versiunilor
- Comenzi: `git status`, `git add .`, `git commit -m "mesaj"`, `git push`

### 5. GitHub
- Serviciu online unde stochezi codul
- Nu editezi direct codul pe GitHub – editezi local și faci push

### 6. Django
- Framework Python pentru site-uri web
- Structură: `manage.py`, `platforma/`, `anunturi/`, `templates/`

### 7. Render
- Platformă de hosting – rulează site-ul tău pe internet
- Conectat la GitHub – la fiecare `git push` face deploy automat

### Fluxul Complet: De La Modificare La Site Live

1. Deschizi proiectul în Cursor
2. Modifici fișierele necesare
3. Salvezi (Ctrl+S)
4. Testezi local (opțional): `python manage.py runserver`
5. Commit: `git add .` → `git commit -m "Descriere"`
6. Push: `git push origin main`
7. Render ia codul de pe GitHub și face deploy (2–5 min)
8. Verifici site-ul live: https://eu-adopt.onrender.com

## Cold Start (Site Se Încarcă Foarte Lent)

Pe planul **Free**, Render oprește serviciul după ~15 min de inactivitate. La primul acces după ce s-a oprit, „trezirea” poate dura **30 sec – 2 minute**.

**Soluție gratuită – UptimeRobot:**
1. Mergi la **https://uptimerobot.com** și creează cont gratuit
2. **Add New Monitor**
3. **Monitor Type:** HTTP(s)
4. **URL:** `https://eu-adopt.onrender.com/health/`
5. **Monitoring Interval:** 5 minute
6. **Create Monitor**

UptimeRobot va face request la site la fiecare 5 min → serviciul rămâne treaz → paginile se încarcă rapid.

---

# Formulare & Funcționalități

## Formulare Existente

| Formular | Unde | Scop |
|----------|------|------|
| **Formular cerere adopție** | Pagina animalului (`/pets/<id>/adoption/`) | Vizitatorul completează: nume complet, email, telefon, adresă, mesaj, ridicare personală Da/Nu, opțiuni transport/cazare medicală |
| **Validare platformă** | Automată (backend) | Verificare condiții: nume 2+ cuvinte, telefon 10+ cifre, mesaj/adresă în limite. Dacă trece → trimitere email la ONG cu link validare |
| **Validare ONG** | Link în email (unic) | ONG apasă pe link → se trimit datele adoptatorului către ONG și cartea de vizită către adoptator; cererea devine „Validată de ONG” |

## Formular Verificare Post-Adopție

- **Angajament adoptator:** prin validarea cererii de adopție, adoptatorul **își asumă** că la fiecare **6 luni** va trimite **o poză sau mai multe** cu animalul
- **Formular verificare post-adopție:** implementat – pagină `/adoption/verificare/<token>/` (link în emailul de follow-up), mesaj + opțional 3 poze (max 2 MB)

## Email Automat la 3 sau 6 Luni După Adopție

- La fiecare **adopție finalizată** (status `approved_ong`) se trimite **automat** un email la **3** sau **6 luni** cu link către formularul de verificare post-adopție
- **Implementare:** Comandă `python manage.py send_post_adoption_followups` (opțional `--months 6`, `--dry-run`)
- Setare `POST_ADOPTION_FOLLOWUP_MONTHS = 6` în settings
- Programare cron pe server (ex. zilnic)

## Verificare Online CUI/CIF (Membri cu Date Oficiale)

Script și surse pentru verificarea veridicității informațiilor (CUI/CIF) ale membrilor:

| Tip | Surse (gratuit) |
|-----------|------------------|
| **SRL** | termene.ro (date de bază), listafirme.ro (date principale) |
| **ONG/AF** | portal.just.ro → Registrul Național ONG (registrul oficial) |

- **Modul:** `anunturi/official_verification.py` – `verify_srl_cui()`, `verify_ong_registry()`, `verify_member_official_data()`
- **Comandă:** `python manage.py verify_cui_members` (opțional `--user ID`, `--verbose`)
- **Setări:** `LISTAFIRME_API_KEY` (dacă e setat, se folosește API listafirme.ro)

## Convenții Formulare

**De acum înainte:** unde trebuie create formulare și nu avem încă toate datele/câmpurile finale, creăm formularul cu ce date avem și pe parcurs **doar modificăm** (adăugăm sau ajustăm câmpuri). Nu așteptăm lista completă; iterăm.

**Faza curentă:** construim **baza** (fluxuri, categorii, date esențiale). Finisaje, rafinări și „finete" le facem când lucrăm explicit la ele.

## De Nu Uitat – Checklist

**Cron / automatizări**
- [ ] Cron (ex. zilnic) pentru `python manage.py send_post_adoption_followups` – email follow-up la 3/6 luni după adopție finalizată

**Limite și reguli de business**
- Persoane fizice: **max 2 anunțuri (animale) pe lună** – `POSTS_PER_MONTH_PF = 2` în settings
- Adoptator: angajament **6 luni** – poze/verificare; email automat la 3 sau 6 luni cu link formular verificare post-adopție

**Înregistrare / tip cont (3 categorii)**
- 1 = Persoană fizică (UserProfile)
- 2 = SRL / PFA / Asociație sau Fundație → sub-alegere SRL, PFA sau AF (OngProfile, grup „Asociație")
- 3 = ONG / Asociație de profil (OngProfile, grup „Asociație")

**Logare și URL-uri**
- Logare: `/cont/login/` (Django auth)
- Înregistrare: `/cont/inregistrare/`
- Cont PF: `/cont/profil/` (profil + verificare telefon SMS, 6 casete cod)
- Cont ONG/SRL/PFA/AF: `/cont/ong/`
- Adăugare animal PF: `/cont/adauga-animal/` (limitat 2/lună)
- Adăugare animal ONG: `/cont/ong/adauga/`

**Verificare telefon (persoană fizică)**
- La Cont → Profil: câmp Telefon + mesaj că se primește cod SMS; secțiune „Verificare telefon" cu **6 casete** pentru cod; buton Validare

**Verificare CUI/CIF**
- SRL/PFA: termene.ro, listafirme.ro
- ONG/AF: portal.just.ro (Registrul Național ONG)
- Comandă `verify_cui_members`; opțional `LISTAFIRME_API_KEY`

---

# Istoric Modificări

## Stabilizare Burtieră / Slider Pagină Principală (feb. 2026)

**Fișier:** `static/css/style.css`

**Motiv:** Burtiera (banda de poze de sus) nu avea poziție stabilă; după ce s-a scos/comportamentul s-a schimbat, pozele mișcau layout-ul.

**Ce s-a schimbat:**

1. **#slider_wrap**
   - Înainte: `height: auto;`
   - După: `width: 100%; min-height: 280px; aspect-ratio: 2880/1000; overflow: hidden;`
   - Efect: Zona slider-ului are înălțime rezervată și proporții stabile

2. **Container FlexSlider**
   - Adăugat: `#slider_wrap .flexslider` și `#slider_wrap .flex-viewport` cu `height: 100% !important; min-height: 280px;`

3. **Slide-uri**
   - `#slider_wrap .slides`: `height: 100% !important; min-height: 280px;`
   - `#slider_wrap .slide_image_wrap`: `height: 100%;`
   - `ul.slides`: din `height: 260px` în `min-height: 280px; height: 100%;`

4. **Imagini în slider**
   - `#slider_wrap img`: `width: 100%; height: 100%; display: block; object-fit: cover;`
   - Efect: Pozele umplu banda fără să deformeze și fără să miște layout-ul

## Logo Mutat în Hero (feb. 2026)

**Fișiere:** `templates/anunturi/home.html`, `static/css/style.css`

**Modificări:**
- Logo adăugat în containerul hero (`#slider_wrap`)
- Logo din header ascuns pe pagina home (`body.page-home #header .the_logo_link { display: none }`)
- Sigla rotundă cu stele păstrată în hero
- Texturi provizorii de identificare ("1home", "1animale", "1contact", "2contact") readuse pentru identificare

---

# Agenda Proiecte

## ⏰ MEMENTO – Diseară după 16:00

**Verifică Cloudflare + Render + eu-adopt.ro**

1. **Cloudflare** (https://dash.cloudflare.com) – dacă eu-adopt.ro e **Active** (verde)
2. **Render** → Custom Domains → apasă **Verify** la eu-adopt.ro și www.eu-adopt.ro
3. **Testează** https://eu-adopt.ro în browser

## 📋 Proiecte Active

| Proiect | Status | Note |
|---------|--------|------|
| EU Adopt (adoptapet_pro) | 🟢 Live | https://eu-adopt.onrender.com |

## 💻 Programe cu Care Lucrezi

| Program | Ce face | Link / Unde |
|---------|---------|-------------|
| **Cursor** | Editor de cod (IDE) | Deschis pe PC |
| **Python** | Limbajul aplicației | `python --version` |
| **Django** | Framework web | în proiect |
| **Git** | Versiune cod | `C:\Program Files\Git\bin\git.exe` |
| **GitHub** | Stocare cod online | https://github.com/rarespepsi/eu-adopt |
| **Render** | Hosting site + baza de date | https://dashboard.render.com |
| **PostgreSQL** | Baza de date (pe Render) | gestionat în Render |
| **PowerShell** | Terminal pentru comenzi | în Cursor sau Windows |
| **UptimeRobot** | Ține site-ul treaz (cold start) | https://uptimerobot.com |
| **Cloudinary** | Poze animale (nu se pierd la redeploy) | https://console.cloudinary.com |

## 🌐 Domenii

| Domeniu | Registrar / Unde | Data expirării | Note |
|---------|------------------|----------------|------|
| eu-adopt.ro | Hostico | _(completăază)_ | Toate domeniile cumpărate de la Hostico. Parolă ROTLD – păstrată în siguranță. De conectat la Render. |

## ✅ De Făcut (TODO)

- [ ] Configurare email principal (contact@eu-adopt.ro sau Gmail dedicat)
- [ ] Creare conturi social media cu același brand
- [ ] Conectare domeniu eu-adopt.ro la Render
- [ ] UptimeRobot configurat (dacă nu e deja)

## 📝 Notițe Libere

- Git pe Windows: calea completă `"C:\Program Files\Git\bin\git.exe"`
- Root Directory pe Render: `adoptapet_pro`
- Proiect local: `c:\Users\USER\Desktop\adoptapet_pro`
- **ROTLD** (pentru .ro): https://portal.rotld.ro – acolo setezi DNS-ul pentru eu-adopt.ro
- **DNS eu-adopt.ro (Render):** `www` CNAME → `eu-adopt.onrender.com` | `@` A record → `216.24.57.1`
- **Cloudinary:** CLOUDINARY_URL în Render Environment (pozele merg în cloud)
- **Start Command Render:** `gunicorn platforma.wsgi:application` (nu pune migrate/seed în Start – rulează în build)
- **Animale dispar:** build-ul rulează `seed_demo_pets`; dacă lipsesc, Manual Deploy din Render

---

# Reminder-uri

## ⏰ Reînnoire Domenii EU Adopt

**Reînnoiește domeniile până pe 15 ianuarie 2027**  
(expiră pe 14 februarie 2027)

### Domenii de Reînnoit:
- eu-adopt.ro
- eu-adopt.com
- eu-adopt.eu
- euadopt.com
- euadopt.org
- euadopt.eu
- euadopt.de
- euadopt.es
- euadopt.fr

### Cost Aproximativ: ~600 RON / an

---

## Punct de Întoarcere (Undo)

**Tag:** `undo-point-2026-02-17-2239`  
**Data și ora:** 17 februarie 2026, 22:39  
**Conține:** layout sidebars, paginare animale, signup→register, slot IDs.

### Dacă Mâine Ai Probleme și Vrei Să Revii La Acest Punct:

**Vedere rapidă (fără să ștergi nimic):**
```bash
cd c:\Users\USER\Desktop
git checkout undo-point-2026-02-17-2239
```
*(revino la branch-ul main după: `git checkout main`)*

**Resetare completă – proiectul devine exact ca la acest punct:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard undo-point-2026-02-17-2239
```
⚠️ Orice modificări făcute după acest tag se pierd.

**Listează toate tag-urile:**
```bash
git tag -l
```

---

# Istoric Conversații / Lucrări Făcute

## Logo și Stele

- **Stele**: 12 stele pe cerc, alternând galben (#FFD700) și albastru (#003399), formă cu 5 vârfuri.
- **Dimensiuni**: container 320px, imagine logo 229px, stele 260px.
- **SVG complet**: salvat în `static/images/eu-adopt-logo-complete.svg`

## Schema Site (Casute și Spații)

- **Rută**: `/schema-site/` (template: `templates/anunturi/schema-site.html`).
- **Conținut**: schelet vizual al paginilor, fără poze/logo, doar casute numerotate pentru postări (câini), spații pentru reclame, banner/burtiere.
- **Layout-uri reflectate**:
  - **Home**: 2×2 (4 casute).
  - **Animale**: 2×7 (2 linii × 7 coloane = 14 casute).
  - **Contact**: conținut + sidebar reclame.
  - **Detalii animal**: detalii + formulare + sidebar.

## Fișiere Importante Modificate

| Fișier | Modificări / Rol |
|--------|-------------------|
| `static/css/style.css` | Toate stilurile logo (inclusiv Contact), stele, texturi provizorii, grid-uri. |
| `templates/anunturi/contact.html` | Logo șters din header; două logo-uri în conținut. |
| `templates/anunturi/home.html` | Clasă `page-home`, logo în hero. |
| `templates/anunturi/pets-all.html` | Burtieră mică, clasă `page-animale`. |
| `templates/anunturi/schema-site.html` | Pagina de schemă (casute + reclame). |
| `anunturi/views.py` | `pets_all` cu `strip_pets`; view pentru schema. |
| `anunturi/urls.py` | Rută `schema-site/`. |
| `SETARI_LOGO.md` | Documentație setări logo. |
| `static/images/eu-adopt-logo-complete.svg` | Logo complet (stele + referință imagine). |

---

*Document creat: februarie 2026. Păstrează acest fișier în proiect și actualizează-l când faci modificări sau când site-ul merge și vrei să salvezi starea.*
