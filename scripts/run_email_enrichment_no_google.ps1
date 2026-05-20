# 1) Scrape email din web= în notes (0 Google)
# 2) DDG în loturi pentru rest
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=== Pas 1: email de pe website din notes ==="
python manage.py staff_lead_email_from_website_notes --limit 2000 --apply --sleep 0.35
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Pas 2: DDG email (loturi 500) ==="
python scripts\run_web_email_probe_all_batches.py 2>&1 | Tee-Object -FilePath "database\exports\web_email_ddg_full.log"
