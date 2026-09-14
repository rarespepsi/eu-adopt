#!/usr/bin/env bash
# Repară vhost-urile Eu: .com/.de/.fr/.es nu mai cad pe cazareamea (default SSL).
# Rulează ca root pe Hetzner.
# După editare: sites-enabled/eu-adopt trebuie să fie symlink la sites-available
# (copie separată a cauzat regresii — enabled rămânea vechi).
set -euo pipefail

EU_AVAIL="/etc/nginx/sites-available/eu-adopt"
EU_ENABLED="/etc/nginx/sites-enabled/eu-adopt"
BACKUP_DIR="/root/nginx-backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"
cp -a "${EU_AVAIL}" "${BACKUP_DIR}/eu-adopt.${STAMP}"
if [[ -e "${EU_ENABLED}" && ! -L "${EU_ENABLED}" ]]; then
  cp -a "${EU_ENABLED}" "${BACKUP_DIR}/eu-adopt.enabled.${STAMP}"
fi

python3 - <<'PY'
from pathlib import Path
import re

path = Path("/etc/nginx/sites-available/eu-adopt")
text = path.read_text(encoding="utf-8")
names = (
    "eu-adopt.ro www.eu-adopt.ro "
    "euadopt.com www.euadopt.com "
    "euadopt.de www.euadopt.de "
    "euadopt.fr www.euadopt.fr "
    "euadopt.es www.euadopt.es "
    "euadopt.eu www.euadopt.eu "
    "euadopt.org www.euadopt.org "
    "eu-adopt.com www.eu-adopt.com "
    "eu-adopt.eu www.eu-adopt.eu"
)

def repl_server_name(_m):
    return f"    server_name {names};"

text2 = re.sub(
    r"^[ \t]*server_name\s+eu-adopt\.ro[^;]*;",
    repl_server_name,
    text,
    flags=re.M,
)

# Make first listen 443 ssl the default_server (only once)
if "default_server" not in text2:
    text2 = text2.replace(
        "listen 443 ssl; # managed by Certbot",
        "listen 443 ssl default_server; # managed by Certbot + euadopt catch-all",
        1,
    )
    if "default_server" not in text2:
        text2 = re.sub(
            r"(listen\s+443\s+ssl)(\s*;)",
            r"\1 default_server\2",
            text2,
            count=1,
        )

path.write_text(text2, encoding="utf-8")
print("updated", path)
print("--- preview server_name / listen ---")
for ln in path.read_text(encoding="utf-8").splitlines():
    if "server_name" in ln or "listen 443" in ln or "listen 80" in ln:
        print(ln)
PY

# Asigură symlink (nu copie) sites-enabled → sites-available
rm -f "${EU_ENABLED}"
ln -s "${EU_AVAIL}" "${EU_ENABLED}"
ls -la "${EU_ENABLED}"

nginx -t
systemctl reload nginx
echo "nginx reloaded OK"
echo "backup: ${BACKUP_DIR}/eu-adopt.${STAMP}"
