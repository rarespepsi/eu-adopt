# Fișiere legate de baza de date (EU-ADOPT)

Aici păstrăm **local** copii și exporturi legate de DB, ca să le aveți la îndemână (backup înainte de migrări, export înainte de import masiv, etc.).

## Structură

| Folder / fișier | Rol |
|------------------|-----|
| **`backups/`**   | Copii ale bazei (ex. `db.sqlite3` copiat, dump SQL). **Nu se urcă pe git** — pot conține date personale. Folderul există în repo (`.gitkeep`); fișierele tale rămân doar local. |
| **`exports/`**   | Opțional: exporturi CSV/SQL mici, scripturi de notă. Puteți versiona sau ignora după preferință. |

După fiecare rulare reușită a `python manage.py import_prospecte_csv --path …/fișier.csv`, lângă CSV apare automat **`fișier.csv.imported`** (text) — semn că acel CSV a fost trecut prin import (data, număr rânduri, `created_by`).

## Convenție de nume (recomandat)

```
YYYY-MM-DD_scurt_descriere.ext
```

Exemple:

- `2026-05-12_inainte_import_adaposturi.sqlite3`
- `2026-05-12_prospecte_export.csv`

## Unde e baza „live” a aplicației

- **Local (tipic):** fișierul `db.sqlite3` în **rădăcina proiectului** (un nivel mai sus decât acest folder `database/`). Acela e DB-ul pe care îl folosește Django la rulare.
- **Producție:** PostgreSQL sau alt server — vezi `DATABASE_URL` / setările din `.env` (nu comiteți `.env`).

## Ce să puneți aici la fiecare operație importantă

1. **Înainte de migrare Django** (`migrate`) sau import masiv: copie `db.sqlite3` → `database/backups/`.
2. **După import CSV prospecte:** opțional export din Add USER sau copie DB.
3. **Dump SQL** (dacă folosiți `pg_dump` / `sqlite3 .dump`): tot în `backups/`.

## Git

- Fișierele din **`database/backups/`** (în afară de `.gitkeep`) sunt **ignorate** de git.
- **`database/exports/`** — poți versiona exporturi mici sau adăuga reguli în `.gitignore` dacă nu vrei în repo.
- **`database/README.md`** rămâne în repo ca **documentație** pentru echipă.
