# Teste end-to-end (Playwright) — EU-Adopt

## Pregătire

1. Instalare dependențe (o dată):

```bash
npm install
npx playwright install chromium
```

2. **Useri pentru 11/11 teste (fără skip)** — din rădăcina proiectului:

```bash
python e2e/create_e2e_users.py
```

Asta creează (dacă lipsesc) `e2e_pf` (user normal) și `e2e_staff` (staff, pentru publicitate). Parolele implicite sunt cele tipărite la finalul scriptului.

3. Pornește Django **într-un terminal separat**:

```bash
python manage.py runserver 127.0.0.1:8000
```

4. **Variabile de mediu** — pentru **toate** testele, inclusiv cele care altfel sunt *skipped*:

**PowerShell:**

```powershell
$env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:8000"
$env:E2E_USER_EMAIL = "e2e_pf@test.local"
$env:E2E_USER_PASSWORD = "E2E_Test_Pass12!"
$env:E2E_PUB_EMAIL = "e2e_staff@test.local"
$env:E2E_PUB_PASSWORD = "E2E_Staff_Pass12!"
npm run test:e2e
```

- **E2E_USER_*** — user **non-staff** (`auth.spec.js`, test admin-analysis din `access-restricted.spec.js`).
- **E2E_PUB_*** — cont **staff** sau colaborator cu acces `/publicitate/` (`publicitate.spec.js` flux complet).

**Bash:**

```bash
export PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000
export E2E_USER_EMAIL=e2e_pf@test.local
export E2E_USER_PASSWORD='E2E_Test_Pass12!'
export E2E_PUB_EMAIL=e2e_staff@test.local
export E2E_PUB_PASSWORD='E2E_Staff_Pass12!'
npm run test:e2e
```

## Rulare

```bash
npm run test:e2e
```

UI interactiv:

```bash
npm run test:e2e:ui
```

## Rezultat așteptat

Cu serverul pornit și cele patru perechi de variabile setate (`PLAYWRIGHT_BASE_URL` + `E2E_USER_*` + `E2E_PUB_*`), raportul Playwright ar trebui să arate **11 trecute, 0 sărite** (11/11).

## Date în DB

- Testele care deschid `/pets/` și o fișă presupun **cel puțin un animal publicat** în grila PT (altfel poți vedea doar demo). Pentru mediu gol, adaugă un anunț publicat de test sau folosește un DB de dev cu date.
- Checklist pre-lansare (Django + Playwright + manual): vezi **`PRELAUNCH_CHECKLIST.md`** în acest folder.

## Ce nu e acoperit fără date reale

- Fluxuri care depind de oferte colaboratori, plăți reale sau email SMTP de producție — în plus față de ce e în spec-uri.
