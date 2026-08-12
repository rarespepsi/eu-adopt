# Backup & rollback — EU-Adopt

**Procedură agent (obligatorie, always-on):** `.cursor/rules/BACKUP_DEPLOY_PROCEDURA.mdc`

Două rotații automate câte **3 variante** (la a 4-a se șterge cea mai veche).

---

## 0. Versiune „site funcțional” (regula de aur)

**Pointer operațional pe Hetzner:** `/var/lib/euadopt/EXPECTED_RELEASE.txt`  
**Copie în repo:** `deploy/EXPECTED_RELEASE.txt`

- Se **actualizează automat** după `deploy_update.sh` dacă smoke + Maps trec.
- Healthcheck **3×/zi** (06/14/22 Europe/Bucharest) compară live cu acest SHA.
- La FAIL → **rollback** la SHA din EXPECTED (nu inventează fix-uri) + email `rarespepsi@gmail.com`.
- Undo: `bash /opt/eu-adopt/deploy/hetzner/undo_last_auto_repair.sh`
- State: `/var/lib/euadopt/AUTO_REPAIR_STATE.json`
- Log: `/var/log/euadopt-healthcheck.log`
- Instalare cron: `bash /opt/eu-adopt/deploy/hetzner/install_site_healthcheck_cron.sh`

---

## 1. Copii „bune” pe PC (cod)

**Script:** `scripts/backup_good_release_rotate.ps1`

- Creează ZIP din `git archive` (doar fișiere urmărite, fără `venv` / `db.sqlite3`)
- Nume: `good_YYYYMMDD_HHMMSS_<sha>.zip` + fișier `.txt` cu commit
- Implicit: `%USERPROFILE%\Desktop\EU-Adopt-backups\good-releases`
- Păstrează **3** arhive; șterge automat restul

```powershell
cd "C:\Users\USER\Desktop\euadopt_final8martie_P2stabilizat 4x3"
.\scripts\backup_good_release_rotate.ps1
```

Parametri opționali: `-Keep 3`, `-BackupRoot "D:\Backups\eu-adopt"`.

**Restore (doar cod):** dezarhivezi ZIP-ul într-un folder nou sau `git checkout <sha>` din repo.

---

## 2. Backup PostgreSQL pe Hetzner (bază)

**Script:** `deploy/hetzner/backup_db_rotate.sh`

- Dump: `pg_dump -Fc` → `/var/backups/euadopt/euadopt_YYYYMMDD_HHMMSS.dump`
- Păstrează **3** dump-uri; șterge automat restul
- Variabile: `EUADOPT_DB_BACKUP_KEEP`, `EUADOPT_DB_BACKUP_DIR`, `EUADOPT_DB_NAME`

```bash
# pe server (root)
bash /opt/eu-adopt/deploy/hetzner/backup_db_rotate.sh
```

**Cron zilnic (opțional, 03:00):**

```bash
bash /opt/eu-adopt/deploy/hetzner/install_db_backup_cron.sh
```

**Restore DB (urgență):**

```bash
systemctl stop euadopt
sudo -u postgres dropdb euadopt
sudo -u postgres createdb -O euadopt euadopt
sudo -u postgres pg_restore -d euadopt /var/backups/euadopt/euadopt_YYYYMMDD_HHMMSS.dump
systemctl start euadopt
```

---

## 3. Deploy automat din PC (ambele + update server)

**Script:** `scripts/deploy_hetzner_from_pc.ps1`

1. Copie bună locală (rotație 3)  
2. SSH: backup DB (rotație 3) → `git pull` → `migrate` → `collectstatic` → `restart euadopt`

```powershell
.\scripts\deploy_hetzner_from_pc.ps1
```

Fără ZIP local: `-SkipLocalBackup`

---

## 4. Niveluri de rollback (cascadă)

| Pas | Ce faci | Pierderi date |
|-----|---------|----------------|
| **A** | Pe H: `git checkout <sha_bun>` + `collectstatic` + `restart` | minime (dacă fără migrare rea) |
| **B** | Restore dump DB + checkout același SHA | date după momentul dump-ului |
| **C** | Snapshot VPS Hetzner | tot de la snapshot |

Dump-ul din `deploy_update.sh` / `deploy_hetzner_from_pc.ps1` rulează **înainte** de `git pull` → punct de restore chiar înainte de deploy.

---

## 5. După `git push`

Fără script PC, pe server:

```bash
bash /opt/eu-adopt/deploy/hetzner/deploy_update.sh
```

Sau flux complet din PC: `.\scripts\deploy_hetzner_from_pc.ps1`
