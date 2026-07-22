# Deploy pe Hetzner din PC: copie bună locală (rotație 3) + backup DB pe server + pull/migrate/restart.
#   .\scripts\deploy_hetzner_from_pc.ps1
#   .\scripts\deploy_hetzner_from_pc.ps1 -SkipLocalBackup
#   .\scripts\deploy_hetzner_from_pc.ps1 -HetznerHost root@178.104.31.52

param(
    [string]$HetznerHost = "root@178.104.31.52",
    [switch]$SkipLocalBackup,
    [int]$LocalKeep = 3,
    [int]$DbKeep = 3
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not $SkipLocalBackup) {
    Write-Host "=== 1/2 Copie bună locală (păstrează $LocalKeep) ==="
    & (Join-Path $PSScriptRoot "backup_good_release_rotate.ps1") -Keep $LocalKeep
}

Write-Host "=== 2/2 Hetzner: backup DB + deploy ==="
$remoteCmd = "EUADOPT_DB_BACKUP_KEEP=$DbKeep bash /opt/eu-adopt/deploy/hetzner/deploy_update.sh"

ssh -o BatchMode=yes $HetznerHost $remoteCmd
if ($LASTEXITCODE -ne 0) { throw "Deploy SSH a eșuat (exit $LASTEXITCODE)." }

Write-Host "=== Deploy finalizat ==="
