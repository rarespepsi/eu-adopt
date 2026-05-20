# Așteaptă final lot strict 1, apoi rulează toate loturile rămase (telefon gol).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$log1 = "database\exports\places_probe_batch_strict_1.log"
$logAll = "database\exports\places_probe_full_strict.log"

Write-Host "Aștept finalizare lot 1 ($log1)..."
while ($true) {
    if (Test-Path $log1) {
        $tail = Get-Content $log1 -Tail 3 -ErrorAction SilentlyContinue
        if ($tail -match "Gata\.") { break }
    }
    Start-Sleep -Seconds 25
}
Write-Host "Lot 1 gata. Pornesc bucla pentru restul..."
python scripts\run_places_probe_all_batches.py 2>&1 | Tee-Object -FilePath $logAll
