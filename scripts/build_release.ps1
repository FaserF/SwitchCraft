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
    [switch]$Installer,
    [switch]$All
)

$ErrorActionPreference = "Stop"

# Handle -All flag
if ($All) {
    $Modern = $true
    $Legacy = $true
    $Cli = $true
    $Installer = $true
}

# Default behavior: If no specific target provided, build Modern (Standard)
if (-not $Modern -and -not $Legacy -and -not $Cli -and -not $Pip -and -not $Installer) {
    Write-Host "No specific target variables provided. Defaulting to Modern GUI." -ForegroundColor Cyan
    Write-Host "TIP: Use '.\scripts\build_release.ps1 -All' to build Modern, Legacy, CLI, and Installer at once." -ForegroundColor Green
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
Write-Host "  INSTALLER       : $Installer" -ForegroundColor Gray
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
$ProcessNames = @("SwitchCraft-new-Test", "SwitchCraft-windows", "SwitchCraft-CLI")
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

# 1b. SELECTIVE CLEANUP & RENAMING
$ArtifactMap = @{
    "Modern" = "$RepoRoot\dist\SwitchCraft-new-Test.exe"
    "Legacy" = "$RepoRoot\dist\SwitchCraft-windows.exe"
    "Cli"    = "$RepoRoot\dist\SwitchCraft-CLI.exe"
}

foreach ($Key in $ArtifactMap.Keys) {
    $Art = $ArtifactMap[$Key]
    if (Test-Path $Art) {
        # Determine if this specific file is a target of the current build
        $IsTarget = $false
        if ($Key -eq "Modern" -and $Modern) { $IsTarget = $true }
        if ($Key -eq "Legacy" -and $Legacy) { $IsTarget = $true }
        if ($Key -eq "Cli"    -and $Cli)    { $IsTarget = $true }

        if ($IsTarget) {
            # Delete target before building
            try {
                Write-Host "Deleting target artifact for rebuild: $Art" -ForegroundColor Gray
                Remove-Item $Art -Force -ErrorAction Stop
            } catch {
                 Write-Error "CRITICAL: Cannot remove $Art. The file is locked by another process."
                 Write-Error "Please close SwitchCraft manually and try again."
                 exit 1
            }
        } else {
            # Rename existing non-targets to _old
            $OldName = $Art -replace "\.exe$", "_old.exe"
            try {
                if (Test-Path $OldName) { Remove-Item $OldName -Force } # Remove previous _old
                Move-Item $Art $OldName -Force
                Write-Host "Archived existing $Key version to _old.exe." -ForegroundColor Gray
            } catch {
                Write-Warning "Could not rename $Art to $OldName. It might be in use."
            }
        }
    }
}

# Helper Function for Notifications
function Send-BuildNotification {
    param([string]$Title, [string]$Message)
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $notif = New-Object System.Windows.Forms.NotifyIcon
        $notif.Icon = [System.Drawing.SystemIcons]::Information
        $notif.Visible = $true
        $notif.ShowBalloonTip(5000, $Title, $Message, [System.Windows.Forms.ToolTipIcon]::Info)
        Start-Sleep -Seconds 1
        $notif.Dispose()
    } catch {
        Write-Warning "Could not send Windows notification: $_"
    }
}

$ArtifactCount = 0

# 2. MODERN GUI (Flet)
if ($Modern) {
    Write-Host "`n[MODERN] Building Flet GUI..." -ForegroundColor Yellow
    try {
        python -m pip install ".[modern]"
        python -m PyInstaller switchcraft_modern.spec --clean --noconfirm

        $BuiltModern = "$RepoRoot\dist\SwitchCraft-new-Test.exe"
        if (Test-Path $BuiltModern) {
            Write-Host "Success! Modern GUI built at: $BuiltModern" -ForegroundColor Green
            Send-BuildNotification "SwitchCraft Build" "Modern GUI (Flet) successfully generated."
            $ArtifactCount++

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

        $BuiltLegacy = "$RepoRoot\dist\SwitchCraft-windows.exe"
        if (Test-Path $BuiltLegacy) {
            Write-Host "Success! Legacy GUI built at: $BuiltLegacy" -ForegroundColor Green
            Send-BuildNotification "SwitchCraft Build" "Legacy GUI (Tkinter) successfully generated."
            $ArtifactCount++
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
            Send-BuildNotification "SwitchCraft Build" "CLI Executable successfully generated."
            $ArtifactCount++
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
    Send-BuildNotification "SwitchCraft Build" "PIP Package successfully generated."
    $ArtifactCount++
}

# 6. INNO SETUP INSTALLER
if ($Installer) {
    Write-Host "`n[INSTALLER] Building Windows Installer (Inno Setup)..." -ForegroundColor Yellow

    # Check if Legacy EXE exists (required for installer)
    $LegacyExe = "$RepoRoot\dist\SwitchCraft-windows.exe"
    if (-not (Test-Path $LegacyExe)) {
        Write-Warning "Legacy EXE not found at $LegacyExe. Building Legacy first..."
        python -m pip install ".[gui]"
        python -m PyInstaller switchcraft_legacy.spec --clean --noconfirm
    }

    # Check for Inno Setup
    $IsccPath = $null
    $PossiblePaths = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        (Get-Command "iscc" -ErrorAction SilentlyContinue).Source
    )

    foreach ($Path in $PossiblePaths) {
        if ($Path -and (Test-Path $Path)) {
            $IsccPath = $Path
            break
        }
    }

    if (-not $IsccPath) {
        Write-Error "Inno Setup not found. Please install Inno Setup 6 from https://jrsoftware.org/isinfo.php"
        exit 1
    }

    Write-Host "Using Inno Setup: $IsccPath" -ForegroundColor Gray

    # Check for ICO file, convert if needed
    $IcoFile = "$RepoRoot\switchcraft_logo.ico"
    if (-not (Test-Path $IcoFile)) {
        Write-Host "ICO file not found. Checking for ImageMagick..." -ForegroundColor Yellow
        if (Get-Command "magick" -ErrorAction SilentlyContinue) {
            magick "$RepoRoot\images\switchcraft_logo.png" -define icon:auto-resize=256,128,64,48,32,16 $IcoFile
            Write-Host "Created ICO file." -ForegroundColor Green
        } else {
            Write-Warning "ImageMagick not found. Using PNG as fallback (may cause issues)."
        }
    }

    # Build installer
    try {
        & $IsccPath "$RepoRoot\switchcraft.iss"
        $InstallerPath = "$RepoRoot\dist\SwitchCraft-Setup.exe"
        if (Test-Path $InstallerPath) {
            Write-Host "Success! Installer built at: $InstallerPath" -ForegroundColor Green
            Send-BuildNotification "SwitchCraft Build" "Windows Installer successfully generated."
            $ArtifactCount++
        } else {
            Write-Error "Installer output missing!"
        }
    } catch {
        Write-Error "Installer Build Failed: $_"
        exit 1
    }
}

Write-Host "`nAll Tasks Complete." -ForegroundColor Cyan
Send-BuildNotification "SwitchCraft Release Ready" "The complete build process finished. $ArtifactCount artifacts generated."

Write-Host "`nDone!" -ForegroundColor Cyan
