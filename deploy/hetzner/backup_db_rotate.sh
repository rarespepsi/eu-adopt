#!/usr/bin/env bash
# PostgreSQL dump cu rotație: păstrează ultimele KEEP fișiere.
# Rulează pe Hetzner (root): bash /opt/eu-adopt/deploy/hetzner/backup_db_rotate.sh
# Opțional cron zilnic: 0 3 * * * /opt/eu-adopt/deploy/hetzner/backup_db_rotate.sh >> /var/log/euadopt-db-backup.log 2>&1

set -euo pipefail

KEEP_RAW="${EUADOPT_DB_BACKUP_KEEP:-3}"
KEEP="${KEEP_RAW//$'\r'/}"
if [[ ! "${KEEP}" =~ ^[0-9]+$ ]]; then
  KEEP=3
fi
BACKUP_DIR="${EUADOPT_DB_BACKUP_DIR:-/var/backups/euadopt}"
DB_NAME="${EUADOPT_DB_NAME:-euadopt}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/euadopt_${STAMP}.dump"

mkdir -p "${BACKUP_DIR}"
chown root:postgres "${BACKUP_DIR}" 2>/dev/null || true
chmod 750 "${BACKUP_DIR}" 2>/dev/null || true

echo "[$(date -Is)] pg_dump ${DB_NAME} -> ${OUT}"
sudo -u postgres pg_dump -Fc "${DB_NAME}" > "${OUT}"
chmod 640 "${OUT}"
chown root:postgres "${OUT}" 2>/dev/null || true

# Șterge dump-urile mai vechi decât ultimele KEEP (sortare după timp modificare).
mapfile -t ALL < <(ls -1t "${BACKUP_DIR}"/euadopt_*.dump 2>/dev/null || true)
if ((${#ALL[@]} > KEEP)); then
  for ((i = KEEP; i < ${#ALL[@]}; i++)); do
    echo "[$(date -Is)] Șterg backup vechi: ${ALL[$i]}"
    rm -f "${ALL[$i]}"
  done
fi

mapfile -t LEFT < <(ls -1t "${BACKUP_DIR}"/euadopt_*.dump 2>/dev/null || true)
echo "[$(date -Is)] Păstrate ${#LEFT[@]} / ${KEEP}:"
for f in "${LEFT[@]}"; do
  echo "  - $(basename "$f")"
done
