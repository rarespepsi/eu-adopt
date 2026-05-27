$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
python manage.py import_pet_hotel_pensiune_ddg_by_judet --apply --max-per-judet 8 --sleep 2.5 2>&1 | Tee-Object "database\exports\pet_hotel_pensiune_import.log"
