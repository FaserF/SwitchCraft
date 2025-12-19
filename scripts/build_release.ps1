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
    [switch]$Modern,
    [switch]$Legacy,
    [switch]$Cli,
    [switch]$Pip,
    [switch]$All
)

$ErrorActionPreference = "Stop"

# Handle -All flag
if ($All) {
    $Modern = $true
    $Legacy = $true
    $Cli = $true
}

# Default behavior: If no specific target provided, build Modern (Standard)
if (-not $Modern -and -not $Legacy -and -not $Cli -and -not $Pip) {
    Write-Host "No specific target variables provided. Defaulting to Modern GUI." -ForegroundColor Cyan
    Write-Host "TIP: Use '.\scripts\build_release.ps1 -All' to build Modern, Legacy, and CLI versions at once." -ForegroundColor Green
    $Modern = $true
    $AutoLaunch = $true
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SwitchCraft Release Builder (Windows)  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Modes Enabled:" -ForegroundColor Gray
Write-Host "  MODERN (Flet)   : $Modern" -ForegroundColor Gray
Write-Host "  LEGACY (Tkinter): $Legacy" -ForegroundColor Gray
Write-Host "  CLI             : $Cli" -ForegroundColor Gray
Write-Host "  PIP             : $Pip" -ForegroundColor Gray

# Check for Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.9+"
    exit 1
}

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot
Write-Host "Project Root: $RepoRoot" -ForegroundColor Gray

# 1. CLEANUP PROCESSES
$ProcessNames = @("SwitchCraft", "SwitchCraft-Legacy", "SwitchCraft-CLI")
foreach ($ProcessName in $ProcessNames) {
    try {
        $RunningProcesses = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
        if ($RunningProcesses) {
            Write-Host "Stopping running process: $ProcessName..." -ForegroundColor Yellow
            $RunningProcesses | Stop-Process -Force -PassThru | Wait-Process -Timeout 10
        }
    } catch {
        Write-Warning "Could not stop process $ProcessName. It might not be running or is stubborn."
    }
}
Start-Sleep -Seconds 1 # Give OS time to release file handles

# 1b. CLEANUP ARTIFACTS
$Artifacts = @(
    "$RepoRoot\dist\SwitchCraft.exe",
    "$RepoRoot\dist\SwitchCraft-Legacy.exe",
    "$RepoRoot\dist\SwitchCraft-CLI.exe"
)
foreach ($Art in $Artifacts) {
    if (Test-Path $Art) {
        try {
            Remove-Item $Art -Force -ErrorAction Stop
        } catch {
             Write-Error "CRITICAL: Cannot remove $Art. The file is locked by another process."
             Write-Error "Please close SwitchCraft manually and try again."
             exit 1
        }
    }
}

# 2. MODERN GUI (Flet)
if ($Modern) {
    Write-Host "`n[MODERN] Building Flet GUI..." -ForegroundColor Yellow
    try {
        python -m pip install ".[modern]"
        python -m PyInstaller switchcraft_modern.spec --clean --noconfirm

        $BuiltModern = "$RepoRoot\dist\SwitchCraft.exe"
        if (Test-Path $BuiltModern) {
            Write-Host "Success! Modern GUI built at: $BuiltModern" -ForegroundColor Green

            if ($AutoLaunch) {
                Write-Host "Auto-launching Modern GUI..." -ForegroundColor Green
                Start-Process -FilePath $BuiltModern
            }
        } else {
             Write-Error "Modern GUI output missing!"
        }
    } catch {
        Write-Error "Modern Build Failed: $_"
        exit 1
    }
}

# 3. LEGACY GUI (Tkinter)
if ($Legacy) {
    Write-Host "`n[LEGACY] Building Tkinter GUI..." -ForegroundColor Yellow
    try {
        python -m pip install ".[gui]"
        python -m PyInstaller switchcraft_legacy.spec --clean --noconfirm

        $BuiltLegacy = "$RepoRoot\dist\SwitchCraft-Legacy.exe"
        if (Test-Path $BuiltLegacy) {
            Write-Host "Success! Legacy GUI built at: $BuiltLegacy" -ForegroundColor Green
        } else {
             Write-Error "Legacy GUI output missing!"
        }
    } catch {
        Write-Error "Legacy Build Failed: $_"
        exit 1
    }
}

# 4. CLI BUILD
if ($Cli) {
    Write-Host "`n[CLI] Building CLI..." -ForegroundColor Yellow
    try {
        python -m pip install .
        python -m PyInstaller switchcraft_cli.spec --clean --noconfirm

        $BuiltCli = "$RepoRoot\dist\SwitchCraft-CLI.exe"
        if (Test-Path $BuiltCli) {
            Write-Host "Success! CLI built at: $BuiltCli" -ForegroundColor Green
            # Verify
            & $BuiltCli --help | Out-Null
        } else {
            Write-Error "CLI output missing!"
        }
    } catch {
        Write-Error "CLI Build Failed: $_"
        exit 1
    }
}

# 5. PIP BUILD
if ($Pip) {
    Write-Host "`n[PIP] Building Wheel..." -ForegroundColor Yellow
    python -m pip install --upgrade build
    python -m build
    Write-Host "Pip artifacts in dist/" -ForegroundColor Green
}

Write-Host "`nAll Tasks Complete." -ForegroundColor Cyan

Write-Host "`nDone!" -ForegroundColor Cyan
