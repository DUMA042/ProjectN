# Build the per-user Windows installer.
#
# Prerequisites: node_modules, .venv-pack, staged PostgreSQL, built API sidecar
# and runtime DLLs (scripts/stage_postgres.ps1 + scripts/build_api.ps1).
#
# Usage:
#   powershell -File scripts/package.ps1
#   powershell -File scripts/package.ps1 -SkipSeed      # reuse staged seed

[CmdletBinding()]
param(
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$resources = Join-Path $repoRoot "src-tauri\resources"
$seedDir = Join-Path $resources "seed"
$expected = @{
    employees = 1658
    employees_with_phone = 1423
    departments = 40
    leave_types = 8
    rules = 5
}

$prerequisites = @(
    (Join-Path $repoRoot "node_modules"),
    (Join-Path $repoRoot ".venv-pack"),
    (Join-Path $resources "postgres\bin\postgres.exe"),
    (Join-Path $resources "api\flow-api.exe"),
    (Join-Path $resources "runtime\vcruntime140.dll"),
    (Join-Path $repoRoot "src-tauri\icons\icon.ico")
)
$missing = @($prerequisites | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missing.Count -gt 0) {
    throw "Missing packaging prerequisites:`n  - $($missing -join "`n  - ")"
}

if (-not $SkipSeed) {
    Write-Host "Staging the employee seed bundle..."
    if (-not (Test-Path -LiteralPath $seedDir)) {
        New-Item -ItemType Directory -Path $seedDir -Force | Out-Null
    }
    Get-ChildItem -LiteralPath $seedDir -Force |
        Where-Object { $_.Name -ne ".gitkeep" } |
        Remove-Item -Recurse -Force
    & python (Join-Path $repoRoot "scripts\export_seed.py") --out $seedDir
    if ($LASTEXITCODE -ne 0) {
        throw "Seed export failed."
    }
}

$manifestPath = Join-Path $seedDir "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Seed manifest missing at $manifestPath"
}
$counts = (Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json).counts
foreach ($key in $expected.Keys) {
    if ([int]$counts.$key -ne $expected[$key]) {
        throw "Seed mismatch for '$key': expected $($expected[$key]), found $($counts.$key)"
    }
}
Write-Host ("Seed verified: {0} employees, {1} phones, {2} departments, {3} leave types, {4} rules" -f `
    $counts.employees, $counts.employees_with_phone, $counts.departments, $counts.leave_types, $counts.rules)

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "dist\index.html"))) {
    Write-Host "Note: the frontend is rebuilt by the Tauri build step."
}

$env:CARGO_BUILD_JOBS = "1"
$env:CARGO_PROFILE_RELEASE_DEBUG = "false"
$env:CARGO_INCREMENTAL = "0"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"

$nsisCache = Join-Path $env:LOCALAPPDATA "tauri"
if (-not (Test-Path -LiteralPath $nsisCache)) {
    Write-Host "First run: Tauri downloads the NSIS tooling (network required)."
}

Write-Host "Building the installer (release build, this takes a while)..."
& npx tauri build
if ($LASTEXITCODE -ne 0) {
    throw "tauri build failed with exit code $LASTEXITCODE."
}

$bundleDir = Join-Path $repoRoot "src-tauri\target\release\bundle\nsis"
$installer = Get-ChildItem -LiteralPath $bundleDir -Filter *.exe -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $installer) {
    throw "Installer not found under $bundleDir"
}

$hash = (Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256).Hash
Write-Host ""
Write-Host ("Installer: {0}" -f $installer.FullName)
Write-Host ("Size:      {0:N1} MB" -f ($installer.Length / 1MB))
Write-Host ("SHA256:    {0}" -f $hash)
Write-Host ""
Write-Host "OK"
