#!/usr/bin/env bash
# Healthcheck 3×/zi: smoke + Maps tests + SHA vs EXPECTED_RELEASE.
# La FAIL: rollback la SHA bun (fără fix inventat) + email + flag undo.
#   bash /opt/eu-adopt/deploy/hetzner/run_site_healthcheck.sh
#   EUADOPT_HEALTHCHECK_AUTO_REPAIR=0 bash ...  # doar alertă, fără rollback
set -uo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
STATE_DIR="${EUADOPT_STATE_DIR:-/var/lib/euadopt}"
EXPECTED="${EUADOPT_EXPECTED_RELEASE:-${STATE_DIR}/EXPECTED_RELEASE.txt}"
STATE_JSON="${STATE_DIR}/AUTO_REPAIR_STATE.json"
LAST_JSON="${STATE_DIR}/last_healthcheck.json"
LOG="${EUADOPT_HEALTHCHECK_LOG:-/var/log/euadopt-healthcheck.log}"
LOCK="/var/lock/euadopt-healthcheck.lock"
PY="${APP_DIR}/deploy/hetzner/site_healthcheck.py"
AUTO_REPAIR="${EUADOPT_HEALTHCHECK_AUTO_REPAIR:-1}"
ALERT_TO="${EUADOPT_HEALTHCHECK_EMAIL:-rarespepsi@gmail.com}"

mkdir -p "${STATE_DIR}" "$(dirname "${LOG}")" /var/lock 2>/dev/null || true
# euadopt trebuie să poată scrie last_healthcheck.json
chgrp euadopt "${STATE_DIR}" 2>/dev/null || true
chmod 775 "${STATE_DIR}" 2>/dev/null || true
touch "${LOG}"
chmod 644 "${LOG}" 2>/dev/null || true

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "$(date -Iseconds) SKIP: healthcheck deja în curs" >> "${LOG}"
  exit 0
fi

log() { echo "$(date -Iseconds) $*" | tee -a "${LOG}"; }

send_mail_django() {
  local subject="$1"
  local body_file="$2"
  # body trebuie citibil de userul euadopt
  chmod 644 "${body_file}" 2>/dev/null || true
  chown root:euadopt "${body_file}" 2>/dev/null || true
  sudo -u euadopt bash -lc "cd '${APP_DIR}' && source venv/bin/activate && python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'euadopt_final.settings')
import django
django.setup()
from django.conf import settings
from django.core.mail import send_mail
from pathlib import Path
subject = '''${subject}'''
body = Path('''${body_file}''').read_text(encoding='utf-8', errors='replace')
to = '''${ALERT_TO}'''
frm = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip() or 'noreply@eu-adopt.ro'
send_mail(subject, body, frm, [to], fail_silently=False)
print('email_ok', to)
PY"
}

read_expected_sha() {
  if [[ ! -f "${EXPECTED}" ]]; then
    echo ""
    return
  fi
  grep -E '^SHA=' "${EXPECTED}" | head -1 | cut -d= -f2- | tr -d '\r'
}

write_repair_state() {
  local reason="$1"
  local before="$2"
  local after="$3"
  local ok_after="$4"
  cat > "${STATE_JSON}" <<EOF
{
  "repaired_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "reason": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "${reason}"),
  "sha_before": "${before}",
  "sha_after": "${after}",
  "smoke_after_ok": ${ok_after},
  "undo": "bash ${APP_DIR}/deploy/hetzner/undo_last_auto_repair.sh"
}
EOF
  chmod 644 "${STATE_JSON}" 2>/dev/null || true
}

do_rollback() {
  local target_sha="$1"
  local before_sha
  before_sha="$(sudo -u euadopt git -C "${APP_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
  log "ROLLBACK begin before=${before_sha} target=${target_sha}"
  if [[ -z "${target_sha}" ]]; then
    log "ROLLBACK abort: empty target SHA"
    return 2
  fi
  sudo -u euadopt bash -lc "
    set -e
    cd '${APP_DIR}'
    # rollback pe detached HEAD rupe `git pull` la următorul deploy — rămâi pe main
    git fetch --quiet origin || true
    git checkout -B main --track origin/main 2>/dev/null || git checkout -B main
    git reset --hard '${target_sha}'
    source venv/bin/activate
    python manage.py collectstatic --noinput >/dev/null
  "
  systemctl restart euadopt
  sleep 2
  systemctl is-active --quiet euadopt || return 3
  log "ROLLBACK done now=$(sudo -u euadopt git -C "${APP_DIR}" rev-parse --short HEAD)"
  return 0
}

{
  echo "=== $(date -Iseconds) site_healthcheck START ==="
  export EUADOPT_APP_DIR="${APP_DIR}"
  export EUADOPT_EXPECTED_RELEASE="${EXPECTED}"
  export EUADOPT_HEALTHCHECK_LAST_JSON="${LAST_JSON}"
  export EUADOPT_HEALTHCHECK_BASE_URL="${EUADOPT_HEALTHCHECK_BASE_URL:-https://eu-adopt.ro}"
  export EUADOPT_HEALTHCHECK_EMAIL="${ALERT_TO}"

  # Seed EXPECTED from live HEAD if missing (nu copia din repo — poate fi SHA vechi)
  if [[ ! -f "${EXPECTED}" ]]; then
    bash "${APP_DIR}/deploy/hetzner/mark_expected_release.sh" "seed on first healthcheck"
    log "seeded EXPECTED from live HEAD"
  fi

  svc_ok=1
  if systemctl is-active --quiet euadopt; then
    log "service=active"
  else
    log "service=INACTIVE — attempting restart"
    systemctl restart euadopt || true
    sleep 2
    if systemctl is-active --quiet euadopt; then
      log "service=restarted_ok"
    else
      svc_ok=0
      log "service=still_down"
    fi
  fi

  REPORT="$(mktemp "${STATE_DIR}/hc_report.XXXXXX")"
  chmod 644 "${REPORT}" 2>/dev/null || true
  HC_EC=0
  if [[ "${svc_ok}" -ne 1 ]]; then
    echo "FAIL: systemd euadopt not active" > "${REPORT}"
    HC_EC=1
  else
    # rulează checker-ul ca root dar maps tests via sudo în python — mai simplu: tot via sudo euadopt unde se poate
    if ! sudo -u euadopt env \
      EUADOPT_APP_DIR="${APP_DIR}" \
      EUADOPT_EXPECTED_RELEASE="${EXPECTED}" \
      EUADOPT_HEALTHCHECK_LAST_JSON="${LAST_JSON}" \
      EUADOPT_HEALTHCHECK_BASE_URL="${EUADOPT_HEALTHCHECK_BASE_URL:-https://eu-adopt.ro}" \
      bash -lc "cd '${APP_DIR}' && source venv/bin/activate && python '${PY}' check" \
      > "${REPORT}" 2>&1
    then
      HC_EC=1
    fi
  fi
  cat "${REPORT}" >> "${LOG}"

  if [[ "${HC_EC}" -eq 0 ]]; then
    log "result=OK"
    echo "=== $(date -Iseconds) site_healthcheck END exit=0 ==="
    rm -f "${REPORT}"
    exit 0
  fi

  log "result=FAIL auto_repair=${AUTO_REPAIR}"
  TARGET="$(read_expected_sha)"
  BEFORE="$(sudo -u euadopt git -C "${APP_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"

  if [[ "${AUTO_REPAIR}" != "1" ]]; then
    BODY="$(mktemp "${STATE_DIR}/hc_mail.XXXXXX")"
    chmod 644 "${BODY}" 2>/dev/null || true
    {
      echo "EU-Adopt healthcheck FAIL (auto-repair OFF)"
      echo
      cat "${REPORT}"
    } > "${BODY}"
    send_mail_django "[EU-Adopt] Healthcheck FAIL (no auto-repair)" "${BODY}" || log "email_failed"
    rm -f "${BODY}" "${REPORT}"
    echo "=== $(date -Iseconds) site_healthcheck END exit=1 ==="
    exit 1
  fi

  # Auto-repair = rollback la EXPECTED SHA
  if do_rollback "${TARGET}"; then
    AFTER="$(sudo -u euadopt git -C "${APP_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
    # re-check
    RECHECK="$(mktemp "${STATE_DIR}/hc_recheck.XXXXXX")"
    chmod 644 "${RECHECK}" 2>/dev/null || true
    RE_EC=0
    if ! sudo -u euadopt env \
      EUADOPT_APP_DIR="${APP_DIR}" \
      EUADOPT_EXPECTED_RELEASE="${EXPECTED}" \
      EUADOPT_HEALTHCHECK_LAST_JSON="${LAST_JSON}" \
      EUADOPT_HEALTHCHECK_BASE_URL="${EUADOPT_HEALTHCHECK_BASE_URL:-https://eu-adopt.ro}" \
      bash -lc "cd '${APP_DIR}' && source venv/bin/activate && python '${PY}' check" \
      > "${RECHECK}" 2>&1
    then
      RE_EC=1
    fi
    cat "${RECHECK}" >> "${LOG}"
    if [[ "${RE_EC}" -eq 0 ]]; then
      write_repair_state "healthcheck_fail_rollback" "${BEFORE}" "${AFTER}" true
      BODY="$(mktemp "${STATE_DIR}/hc_mail.XXXXXX")"
      chmod 644 "${BODY}" 2>/dev/null || true
      {
        echo "EU-Adopt: FAIL detectat → ROLLBACK automat la versiunea bună."
        echo "sha_before=${BEFORE}"
        echo "sha_after=${AFTER}"
        echo "undo: bash ${APP_DIR}/deploy/hetzner/undo_last_auto_repair.sh"
        echo
        echo "--- fail inițial ---"
        cat "${REPORT}"
        echo
        echo "--- după rollback ---"
        cat "${RECHECK}"
      } > "${BODY}"
      send_mail_django "[EU-Adopt] Healthcheck FAIL → auto-rollback OK" "${BODY}" || log "email_failed"
      rm -f "${BODY}" "${REPORT}" "${RECHECK}"
      log "auto_repair=OK"
      echo "=== $(date -Iseconds) site_healthcheck END exit=0 ==="
      exit 0
    else
      write_repair_state "healthcheck_fail_rollback_still_bad" "${BEFORE}" "${AFTER}" false
      BODY="$(mktemp "${STATE_DIR}/hc_mail.XXXXXX")"
      chmod 644 "${BODY}" 2>/dev/null || true
      {
        echo "CRITICAL: rollback executat dar healthcheck tot FAIL. Intervenție om."
        echo "sha_before=${BEFORE}"
        echo "sha_after=${AFTER}"
        echo "undo: bash ${APP_DIR}/deploy/hetzner/undo_last_auto_repair.sh"
        echo
        cat "${REPORT}"
        echo
        cat "${RECHECK}"
      } > "${BODY}"
      send_mail_django "[EU-Adopt] CRITICAL healthcheck după rollback" "${BODY}" || log "email_failed"
      rm -f "${BODY}" "${REPORT}" "${RECHECK}"
      log "auto_repair=STILL_FAIL"
      echo "=== $(date -Iseconds) site_healthcheck END exit=1 ==="
      exit 1
    fi
  else
    write_repair_state "rollback_command_failed" "${BEFORE}" "${BEFORE}" false
    BODY="$(mktemp "${STATE_DIR}/hc_mail.XXXXXX")"
    chmod 644 "${BODY}" 2>/dev/null || true
    {
      echo "CRITICAL: nu s-a putut face rollback la ${TARGET}"
      echo "sha_before=${BEFORE}"
      echo
      cat "${REPORT}"
    } > "${BODY}"
    send_mail_django "[EU-Adopt] CRITICAL rollback eșuat" "${BODY}" || log "email_failed"
    rm -f "${BODY}" "${REPORT}"
    echo "=== $(date -Iseconds) site_healthcheck END exit=1 ==="
    exit 1
  fi
} >> "${LOG}" 2>&1
