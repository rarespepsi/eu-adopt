# Faza 1: scrape site + pagini contact (739 cu web= în notes)
# Faza 2: pipeline complet (site + Facebook + DDG + Bing) în loturi
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$log = "database\exports\free_email_enrich_full.log"

Write-Host "=== Faza 1: website + contact pages (prioritate URL în notes) ===" | Tee-Object $log
python manage.py staff_lead_free_email_enrich --limit 800 --apply --website-only 2>&1 | Tee-Object $log -Append
if ($LASTEXITCODE -ne 0) { Write-Host "Faza 1 exit $LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host "=== Faza 2: enrich complet (DDG/Bing/Facebook) loturi 200 ===" | Tee-Object $log -Append
python scripts\run_free_email_enrich_batches.py 2>&1 | Tee-Object $log -Append
