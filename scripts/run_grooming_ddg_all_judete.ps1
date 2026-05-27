$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
python manage.py import_grooming_ddg_by_judet --apply --max-per-judet 10 --sleep 2.5 2>&1 | Tee-Object "database\exports\grooming_ddg_import.log"
