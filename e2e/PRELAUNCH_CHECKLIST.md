# EU-Adopt — checklist pre-lansare (teste automate + verificări manuale)

Acest document rezumă ce acoperă deja suitele **Django** și **Playwright** și ce merită verificat manual înainte de producție.

---

## 1. Ce rulezi înainte de lansare (automat)

### Django (`python manage.py test`)

| Zonă indicativă | Fișiere / suite |
|-----------------|-----------------|
| Permisiuni, fluxuri, formulare, auth | `home/tests/test_permissions.py`, `test_flows.py`, `test_forms.py`, `test_auth.py` |
| Smoke / încărcare pagini | `home/tests/test_smoke.py` |
| „Carte” funcționalități (domeniu mare) | `test_carte_21_135.py`, `test_carte_30_40.py`, `test_carte_41_60.py`, `test_carte_61_100.py`, `test_carte_pf_flow.py`, `test_carte_bulk.py` |

**Comandă:** din rădăcina proiectului, cu mediul Django activ și dependențe instalate:

```bash
python manage.py test
```

Rezolvă orice eșec înainte de considera lansarea „închisă” din punct de vedere backend.

### Playwright (E2E browser)

**Pregătire:** `npm install`, `npx playwright install chromium`, useri E2E în DB (`python e2e/create_e2e_users.py`), cel puțin un animal publicat pe `/pets/` dacă vrei fișă reală (DB de dev).

**11/11 teste (fără skip):** setează toate variabilele și rulează:

```powershell
cd <rădăcina_proiectului>
python e2e/create_e2e_users.py
$env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:8000"
$env:E2E_USER_EMAIL = "e2e_pf@test.local"
$env:E2E_USER_PASSWORD = "E2E_Test_Pass12!"
$env:E2E_PUB_EMAIL = "e2e_staff@test.local"
$env:E2E_PUB_PASSWORD = "E2E_Staff_Pass12!"
# Terminal separat: python manage.py runserver 127.0.0.1:8000
npm run test:e2e
```

| Spec | Ce verifică (pe scurt) |
|------|-------------------------|
| `navigation.spec.js` | Navbar: Acasă, Prietenul tău, Servicii, Transport, Shop, Contact, Termeni |
| `pet-detail.spec.js` | Card PT → fișă; DISTRIBUIE, QR, stare adopție (vizitator anonim) |
| `servicii.spec.js` | Pagina Servicii se încarcă (S1) |
| `transport.spec.js` | Formular cerere transport (submit + mesaj confirmare) |
| `signup.spec.js` | Pagină signup PF + validări la submit incomplet |
| `auth.spec.js` | Login → cont → logout |
| `access-restricted.spec.js` | Redirect login pentru cont/MyPet/publicitate; anonim la `/admin-analysis/` → Acasă |
| `publicitate.spec.js` | Anonim → login; staff/colab → hartă PUB, coș, adăugare slot |

---

## 2. Ce nu e (de obicei) acoperit automat sau e parțial

- **Producție reală:** HTTPS, domeniu, `ALLOWED_HOSTS`, `SECRET_KEY`, email SMTP real, plăți (dacă există), rate limiting, backup DB.
- **Conținut și date:** seed producție, imagini, texte legale finale, GDPR/termeni actualizați.
- **Performanță și încărcare:** Lighthouse, timpi sub trafic, CDN pentru static/media.
- **Compatibilitate browser:** Playwright folosește Chromium; Safari/Firefox/Edge mobile — verificare manuală sau proiecte Playwright adiționale.
- **Fluxuri lungi:** adopție cap-coadă cu emailuri reale, SMS, colaboratori, transport dispecerat — doar dacă există teste dedicate în Django; altfel manual.
- **Pagini „înghețate” în proiect (HOME, PT, Shop etc.):** nu se schimbă fără proces; la lansare se verifică că build-ul afișează versiunea așteptată.

---

## 3. Verificări manuale recomandate (scurt checklist)

- [ ] **Înregistrare / login** PF, ONG, colaborator (dacă sunt live) — fără erori 500.
- [ ] **Publicare anunț** câine/pisică/altele → vizibil pe PT și fișă publică.
- [ ] **MyPet** proprietar: editare, mesaje (dacă folosiți), adopție (stări).
- [ ] **Servicii / oferte colaboratori** (dacă aplicabil): filtre, claim, expirare.
- [ ] **Transport:** cerere și (dacă există) flux operator.
- [ ] **Publicitate:** comandă test (sau staging) fără card real dacă e integrat plata.
- [ ] **Admin Django** pe producție: acces doar staff, `DEBUG=False`.
- [ ] **404/500** personalizate, fără stack trace la utilizatori.
- [ ] **Legal:** link Termeni/Contact/Politici corecte; cookie banner dacă e obligatoriu.

---

## 4. Rezumat „mai lipsește înainte de lansare?”

1. **Django `test` verde** pe branch-ul de release.
2. **Playwright 11/11** cu variabilele E2E setate și useri creați în DB-ul folosit la test.
3. **Config producție** (setări, secrete, static, migrări aplicate).
4. **Verificări manuale** din secțiunea 3, adaptate la ce e activ pe site-ul vostru.

Dacă un punct din 1–2 pică, tratați-l ca blocant înainte de go-live.
