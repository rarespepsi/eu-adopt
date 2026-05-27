# Grooming per județ (DDG strict) + curățare non-pet — 0 Google, 0 USD
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$log = "database\exports\grooming_ddg_strict_$(Get-Date -Format 'yyyy-MM-dd_HHmm').log"
Write-Host "Log: $log"
python manage.py import_grooming_ddg_by_judet --apply --max-per-judet 6 --sleep 2.5 2>&1 | Tee-Object $log
python manage.py cleanup_grooming_non_pet_leads --apply 2>&1 | Tee-Object -Append $log
Write-Host "Gata grooming strict + cleanup. Vezi $log"
