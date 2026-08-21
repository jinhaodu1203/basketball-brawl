$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$ZipName = "HOOP HAVOC Latest Windows.zip"
$ZipPath = Join-Path $Root $ZipName

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " HOOP HAVOC - Latest Windows ZIP Builder" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

$Python = Join-Path $Root "winenv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "winenv Python not found. Creating Python 3.11 environment..." -ForegroundColor Yellow
    py -3.11 -m venv winenv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create Python 3.11 winenv."
    }
}

$Version = & $Python --version 2>&1
Write-Host "Python: $Version"

if ($Version -notmatch "3\.11") {
    throw "This builder requires Python 3.11."
}

Write-Host "[1/6] Installing/updating required packages..." -ForegroundColor Yellow
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

& $Python -m pip install pygame==2.6.1 pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pygame/PyInstaller installation failed." }

$Required = @(
    "main.py",
    "game.py",
    "player.py",
    "ball.py",
    "ai.py",
    "animation.py",
    "arenas.py",
    "characters.py",
    "constants.py",
    "entities.py",
    "feedback.py",
    "localization.py",
    "settings.py",
    "ui.py",
    "audio.py",
    "assets",
    "assets\ball.png",
    "assets\props\hoop.png",
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
    Write-Host "Missing required release files:" -ForegroundColor Red
    foreach ($Item in $Missing) {
        Write-Host "  - $Item" -ForegroundColor Red
    }
    throw "Release prerequisites are incomplete."
}

Write-Host "[2/6] Checking Python source syntax..." -ForegroundColor Yellow
Get-ChildItem -Path $Root -File -Filter "*.py" | ForEach-Object {
    if (
        $_.Name -notmatch "_before_" -and
        $_.Name -notmatch "_backup" -and
        $_.Name -notmatch "_broken_" -and
        $_.Name -notmatch "_working"
    ) {
        & $Python -m py_compile $_.FullName
        if ($LASTEXITCODE -ne 0) {
            throw "Syntax check failed: $($_.Name)"
        }
    }
}

$BuildDir = Join-Path $Root "build_win"
$DistDir = Join-Path $Root "dist_win"
$StageDir = Join-Path $Root "_windows_latest_release_stage"

Write-Host "[3/6] Cleaning old Windows build..." -ForegroundColor Yellow
Remove-Item $BuildDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $DistDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $StageDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path $StageDir -Force | Out-Null

Write-Host "[4/6] Building latest HOOP HAVOC.exe..." -ForegroundColor Yellow

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --workpath $BuildDir `
    --distpath $DistDir `
    (Join-Path $Root "HOOP_HAVOC_Windows.spec")

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$BuiltFolder = Join-Path $DistDir "HOOP HAVOC"
$ExePath = Join-Path $BuiltFolder "HOOP HAVOC.exe"

if (-not (Test-Path $ExePath)) {
    throw "Build completed, but HOOP HAVOC.exe was not found."
}

Write-Host "[5/6] Preparing portable release..." -ForegroundColor Yellow

Copy-Item (Join-Path $BuiltFolder "*") $StageDir -Recurse -Force

$Readme = @"
HOOP HAVOC / 篮界狂潮
Latest Windows Portable Build
Build date: $(Get-Date -Format "yyyy-MM-dd HH:mm")

Developer / 开发者
Jinhao Du (David)

========================================
HOW TO RUN / 运行方式
========================================

1. 完整解压整个 ZIP。
2. 打开解压后的文件夹。
3. 双击 HOOP HAVOC.exe。
4. 不要单独移动 EXE；_internal 文件夹必须和 EXE 保持在一起。

No installation required:
- Python
- Pygame
- PyCharm

Recommended:
- Windows 10 64-bit
- Windows 11 64-bit

========================================
LATEST BUILD NOTES
========================================

- Includes current Windows game source and assets.
- Includes the Windows IME fix:
  Left Shift remains the Player 1 ability key,
  but pressing the ability no longer toggles Chinese/English input mode.
- Includes the latest character, arena, gameplay, UI and audio files
  present in the project at build time.

========================================
WINDOWS SECURITY NOTICE
========================================

This development build is not commercially code-signed.
Windows SmartScreen may show an Unknown Publisher warning.

Only run the ZIP when obtained directly from the developer
or another trusted source.

Copyright © 2026 Jinhao Du.
All rights reserved.
"@

Set-Content `
    -Path (Join-Path $StageDir "README_FIRST.txt") `
    -Value $Readme `
    -Encoding UTF8

# Include release/legal audit files when present.
foreach ($Optional in @(
    "STEAM_ASSET_AUDIT.txt",
    "STEAM_ASSET_RIGHTS.md",
    "CRAFTPIX_LICENSE.txt"
)) {
    $Source = Join-Path $Root $Optional
    if (Test-Path $Source) {
        Copy-Item $Source (Join-Path $StageDir $Optional) -Force
    }
}

Write-Host "[6/6] Creating latest ZIP..." -ForegroundColor Yellow

Compress-Archive `
    -Path (Join-Path $StageDir "*") `
    -DestinationPath $ZipPath `
    -CompressionLevel Optimal `
    -Force

Remove-Item $StageDir -Recurse -Force -ErrorAction SilentlyContinue

if (-not (Test-Path $ZipPath)) {
    throw "ZIP creation failed."
}

$ZipInfo = Get-Item $ZipPath
$SizeMB = [math]::Round($ZipInfo.Length / 1MB, 2)

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " BUILD SUCCESS" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Latest playable ZIP:" -ForegroundColor Cyan
Write-Host "  $ZipPath"
Write-Host "  Size: $SizeMB MB"
Write-Host ""
Write-Host "Local EXE:" -ForegroundColor Cyan
Write-Host "  $ExePath"
Write-Host ""
