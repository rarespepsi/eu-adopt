#!/usr/bin/env bash
# Adaugă headere de securitate în site-ul nginx eu-adopt (certbot sau template).
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
SNIPPET_SRC="${APP_DIR}/deploy/hetzner/nginx-security-headers.conf"
SNIPPET_DST="/etc/nginx/snippets/euadopt-security-headers.conf"
SITE="/etc/nginx/sites-available/eu-adopt"
MARKER="# euadopt-security-headers"

if [[ ! -f "${SNIPPET_SRC}" ]]; then
  echo "EROARE: lipsește ${SNIPPET_SRC}"
  exit 1
fi

install -d -m 0755 /etc/nginx/snippets
cp "${SNIPPET_SRC}" "${SNIPPET_DST}"

if [[ ! -f "${SITE}" ]]; then
  echo "WARN: ${SITE} lipsește — sar peste patch nginx."
  exit 0
fi

if ! grep -qF "${MARKER}" "${SITE}"; then
  # Inserează după prima linie server { din blocul HTTPS (listen 443) sau global.
  awk -v m="${MARKER}" '
    /listen 443/ && !done {
      print
      print "    include snippets/euadopt-security-headers.conf; " m
      done=1
      next
    }
    { print }
  ' "${SITE}" > "${SITE}.tmp" && mv "${SITE}.tmp" "${SITE}"
  if ! grep -qF "${MARKER}" "${SITE}"; then
    # fallback: după server_name
    sed -i "/server_name eu-adopt.ro/a\\    include snippets/euadopt-security-headers.conf; ${MARKER}" "${SITE}"
  fi
  echo "nginx: headere securitate adăugate în ${SITE}"
else
  echo "nginx: headere deja prezente"
fi

nginx -t
systemctl reload nginx
echo "[$(date -Is)] nginx reîncărcat."
