# Teste end-to-end (Playwright) — EU-Adopt

## Pregătire

1. Instalare dependențe (o dată):

```bash
npm install
npx playwright install chromium
```

2. Pornește Django **într-un terminal separat**:

```bash
python manage.py runserver
```

3. Opțional — variabile de mediu (în PowerShell exemplu):

```text
$env:E2E_USER_EMAIL="user@test.local"
$env:E2E_USER_PASSWORD="parolaTa"
$env:E2E_PUB_EMAIL="colab@test.local"
$env:E2E_PUB_PASSWORD="parolaColab"
```

- **E2E_USER_*** — user normal (non-staff), pentru `auth.spec.js` și `access-restricted.spec.js` (ultimul test).
- **E2E_PUB_*** — cont **colaborator** sau **staff** (acces `/publicitate/`), pentru fluxul complet publicitate.

Alt URL decât local:

```text
$env:PLAYWRIGHT_BASE_URL="http://127.0.0.1:8000"
```

## Rulare

```bash
npm run test:e2e
```

UI interactiv:

```bash
npm run test:e2e:ui
```

## Ce nu e acoperit fără date reale

- Testele care depind de **animale publicate** pe `/pets/` presupun că există cel puțin un card în grid (DB de dev cu date).
- Fluxul publicitate complet **sare** dacă nu setezi `E2E_PUB_EMAIL` / `E2E_PUB_PASSWORD`.
