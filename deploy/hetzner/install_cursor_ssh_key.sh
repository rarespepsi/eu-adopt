#!/bin/bash
# Instalează cheia SSH Cursor PC pe root@H (o singură rulare).
set -euo pipefail
KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA91pssE3EzUvxwCcQcTAURbBnCMfidXQ7PtdOdcsktF cursor-euadopt-pc'
mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
if grep -qF "$KEY" /root/.ssh/authorized_keys; then
  echo "CHEIE_OK already"
else
  printf '%s\n' "$KEY" >> /root/.ssh/authorized_keys
  echo "CHEIE_OK added"
fi
