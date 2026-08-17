#!/usr/bin/env bash
# Poll IMAP Zoho — bounce / răspuns / opt-out invitații Add USER.
# Cron: la fiecare 30 min. Backlog one-shot: EUADOPT_INVITE_IMAP_BACKLOG=1
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
LOG="${EUADOPT_INVITE_IMAP_LOG:-/var/log/euadopt-invite-imap.log}"
LOCK="/var/lock/euadopt-invite-imap.lock"
TIMEOUT_SEC="${EUADOPT_INVITE_IMAP_TIMEOUT:-600}"
MAX_MSG="${EUADOPT_INVITE_IMAP_MAX:-80}"
BACKLOG="${EUADOPT_INVITE_IMAP_BACKLOG:-0}"
SINCE_DAYS="${EUADOPT_INVITE_IMAP_SINCE_DAYS:-60}"

mkdir -p "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: invite IMAP poll deja în curs" >> "${LOG}"
  exit 0
fi

{
  echo "=== $(date -Iseconds) invite IMAP poll START backlog=${BACKLOG} max=${MAX_MSG} ==="
  if ! cd "${APP_DIR}"; then
    echo "FAIL: nu pot intra în ${APP_DIR}"
    echo "=== $(date -Iseconds) invite IMAP poll END exit=2 ==="
    exit 2
  fi
  export PYTHONUNBUFFERED=1
  if [[ "${BACKLOG}" == "1" ]]; then
    INNER="source venv/bin/activate && python -u manage.py staff_invite_poll_inbox --bounce-backlog --max ${MAX_MSG} --since-days ${SINCE_DAYS}"
  else
    INNER="source venv/bin/activate && python -u manage.py staff_invite_poll_inbox --max ${MAX_MSG}"
  fi
  if command -v timeout >/dev/null 2>&1; then
    timeout --signal=TERM --kill-after=30 "${TIMEOUT_SEC}" \
      sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c "${INNER}"
    ec=$?
  else
    sudo -u euadopt env PYTHONUNBUFFERED=1 bash -c "${INNER}"
    ec=$?
  fi
  if [[ "${ec}" -eq 124 ]]; then
    echo "FAIL: timeout ${TIMEOUT_SEC}s"
  elif [[ "${ec}" -ne 0 ]]; then
    echo "FAIL: exit=${ec}"
  fi
  echo "=== $(date -Iseconds) invite IMAP poll END exit=${ec} ==="
  exit "${ec}"
} >> "${LOG}" 2>&1
