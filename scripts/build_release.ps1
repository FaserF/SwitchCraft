<#
.SYNOPSIS
    Builds SwitchCraft releases with modular options.

.DESCRIPTION
    This script builds the SwitchCraft project. You can choose to build the
    Standard GUI Executable, the CLI-Only Executable, or the Python Pip Package (Wheel).

    If no parameters are provided, it defaults to building ONLY the GUI version.

.PARAMETER Gui
    Builds the Standard GUI application (SwitchCraft.exe). Default if no other flags used.

.PARAMETER Cli
    Builds the CLI-Only application (SwitchCraft-CLI.exe).

.PARAMETER Pip
    Builds the Python Package (.whl and .tar.gz).

.EXAMPLE
    .\build_release.ps1
    Builds only the GUI version.

.EXAMPLE
    .\build_release.ps1 -Cli
    Builds only the CLI version.

.EXAMPLE
    .\build_release.ps1 -Gui -Cli
    Builds both versions.

.NOTES
    File Name      : build_release.ps1
    Author         : SwitchCraft Team
#>

param (
    [switch]$Gui,
    [switch]$Cli,
    [switch]$Pip
)

$ErrorActionPreference = "Stop"

# Default behavior: If no switches provided, enable GUI
if (-not $Gui -and -not $Cli -and -not $Pip) {
    Write-Host "No parameters provided. Defaulting to GUI build." -ForegroundColor Cyan
    $Gui = $true
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SwitchCraft Release Builder (Windows)  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Modes Enabled:" -ForegroundColor Gray
Write-Host "  GUI : $Gui" -ForegroundColor Gray
Write-Host "  CLI : $Cli" -ForegroundColor Gray
Write-Host "  PIP : $Pip" -ForegroundColor Gray

# Check for Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.9+"
    exit 1
}

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot
Write-Host "Project Root: $RepoRoot" -ForegroundColor Gray

$DownloadsDir = [System.Environment]::GetFolderPath("UserProfile") + "\Downloads"

# 0. Cleanup Running Processes
Write-Host "`n[Checking for running instances...]" -ForegroundColor Yellow
$ProcessNames = @("SwitchCraft", "SwitchCraft-CLI")
foreach ($ProcessName in $ProcessNames) {
    if ($Gui -or $Cli) { # Only strict check needed if we are overwriting EXEs
        $RunningProcesses = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
        if ($RunningProcesses) {
            Write-Host "Found running instance(s) of $ProcessName. Terminating..." -ForegroundColor Magenta
            $RunningProcesses | Stop-Process -Force
            Start-Sleep -Seconds 2
        }
    }
}

# 1. PIP BUILD
if ($Pip) {
    Write-Host "`n[PIP] Building Python Package (Wheel)..." -ForegroundColor Yellow
    try {
        python -m pip install --upgrade build
        python -m build

        # Move artifacts
        $DistDir = "$RepoRoot\dist"
        $Wheels = Get-ChildItem -Path $DistDir -Filter "*.whl"
        $Tars = Get-ChildItem -Path $DistDir -Filter "*.tar.gz"

        foreach ($File in $Wheels + $Tars) {
           Copy-Item -Path $File.FullName -Destination $DownloadsDir -Force
           Write-Host "Copied to Downloads: $($File.Name)" -ForegroundColor Green
        }
    }
    catch {
        Write-Error "Pip build failed. $_"
        exit 1
    }
}

# 2. GUI BUILD
if ($Gui) {
    Write-Host "`n[GUI] Installing Dependencies..." -ForegroundColor Yellow
    try {
        python -m pip install --upgrade pyinstaller
        python -m pip install ".[gui]"
    }
    catch {
        Write-Error "Failed to install GUI dependencies. $_"
        exit 1
    }

    Write-Host "`n[GUI] Building Executable..." -ForegroundColor Yellow
    try {
        python -m PyInstaller switchcraft.spec --clean --noconfirm

        $BuiltGui = "$RepoRoot\dist\SwitchCraft.exe"
        if (Test-Path $BuiltGui) {
            $TargetGui = Join-Path $DownloadsDir "SwitchCraft.exe"
            Copy-Item -Path $BuiltGui -Destination $TargetGui -Force
            Write-Host "Success! GUI Copied to: $TargetGui" -ForegroundColor Green

            # Auto-launch only if standalone GUI build
            if (-not $Cli -and -not $Pip) {
                 Write-Host "[Auto-Launch] Starting SwitchCraft..." -ForegroundColor Green
                 Start-Process -FilePath $TargetGui
            }
        } else {
            Write-Error "GUI output missing at $BuiltGui"
        }
    }
    catch {
        Write-Error "GUI Build failed. $_"
        exit 1
    }
}

# 3. CLI BUILD
if ($Cli) {
    Write-Host "`n[CLI] Installing Dependencies..." -ForegroundColor Yellow
    # Note: Dependencies might already be there from GUI build, but let's ensure core is there.
    # We use pip install . because CLI doesn't need extras.
    try {
        python -m pip install --upgrade pyinstaller
        python -m pip install .
    }
    catch {
        Write-Error "Failed to install CLI dependencies. $_"
        exit 1
    }

    Write-Host "`n[CLI] Building Executable..." -ForegroundColor Yellow
    try {
        python -m PyInstaller switchcraft_cli.spec --clean --noconfirm

        $BuiltCli = "$RepoRoot\dist\SwitchCraft-CLI.exe"
        if (Test-Path $BuiltCli) {
            $TargetCli = Join-Path $DownloadsDir "SwitchCraft-CLI.exe"
            Copy-Item -Path $BuiltCli -Destination $TargetCli -Force
            Write-Host "Success! CLI Copied to: $TargetCli" -ForegroundColor Green

            # Verify
            Write-Host "Verifying CLI..." -ForegroundColor Gray
            & $TargetCli --help | Out-Null
            if ($LASTEXITCODE -eq 0) { Write-Host "Verification Passed." -ForegroundColor Green }
        } else {
            Write-Error "CLI output missing at $BuiltCli"
        }
    }
    catch {
        Write-Error "CLI Build failed. $_"
        exit 1
    }
}

Write-Host "`nDone!" -ForegroundColor Cyan
