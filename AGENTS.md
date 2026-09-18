# AGENTS.md

## Cursor Cloud specific instructions

EU-Adopt is a single Django 6 project (`euadopt_final`) with one main app (`home`). It is a
Romanian pet-adoption platform. There is no Celery/Redis; background work is done via management
commands + cron. A small Node/Playwright setup exists for optional E2E tests only.

### Environment / how things run

- Python deps live in a virtualenv at `.venv` (created by the startup update script). Always call
  Python via `.venv/bin/python` (e.g. `.venv/bin/python manage.py ...`) — the system `python3`
  does not have the dependencies.
- The database defaults to **SQLite** (`db.sqlite3`) when `DATABASE_URL` is unset (production uses
  PostgreSQL). No external DB service is needed for local dev.
- A dev `.env` is used locally (git-ignored). The important setting is `DJANGO_DEBUG=1`: with
  `DEBUG=False` (the default) Django enables `SECURE_SSL_REDIRECT` and secure cookies, which makes
  plain-HTTP local testing redirect to HTTPS and appear broken. Keep `DJANGO_DEBUG=1` for local dev.
  If `.env` is missing, recreate it with at least `DJANGO_DEBUG=1`.
- Email uses the console backend when SMTP is unconfigured (activation/reset links print to the
  server console). SMS OTP is disabled by default (`EUADOPT_SMS_OTP_ENABLED=0`) and shows a fixed
  dev code `528419` on screen instead of sending a real SMS.

### Run / lint / test / build

- Run dev server: `.venv/bin/python manage.py runserver 127.0.0.1:8000` (see also `run_dev_server.bat`).
- Lint / system check: `.venv/bin/python manage.py check` (deploy checks: `manage.py check --deploy`).
- Migrations: `.venv/bin/python manage.py migrate`.
- Static (prod-only): `.venv/bin/python manage.py collectstatic` — not needed for dev (WhiteNoise +
  DEBUG serve static automatically).
- E2E tests (optional): server must already be running, then
  `.venv/bin/python e2e/create_e2e_users.py` and run Playwright per `e2e/README.md`
  (`PLAYWRIGHT_BASE_URL`, `E2E_USER_*`, `E2E_PUB_*` env vars, then `npm run test:e2e`). Browser is
  installed via `npx playwright install chromium`.

### Gotchas

- Several E2E specs (`pet-detail.spec.js`, `pt-mobile-portrait.spec.js`) and some `publicitate`
  assertions require **seed data** (at least one published pet / offer). On a fresh empty DB they
  fail by design, not because of an environment problem — see `e2e/README.md`. Auth/access specs
  pass on an empty DB.
- Deployment is Hetzner-only (`deploy/hetzner/`); Render is abandoned. Do not run deploy scripts
  from the cloud agent.
