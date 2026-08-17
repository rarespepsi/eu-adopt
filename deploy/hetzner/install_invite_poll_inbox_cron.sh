#!/usr/bin/env bash
# Cron IMAP poll invitații: la fiecare 30 min (Europe/Bucharest).
# Procesează bounce / răspuns / opt-out din Zoho → marchează lead-uri.
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SCRIPT="${APP_DIR}/deploy/hetzner/run_invite_poll_inbox.sh"
REPORT_SCRIPT="${APP_DIR}/deploy/hetzner/run_invite_bounce_weekly_report.sh"

chmod +x "${SCRIPT}" "${REPORT_SCRIPT}" 2>/dev/null || true
touch /var/log/euadopt-invite-imap.log /var/log/euadopt-invite-bounce-report.log
chmod 644 /var/log/euadopt-invite-imap.log /var/log/euadopt-invite-bounce-report.log

TMP="$(mktemp)"
crontab -l 2>/dev/null \
  | grep -v 'run_invite_poll_inbox.sh' \
  | grep -v 'run_invite_bounce_weekly_report.sh' \
  | grep -v 'euadopt-invite-imap' \
  > "${TMP}" || true

# Păstrează un singur CRON_TZ=Europe/Bucharest
if ! grep -q '^CRON_TZ=Europe/Bucharest$' "${TMP}"; then
  {
    echo "CRON_TZ=Europe/Bucharest"
    cat "${TMP}"
  } > "${TMP}.2"
  mv "${TMP}.2" "${TMP}"
fi
awk 'BEGIN{seen=0} /^CRON_TZ=Europe\/Bucharest$/{if(seen++) next} {print}' "${TMP}" > "${TMP}.3"
mv "${TMP}.3" "${TMP}"

echo "*/30 * * * * bash ${SCRIPT}" >> "${TMP}"
# Luni 09:15 — raport bounce 7 zile
echo "15 9 * * 1 bash ${REPORT_SCRIPT}" >> "${TMP}"
crontab "${TMP}"
rm -f "${TMP}"

echo "Instalat cron invite IMAP poll (*/30) + bounce weekly report (Luni 09:15):"
crontab -l | grep -E 'invite.imap|invite_poll|bounce_weekly|CRON_TZ' || true
echo "Log: /var/log/euadopt-invite-imap.log"
