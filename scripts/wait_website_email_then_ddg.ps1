# După scrape website din notes → DDG loturi (0 Google)
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"

$countPy = @"
from django.db.models import Q
from home.models import StaffOnboardingLead
n = StaffOnboardingLead.objects.filter(
    Q(email__iendswith='@lead-placeholder.invalid') | Q(email=''),
).filter(notes__regex=r'web=https?://').exclude(
    notes__contains='[WEBSITE_EMAIL_FROM_NOTES'
).count()
print(n)
"@

Write-Host "Aștept final scrape website din notes..."
while ($true) {
    $n = python manage.py shell -c $countPy 2>$null | Select-Object -Last 1
    if ($n -eq "0") { break }
    Write-Host "  rămase scrape: $n"
    Start-Sleep -Seconds 45
}
Write-Host "Scrape gata. Pornesc DDG (fără Google)..."
python scripts\run_web_email_probe_all_batches.py 2>&1 | Tee-Object -FilePath "database\exports\web_email_ddg_full.log"
