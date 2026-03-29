# EU-Adopt — checklist pre-lansare (închis punct cu punct)

**Ultima actualizare în repo:** pagini 404/500, `SECRET_KEY` + HTTPS opțional din env, `.env.example`; teste Django **129 OK**; Playwright **11/11** cu variabile E2E (rulare locală).

**Legendă stare**

| Cod | Semnificație |
|-----|----------------|
| **1 — REZOLVAT în repo** | Făcut în cod / verificat cu comenzi în dev |
| **2 — DE VERIFICAT MANUAL de tine** | Browser, conținut, decizii business |
| **3 — NECESITĂ ACCES / DATE REALE / SERVER** | Producție, SMTP, backup, domeniu — nu din repo |
| **4 — OPȚIONAL DUPĂ LANSARE** | Îmbunătățiri, nu blocante |

---

## Închidere pe puncte (lista practică)

### Suite automate

| Punct | Stare | Note |
|-------|--------|------|
| `python manage.py test` verde | **1** | Verificat: **129 teste OK** pe branch curent. **Tu:** rulează din nou înainte de tag release. |
| `npm run test:e2e` → 11 passed, 0 skipped | **1** | Verificat cu `e2e/create_e2e_users.py` + env din `e2e/README.md`. **Tu:** repetă pe mașina de build cu server pornit. |
| Acoperire minimă E2E (navbar, PT, servicii, transport, signup, auth, restricții, publicitate) | **1** | Spec-urile din `e2e/` acoperă fluxurile listate. |

### Verificări manuale (înainte de go-live)

| Punct | Stare | Ce faci tu (scurt) |
|-------|--------|---------------------|
| Înregistrare / login PF, ONG, colaborator | **2** | Parcurgi o dată fiecare tip de cont pe **staging/prod**; notezi erori 500. |
| Publicare anunț (câine / pisică / altele) vizibil pe PT + fișă | **2** | Postezi un anunț test și verifici listă + `/pets/<id>/`. |
| MyPet proprietar (editare, mesaje, stări adopție) | **2** | Un flux scurt cu cont real de test. |
| Servicii + oferte colaboratori (filtre, claim) | **2** dacă modulul e live; altfel **4** | Doar dacă îl folosiți activ. |
| Transport + eventual panou operator | **2** | Trimite o cerere; dacă aveți dispecerat, un tur rapid. |
| Publicitate (flux până la coș; plată reală doar dacă e cazul) | **2** + **3** pentru plată | Test pe staging; **card live** = doar cu chei de producție pe server. |
| Admin Django: acces restricționat, URL neexpus | **2** + **3** | Verifici cine are staff; pe **server**: firewall / IP allowlist dacă e politica voastră. |
| Pagini eroare fără stack pentru utilizatori | **1** + **3** | **1:** există `templates/404.html`, `templates/500.html`; cu `DEBUG=False` utilizatorul nu vede traceback. **3:** pe prod setezi `DJANGO_DEBUG` neactiv/fals și `collectstatic`. |
| Legal: Termeni, Contact, politici, cookie | **2** | Citești linkurile din footer; actualizezi textele dacă e cazul (conținut). |
| Pagini înghețate / layout (HOME, PT, Shop…) | **2** | Smoke vizual după deploy: compară cu referința voastră. |

### Config producție

| Punct | Stare | Ce faci tu / unde |
|-------|--------|---------------------|
| `DEBUG=False` pe live | **3** | Variabile pe host (ex. Render): **nu** seta `DJANGO_DEBUG=1`. |
| `SECRET_KEY` unic, secret | **1** + **3** | **1:** `settings` citește `DJANGO_SECRET_KEY`; vezi `.env.example`. **3:** generezi cheie și o pui în env **producție** (niciodată în git). |
| HTTPS + domeniu + `ALLOWED_HOSTS` | **3** | Certificat + DNS la provider; lista din `settings` include deja `eu-adopt.ro` — verifici că domeniul real e acoperit. |
| Cookie-uri secure / redirect SSL | **1** + **3** | **1:** dacă setezi `DJANGO_SECURE_SSL=1`, se activează HSTS + `SESSION_COOKIE_SECURE` etc. **3:** pornește **după** ce HTTPS merge (evită loop local). |
| Email SMTP real | **3** | Pui `EMAIL_HOST_PASSWORD` (parolă aplicație Gmail) în env pe server; testezi „reset parolă”. |
| Static + `collectstatic` + media | **3** | Pe deploy: `collectstatic`; volume sau S3 pentru media după cum aveți. |
| Migrări pe DB producție | **3** | `migrate` pe backup + plan de rollback. |
| Backup DB periodic + restore testat | **3** | Cron / serviciu host; o dată restaurezi într-un mediu gol. |
| Rate limiting / anti-bruteforce | **3** sau **4** | La CDN (Cloudflare) sau middleware; opțional la început dacă trafic mic. |
| Plăți (dacă există) | **3** | Chei live, webhook, URL-uri — doar pe server secrete. |

### Opțional după lansare

| Punct | Stare |
|-------|--------|
| Lighthouse, CDN, timpi | **4** |
| Safari/Firefox/mobil (în afara Chromium E2E) | **4** |
| Flux adopție cap-coadă + email/SMS real | **4** (sau **2** când prioritate) |
| Seed conținut / imagini inițiale | **4** dacă aveți deja date; altfel **2** la primul gol |

---

## Comenzi de referință

```bash
python manage.py test
```

```powershell
python e2e/create_e2e_users.py
$env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:8000"
$env:E2E_USER_EMAIL = "e2e_pf@test.local"
$env:E2E_USER_PASSWORD = "E2E_Test_Pass12!"
$env:E2E_PUB_EMAIL = "e2e_staff@test.local"
$env:E2E_PUB_PASSWORD = "E2E_Staff_Pass12!"
# alt terminal: python manage.py runserver 127.0.0.1:8000
npm run test:e2e
```

---

## Ce mai rămâne doar pe tine (rezumat)

1. **Manual (2):** fluxuri cont, anunț, MyPet, servicii/transport/publicitate după caz, legal, smoke vizual pagini cheie, admin.  
2. **Server / date reale (3):** env producție (`DJANGO_SECRET_KEY`, fără DEBUG, SMTP, `DJANGO_SECURE_SSL` după HTTPS), migrări, backup, plăți, hardening la host.  
3. **Opțional (4):** performanță, browsere extra, conținut inițial dacă nu e urgent.

După ce (2) și (3) sunt bifate pentru mediul vostru real, checklistul e **închis** pentru lansare.
