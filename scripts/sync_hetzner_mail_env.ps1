# Sincronizează SMTP + invitații + IMAP pe Hetzner din .env local (fără a comite parole).
#   .\scripts\sync_hetzner_mail_env.ps1

param(
    [string]$HetznerHost = "root@178.104.31.52",
    [string]$RemoteEnv = "/opt/eu-adopt/.env"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$LocalEnv = Join-Path $RepoRoot ".env"
if (-not (Test-Path $LocalEnv)) {
    throw "Lipsește $LocalEnv"
}

function Get-EnvValue([string]$key) {
    foreach ($line in Get-Content $LocalEnv -Encoding UTF8) {
        if ($line -match "^\s*$([regex]::Escape($key))\s*=\s*(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return ""
}

$smtpPwd = Get-EnvValue "EMAIL_HOST_PASSWORD"
if (-not $smtpPwd) {
    throw "EMAIL_HOST_PASSWORD gol în .env local"
}

$imapHost = Get-EnvValue "STAFF_INVITE_IMAP_HOST"
if (-not $imapHost) { $imapHost = "imappro.zoho.eu" }
$imapUser = Get-EnvValue "STAFF_INVITE_IMAP_USER"
if (-not $imapUser) { $imapUser = Get-EnvValue "EMAIL_HOST_USER" }
if (-not $imapUser) { $imapUser = "contact@eu-adopt.ro" }

$py = @"
import pathlib
import re

path = pathlib.Path(r"$RemoteEnv")
text = path.read_text(encoding="utf-8") if path.exists() else ""

def set_kv(key: str, val: str) -> None:
    global text
    line = f"{key}={val}"
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if pat.search(text):
        text = pat.sub(line, text)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"

pwd = $(python -c "import json,sys; print(json.dumps(sys.argv[1]))" $smtpPwd)
set_kv("EMAIL_HOST_PASSWORD", pwd)
set_kv("EUADOPT_STAFF_INVITE_EMAIL_ENABLED", "1")
set_kv("STAFF_INVITE_IMAP_HOST", "$imapHost")
set_kv("STAFF_INVITE_IMAP_PORT", "993")
set_kv("STAFF_INVITE_IMAP_USER", "$imapUser")
set_kv("STAFF_INVITE_IMAP_PASSWORD", pwd)
path.write_text(text, encoding="utf-8")
print("OK: .env actualizat")
"@

$tmpPy = [System.IO.Path]::GetTempFileName() + ".py"
Set-Content -Path $tmpPy -Value $py -Encoding UTF8
scp -o BatchMode=yes $tmpPy "${HetznerHost}:/tmp/patch_euadopt_env.py"
ssh -o BatchMode=yes $HetznerHost "python3 /tmp/patch_euadopt_env.py && rm -f /tmp/patch_euadopt_env.py"
Remove-Item $tmpPy -Force

Write-Host "Repornire serviciu euadopt..."
ssh -o BatchMode=yes $HetznerHost "systemctl restart euadopt"
Write-Host "Gata - SMTP invitatii activ pe Hetzner."
