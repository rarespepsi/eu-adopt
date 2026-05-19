# Afișează variabilele SMTP din .env pentru copy-paste în Render → Environment
# Nu trimite nimic pe rețea. Rulează: powershell -File scripts/render_email_env_copy.ps1

$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env lipsește în $root"
    exit 1
}

$keys = @(
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "EMAIL_USE_TLS",
    "EMAIL_USE_SSL",
    "DEFAULT_FROM_EMAIL"
)

Write-Host "`n=== Copiază în Render Dashboard → Environment ===`n" -ForegroundColor Cyan
foreach ($line in Get-Content $envFile -Encoding UTF8) {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $k = ($line -split '=', 2)[0].Trim()
    if ($keys -contains $k) {
        Write-Host $line
    }
}
Write-Host "`n(Salvează → Manual Deploy sau așteaptă redeploy automat)`n" -ForegroundColor Green
