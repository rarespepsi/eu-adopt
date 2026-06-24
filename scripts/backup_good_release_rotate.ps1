# Salvează o copie „bună” a proiectului (git archive) și păstrează ultimele N variante.
# Utilizare: după deploy reușit sau când marchezi o versiune stabilă.
#   .\scripts\backup_good_release_rotate.ps1
#   .\scripts\backup_good_release_rotate.ps1 -Keep 3 -BackupRoot "$env:USERPROFILE\Desktop\EU-Adopt-backups\good-releases"

param(
    [int]$Keep = 3,
    [string]$BackupRoot = "",
    [string]$Label = "good"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git nu este în PATH."
}

$sha = (git rev-parse --short HEAD).Trim()
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Nu e repo git valid." }

if (-not $BackupRoot) {
    $BackupRoot = Join-Path $env:USERPROFILE "Desktop\EU-Adopt-backups\good-releases"
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$zipName = "${Label}_${stamp}_${sha}.zip"
$zipPath = Join-Path $BackupRoot $zipName
$metaPath = Join-Path $BackupRoot "${Label}_${stamp}_${sha}.txt"

Write-Host "Arhivă git -> $zipPath"
git archive --format=zip -o $zipPath HEAD
if ($LASTEXITCODE -ne 0) { throw "git archive a eșuat." }

@"
EU-Adopt — copie marcată bună
Creat: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Branch: $branch
Commit: $sha
Full: $(git rev-parse HEAD)
Repo: $RepoRoot
"@ | Set-Content -Path $metaPath -Encoding UTF8

$pattern = "${Label}_*.zip"
$existing = @(Get-ChildItem -Path $BackupRoot -Filter $pattern -File | Sort-Object LastWriteTime -Descending)
if ($existing.Count -gt $Keep) {
    $toRemove = $existing | Select-Object -Skip $Keep
    foreach ($f in $toRemove) {
        Write-Host "Șterg backup vechi: $($f.Name)"
        Remove-Item -LiteralPath $f.FullName -Force
        $sidecar = [System.IO.Path]::ChangeExtension($f.FullName, ".txt")
        if (Test-Path -LiteralPath $sidecar) {
            Remove-Item -LiteralPath $sidecar -Force
        }
    }
}

$remaining = @(Get-ChildItem -Path $BackupRoot -Filter $pattern -File | Sort-Object LastWriteTime -Descending)
Write-Host "OK. Păstrate $($remaining.Count) / $Keep :"
foreach ($f in $remaining) {
    Write-Host "  - $($f.Name)"
}
