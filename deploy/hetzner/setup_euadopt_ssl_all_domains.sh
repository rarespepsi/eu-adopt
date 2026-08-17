#!/usr/bin/env bash
# Rulează pe Hetzner (root) după DNS A/AAAA pentru toate hosturile din registrul EU-Adopt.
#   bash /opt/eu-adopt/deploy/hetzner/setup_euadopt_ssl_all_domains.sh
set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"
CERTBOT_EMAIL="${EUADOPT_CERTBOT_EMAIL:-contact@eu-adopt.ro}"

DOMAINS=(
  eu-adopt.ro www.eu-adopt.ro
  euadopt.com www.euadopt.com
  euadopt.eu www.euadopt.eu
  euadopt.org www.euadopt.org
  euadopt.de www.euadopt.de
  euadopt.fr www.euadopt.fr
  euadopt.es www.euadopt.es
  eu-adopt.com www.eu-adopt.com
  eu-adopt.eu www.eu-adopt.eu
)

echo "==> Copiază nginx (revizuiește conflict cu sites-enabled/eu-adopt)"
cp -a "${APP_DIR}/deploy/hetzner/nginx-euadopt-all-domains.conf" /etc/nginx/sites-available/euadopt-all-domains
ln -sf /etc/nginx/sites-available/euadopt-all-domains /etc/nginx/sites-enabled/euadopt-all-domains
nginx -t
systemctl reload nginx

echo "==> Certbot (toate domeniile active + redirect cratimă)"
certbot --nginx --non-interactive --agree-tos -m "${CERTBOT_EMAIL}" \
  -d eu-adopt.ro -d www.eu-adopt.ro \
  -d euadopt.com -d www.euadopt.com \
  -d euadopt.eu -d www.euadopt.eu \
  -d euadopt.org -d www.euadopt.org \
  -d euadopt.de -d www.euadopt.de \
  -d euadopt.fr -d www.euadopt.fr \
  -d euadopt.es -d www.euadopt.es \
  -d eu-adopt.com -d www.eu-adopt.com \
  -d eu-adopt.eu -d www.eu-adopt.eu \
  || echo "Certbot parțial — verifică DNS pentru hosturile eșuate"

echo "==> Editează manual redirect HTTPS eu-adopt.com/.eu → euadopt.* (vezi comentarii în nginx-euadopt-all-domains.conf)"
echo "Done. Test: curl -I https://euadopt.com/ && curl -I https://eu-adopt.com/shop/"
