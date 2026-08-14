# Build the Windows release of HOOP HAVOC.
#
#   .\build_windows.ps1              # build
#   .\build_windows.ps1 -Clean       # wipe previous output first
#
# Output: dist-windows\HOOP HAVOC\HOOP HAVOC.exe
#
# The output goes to dist-windows\ / build-windows\ rather than the default
# dist\ / build\ because those two directories hold the committed macOS build
# and must not be overwritten.

[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$spec = Join-Path $root 'HOOP HAVOC.spec'
$distPath = Join-Path $root 'dist-windows'
$workPath = Join-Path $root 'build-windows'

if (-not (Test-Path $python)) {
    Write-Error @"
Virtual environment not found at $python

Create it first:
    py -3.13 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install "pygame==2.6.1" pyinstaller
"@
}

if ($Clean) {
    foreach ($path in @($distPath, $workPath)) {
        if (Test-Path $path) {
            Write-Host "Removing $path"
            Remove-Item -Recurse -Force $path
        }
    }
}

Write-Host "Building HOOP HAVOC for Windows..." -ForegroundColor Cyan

& $python -m PyInstaller `
    --noconfirm `
    --distpath $distPath `
    --workpath $workPath `
    $spec

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
}

$exe = Join-Path $distPath 'HOOP HAVOC\HOOP HAVOC.exe'
if (-not (Test-Path $exe)) {
    Write-Error "Build reported success but $exe is missing."
}

$sizeMb = [math]::Round((Get-Item $exe).Length / 1MB, 2)
$totalMb = [math]::Round(
    ((Get-ChildItem (Join-Path $distPath 'HOOP HAVOC') -Recurse -File |
        Measure-Object -Property Length -Sum).Sum / 1MB), 2)

Write-Host ""
Write-Host "Build succeeded." -ForegroundColor Green
Write-Host "  Executable: $exe ($sizeMb MB)"
Write-Host "  Total size: $totalMb MB"
