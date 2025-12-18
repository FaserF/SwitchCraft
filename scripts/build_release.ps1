<#
.SYNOPSIS
    Builds a SwitchCraft release executable.

.DESCRIPTION
    This script installs necessary dependencies, builds the project using PyInstaller,
    and moves the resulting executable to the user's Downloads folder.

.NOTES
    File Name      : build_release.ps1
    Author         : SwitchCraft Team
    Prerequisite   : Python 3.9+ installed and in PATH.
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SwitchCraft Release Builder (Windows)  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check for Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.9+"
    exit 1
}

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot
Write-Host "Project Root: $RepoRoot" -ForegroundColor Gray

# 0. Cleanup Running Processes
Write-Host "`n[0/5] Checking for running instances..." -ForegroundColor Yellow
$ProcessName = "SwitchCraft"
$RunningProcesses = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
if ($RunningProcesses) {
    Write-Host "Found running instance(s) of $ProcessName. Terminating..." -ForegroundColor Magenta
    $RunningProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2 # Wait for file unlock
    Write-Host "Terminated." -ForegroundColor Gray
}

# 1. Install Dependencies
Write-Host "`n[1/5] Installing/Updating Deployment Dependencies..." -ForegroundColor Yellow
try {
    # Install PyInstaller explicitly
    python -m pip install --upgrade pyinstaller

    # Install project dependencies
    python -m pip install .
}
catch {
    Write-Error "Failed to install dependencies. $_"
    exit 1
}

# 2. Build with PyInstaller
Write-Host "`n[2/5] Building Executable..." -ForegroundColor Yellow
if (-not (Test-Path "$RepoRoot\switchcraft.spec")) {
    Write-Error "switchcraft.spec not found in project root!"
    exit 1
}

try {
    # Use python -m PyInstaller to avoid PATH issues
    python -m PyInstaller switchcraft.spec --clean --noconfirm
}
catch {
    Write-Error "Build failed. $_"
    exit 1
}

# 3. Locate Artifact
$BuiltExe = "$RepoRoot\dist\SwitchCraft.exe"
if (-not (Test-Path $BuiltExe)) {
    Write-Error "Build appeared to succeed but $BuiltExe is missing."
    exit 1
}

# 4. Move to Downloads
Write-Host "`n[4/5] Moving Artifact..." -ForegroundColor Yellow
$DownloadsDir = [System.Environment]::GetFolderPath("UserProfile") + "\Downloads"
$TargetExe = Join-Path $DownloadsDir "SwitchCraft.exe"

try {
    Copy-Item -Path $BuiltExe -Destination $TargetExe -Force
    Write-Host "Success! copied to: $TargetExe" -ForegroundColor Green
}
catch {
    Write-Error "Failed to move executable to Downloads. $_"
    exit 1
}

Write-Host "`n[5/5] Done!" -ForegroundColor Cyan
Write-Host "You can now run SwitchCraft from your Downloads folder." -ForegroundColor Green
Write-Host "Path: $TargetExe"

# 5. Launch
Write-Host "`n[Auto-Launch] Starting $ProcessName..." -ForegroundColor Green
Start-Process -FilePath $TargetExe
