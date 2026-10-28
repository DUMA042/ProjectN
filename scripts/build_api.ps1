# Build the self-contained API sidecar (flow-api.exe) with PyInstaller.
#
# Usage:
#   powershell -File scripts/build_api.ps1
#   powershell -File scripts/build_api.ps1 -SkipInstall   # reuse .venv-pack
#
# Output: src-tauri/resources/api/flow-api.exe (+ support files), git-ignored.

[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

# Numerical libraries spawn one worker per logical CPU by default, which can
# exhaust memory on small build machines. Keep them single-threaded.
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $repoRoot ".venv-pack"
$venvPython = Join-Path $venv "Scripts\python.exe"
$work = Join-Path $repoRoot "build\pyinstaller"
$dist = Join-Path $work "dist"
$target = Join-Path $repoRoot "src-tauri\resources\api"

if (-not $SkipInstall) {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host "Creating packaging venv at $venv"
        & $Python -m venv $venv
    }
    Write-Host "Installing build dependencies (this takes a while)..."
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install `
        -r (Join-Path $repoRoot "requirements.lock.txt") `
        -r (Join-Path $repoRoot "requirements-pack.txt") `
        --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Packaging venv not found at $venvPython (run without -SkipInstall)."
}

if (-not (Test-Path -LiteralPath $target)) {
    New-Item -ItemType Directory -Path $target -Force | Out-Null
}

Write-Host "Running PyInstaller..."
Push-Location $repoRoot
try {
    # PyInstaller resolves relative --add-data paths against --specpath, so all
    # sources are passed as absolute paths.
    $pyArgs = @(
        "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--name", "flow-api",
        "--distpath", $dist,
        "--workpath", $work,
        "--specpath", $work,
        "--add-data", "$repoRoot\migrations;migrations",
        "--add-data", "$repoRoot\alembic.ini;.",
        "--add-data", "$repoRoot\owl\load\schema.sql;owl/load",
        "--hidden-import", "api.main",
        "--hidden-import", "scripts.load_seed",
        "--hidden-import", "scripts.export_seed",
        "--collect-data", "docx",
        "--collect-submodules", "uvicorn",
        "--exclude-module", "statsmodels",
        "--exclude-module", "scipy",
        "--exclude-module", "pytest",
        "--exclude-module", "_pytest",
        "--exclude-module", "black",
        "--exclude-module", "streamlit",
        "--exclude-module", "altair",
        "--exclude-module", "tkinter",
        (Join-Path $repoRoot "api\__main__.py")
    )
    & $venvPython @pyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

$built = Join-Path $dist "flow-api"
if (-not (Test-Path -LiteralPath (Join-Path $built "flow-api.exe"))) {
    throw "Build output missing: $built\flow-api.exe"
}

# Replace the previous sidecar, keeping the tracked .gitkeep.
Get-ChildItem -LiteralPath $target -Force |
    Where-Object { $_.Name -ne ".gitkeep" } |
    Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $built "*") -Destination $target -Recurse -Force
Remove-Item -LiteralPath $dist -Recurse -Force

$checks = @(
    "flow-api.exe",
    "_internal\alembic.ini",
    "_internal\migrations\env.py",
    "_internal\migrations\versions\0001_baseline_full_schema.py",
    "_internal\owl\load\schema.sql"
)
$missing = @()
foreach ($item in $checks) {
    if (-not (Test-Path -LiteralPath (Join-Path $target $item))) {
        $missing += $item
    }
}
if ($missing.Count -gt 0) {
    throw "Sidecar incomplete. Missing:`n  - $($missing -join "`n  - ")"
}

$files = Get-ChildItem -LiteralPath $target -Recurse -File
$bytes = ($files | Measure-Object Length -Sum).Sum
Write-Host ""
Write-Host ("Sidecar: {0:N1} MB in {1} files" -f ($bytes / 1MB), $files.Count)
Write-Host "Output:  $target\flow-api.exe"
Write-Host "OK"
