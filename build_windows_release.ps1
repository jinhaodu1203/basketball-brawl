$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " HOOP HAVOC - Windows Release Builder" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$Python = Join-Path $Root "winenv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: winenv Python was not found:" -ForegroundColor Red
    Write-Host $Python -ForegroundColor Red
    Write-Host ""
    Write-Host "Create the Python 3.11 environment first:" -ForegroundColor Yellow
    Write-Host '  py -3.11 -m venv winenv'
    exit 1
}

$Version = & $Python --version 2>&1
Write-Host "Python: $Version"

if ($Version -notmatch "3\.11") {
    Write-Host "ERROR: This release builder expects Python 3.11." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $Root "main.py"))) {
    Write-Host "ERROR: main.py is missing from the project root." -ForegroundColor Red
    exit 1
}

# Some earlier ZIP extractions created a nested "HOOP HAVOC" directory.
# If DUKE assets are missing from the real project root, recover only those assets
# from the nested copy without replacing the latest Python source files.
$Nested = Join-Path $Root "HOOP HAVOC"
$RootAssets = Join-Path $Root "assets"
$NestedAssets = Join-Path $Nested "assets"

if (-not (Test-Path $RootAssets)) {
    if (Test-Path $NestedAssets) {
        Write-Host "Restoring assets folder from nested project copy..." -ForegroundColor Yellow
        Copy-Item $NestedAssets $RootAssets -Recurse -Force
    }
}

$Duke = Join-Path $Root "assets\characters\duke"
$Echo = Join-Path $Root "assets\characters\duke_blood_echo"

if (-not (Test-Path $Duke)) {
    $NestedDuke = Join-Path $Nested "assets\characters\duke"
    if (Test-Path $NestedDuke) {
        Write-Host "Restoring DUKE assets..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path (Split-Path $Duke -Parent) | Out-Null
        Copy-Item $NestedDuke $Duke -Recurse -Force
    }
}

if (-not (Test-Path $Echo)) {
    $NestedEcho = Join-Path $Nested "assets\characters\duke_blood_echo"
    if (Test-Path $NestedEcho) {
        Write-Host "Restoring Blood Echo assets..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path (Split-Path $Echo -Parent) | Out-Null
        Copy-Item $NestedEcho $Echo -Recurse -Force
    }
}

$Required = @(
    "assets",
    "assets\ball.png",
    "assets\props\hoop.png",
    "assets\characters\djh",
    "assets\characters\gorilla",
    "assets\characters\ninja",
    "assets\characters\duke",
    "assets\characters\duke_blood_echo",
    "lang\en.json",
    "lang\zh.json",
    "HOOP_HAVOC_Windows.spec"
)

$Missing = @()
foreach ($Item in $Required) {
    if (-not (Test-Path (Join-Path $Root $Item))) {
        $Missing += $Item
    }
}

if ($Missing.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: Required release files are missing:" -ForegroundColor Red
    foreach ($Item in $Missing) {
        Write-Host "  - $Item" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Do not build until these files are restored." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[1/4] Installing/updating PyInstaller..." -ForegroundColor Green
& $Python -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$BuildDir = Join-Path $Root "build_win"
$DistDir = Join-Path $Root "dist_win"
$ReleaseRoot = Join-Path $Root "RELEASE_WINDOWS"
$PortableDir = Join-Path $ReleaseRoot "HOOP HAVOC"
$ZipPath = Join-Path $ReleaseRoot "HOOP_HAVOC_Windows_V3.2_Portable.zip"

Write-Host ""
Write-Host "[2/4] Cleaning old Windows build..." -ForegroundColor Green
Remove-Item $BuildDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $DistDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $PortableDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null

Write-Host ""
Write-Host "[3/4] Building HOOP HAVOC.exe..." -ForegroundColor Green
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --workpath $BuildDir `
    --distpath $DistDir `
    (Join-Path $Root "HOOP_HAVOC_Windows.spec")

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller build failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

$BuiltFolder = Join-Path $DistDir "HOOP HAVOC"
$ExePath = Join-Path $BuiltFolder "HOOP HAVOC.exe"

if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: Build completed but HOOP HAVOC.exe was not found." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[4/4] Creating friend-ready ZIP..." -ForegroundColor Green
Copy-Item $BuiltFolder $PortableDir -Recurse -Force

$Readme = @"
HOOP HAVOC / 篮界狂潮
Windows Portable Build - V3.2

HOW TO PLAY
1. Extract the entire ZIP first.
2. Open the extracted "HOOP HAVOC" folder.
3. Double-click "HOOP HAVOC.exe".
4. Keep all files/folders beside the EXE. Do not move only the EXE out of the folder.

REQUIREMENTS
- Windows 10/11 64-bit recommended.
- Python, pygame and PyCharm are NOT required.

If Windows SmartScreen appears, only run the game if you received this build directly
from someone you trust. This development build is not code-signed yet.
"@

Set-Content -Path (Join-Path $PortableDir "README_FIRST.txt") -Value $Readme -Encoding UTF8

Compress-Archive `
    -Path $PortableDir `
    -DestinationPath $ZipPath `
    -CompressionLevel Optimal `
    -Force

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " BUILD SUCCESS" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test EXE:" -ForegroundColor Cyan
Write-Host "  $ExePath"
Write-Host ""
Write-Host "Send this ZIP to your friend:" -ForegroundColor Cyan
Write-Host "  $ZipPath"
Write-Host ""
Write-Host "IMPORTANT: Test the EXE on this PC before sending the ZIP." -ForegroundColor Yellow
