#!/usr/bin/env bash
# Hardening server Hetzner: UFW, fail2ban, (opțional) SSH, headere nginx.
# Rulează pe server ca root:
#   bash /opt/eu-adopt/deploy/hetzner/harden_server.sh
#
# SSH fără parolă (doar după ce cheia SSH funcționează):
#   EUADOPT_SSH_HARDEN=1 bash /opt/eu-adopt/deploy/hetzner/harden_server.sh

set -euo pipefail

APP_DIR="${EUADOPT_APP_DIR:-/opt/eu-adopt}"

echo "[$(date -Is)] === EU-Adopt server hardening ==="

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ufw fail2ban

echo "[$(date -Is)] UFW: allow 22, 80, 443; deny rest"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose

echo "[$(date -Is)] fail2ban: sshd jail"
install -d -m 0755 /etc/fail2ban/jail.d
cat > /etc/fail2ban/jail.d/euadopt.conf << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
findtime = 600
bantime = 3600
EOF

systemctl enable fail2ban
systemctl restart fail2ban
fail2ban-client status sshd 2>/dev/null || echo "WARN: verifică manual fail2ban-client status"

if [[ "${EUADOPT_SSH_HARDEN:-0}" == "1" ]]; then
  if [[ -s /root/.ssh/authorized_keys ]]; then
    echo "[$(date -Is)] SSH: dezactivez autentificarea cu parolă (chei prezente)"
    install -d -m 0755 /etc/ssh/sshd_config.d
    cat > /etc/ssh/sshd_config.d/99-euadopt-hardening.conf << 'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF
    if sshd -t 2>/dev/null; then
      systemctl reload sshd || systemctl reload ssh
      echo "[$(date -Is)] SSH reîncărcat."
    else
      echo "EROARE: sshd -t a eșuat — nu am aplicat SSH hardening."
      rm -f /etc/ssh/sshd_config.d/99-euadopt-hardening.conf
    fi
  else
    echo "WARN: EUADOPT_SSH_HARDEN=1 dar /root/.ssh/authorized_keys e gol — sar peste SSH."
  fi
else
  echo "[$(date -Is)] SSH: parola rămâne activă (setează EUADOPT_SSH_HARDEN=1 după test cheie SSH)."
fi

NGINX_SCRIPT="${APP_DIR}/deploy/hetzner/apply_nginx_security.sh"
if [[ -f "${NGINX_SCRIPT}" ]]; then
  bash "${NGINX_SCRIPT}"
else
  echo "WARN: ${NGINX_SCRIPT} lipsește — rulează după git pull."
fi

echo "[$(date -Is)] === Hardening finalizat ==="
