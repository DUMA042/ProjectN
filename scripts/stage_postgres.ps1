# Stage a portable PostgreSQL runtime for the installer.
#
# Copies the server binaries (bin, lib, share) into the Tauri resources folder
# and adds the MSVC runtime DLLs so the database starts on a clean PC.
# The payload is git-ignored; run this before `tauri build`.
#
# Usage:
#   powershell -File scripts/stage_postgres.ps1
#   powershell -File scripts/stage_postgres.ps1 -Source "D:\pgsql"

[CmdletBinding()]
param(
    [string]$Source = "C:\Program Files\PostgreSQL\17",
    [string]$TargetRoot
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $TargetRoot) {
    $TargetRoot = Join-Path $repoRoot "src-tauri\resources\postgres"
}
$runtimeRoot = Join-Path $repoRoot "src-tauri\resources\runtime"

if (-not (Test-Path -LiteralPath (Join-Path $Source "bin\postgres.exe"))) {
    throw "PostgreSQL server not found under '$Source' (expected bin\postgres.exe)."
}

Write-Host "Staging PostgreSQL from $Source"
foreach ($dir in @($TargetRoot, $runtimeRoot)) {
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        continue
    }
    Get-ChildItem -LiteralPath $dir -Force |
        Where-Object { $_.Name -ne ".gitkeep" } |
        Remove-Item -Recurse -Force
}

foreach ($part in @("bin", "lib", "share")) {
    Copy-Item -LiteralPath (Join-Path $Source $part) -Destination $TargetRoot -Recurse -Force
}

# PostgreSQL and the Rust binary link the MSVC runtime dynamically. Ship it
# app-locally so no redistributable install (or elevation) is required.
$runtimeDlls = @("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll")
foreach ($dll in $runtimeDlls) {
    $sourceDll = Join-Path $env:SystemRoot "System32\$dll"
    if (-not (Test-Path -LiteralPath $sourceDll)) {
        throw "Required runtime DLL not found: $sourceDll"
    }
    Copy-Item -LiteralPath $sourceDll -Destination (Join-Path $TargetRoot "bin\$dll") -Force
    Copy-Item -LiteralPath $sourceDll -Destination (Join-Path $runtimeRoot $dll) -Force
}

$required = @(
    "bin\postgres.exe",
    "bin\initdb.exe",
    "bin\pg_ctl.exe",
    "bin\createdb.exe",
    "bin\psql.exe",
    "bin\vcruntime140.dll",
    "bin\vcruntime140_1.dll",
    "bin\msvcp140.dll",
    "share\postgres.bki",
    "share\system_views.sql",
    "share\snowball_create.sql",
    "share\postgresql.conf.sample"
)
$missing = @()
foreach ($item in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $TargetRoot $item))) {
        $missing += $item
    }
}
foreach ($dir in @("lib", "share\timezone", "share\timezonesets", "share\tsearch_data")) {
    $full = Join-Path $TargetRoot $dir
    if (-not (Test-Path -LiteralPath $full) -or -not (Get-ChildItem -LiteralPath $full -ErrorAction SilentlyContinue)) {
        $missing += "$dir (empty or missing)"
    }
}
foreach ($dll in $runtimeDlls) {
    if (-not (Test-Path -LiteralPath (Join-Path $runtimeRoot $dll))) {
        $missing += "runtime\$dll"
    }
}

if ($missing.Count -gt 0) {
    throw "Staging incomplete. Missing:`n  - $($missing -join "`n  - ")"
}

Write-Host ""
Write-Host ("{0,-8} {1,10} {2,8}" -f "Part", "Size", "Files")
$totalBytes = 0
foreach ($part in @("bin", "lib", "share")) {
    $files = Get-ChildItem -LiteralPath (Join-Path $TargetRoot $part) -Recurse -File
    $bytes = ($files | Measure-Object Length -Sum).Sum
    $totalBytes += $bytes
    Write-Host ("{0,-8} {1,7:N1} MB {2,8}" -f $part, ($bytes / 1MB), $files.Count)
}
$runtimeBytes = (Get-ChildItem -LiteralPath $runtimeRoot -File | Measure-Object Length -Sum).Sum
$totalBytes += $runtimeBytes
Write-Host ("{0,-8} {1,7:N1} MB {2,8}" -f "runtime", ($runtimeBytes / 1MB), (Get-ChildItem -LiteralPath $runtimeRoot -File).Count)
Write-Host ("{0,-8} {1,7:N1} MB" -f "total", ($totalBytes / 1MB))
Write-Host ""
Write-Host "OK: portable PostgreSQL staged at $TargetRoot"
