<#
.SYNOPSIS
    Builds SwitchCraft releases for Windows, Linux, and macOS.

.DESCRIPTION
    Universal build script for SwitchCraft.
    Supports building:
    - Modern GUI (Flet) - Portable & Installer (Windows only for Installer)
    - Legacy GUI (Tkinter) - Portable & Installer (Windows only, built last)
    - CLI - Portable
    - Addons (Zip)
    - Pip Package (Wheel)

    This script is designed to run on PowerShell 7+ (cross-platform) or PowerShell 5.1 (Windows).
    It detects the running OS and builds compatible artifacts.

.PARAMETER Modern
    Build Modern GUI (Flet).

.PARAMETER Legacy
    Build Legacy GUI (Tkinter). Windows Only.

.PARAMETER Cli
    Build CLI version.

.PARAMETER Pip
    Build Python Wheel.

.PARAMETER Addons
    Package Addons into Zips.

.PARAMETER Installer
    Build Windows Installers (Inno Setup). Requires Windows and Inno Setup.

.PARAMETER All
    Build EVERYTHING supported on the current OS.

.EXAMPLE
    .\build_release.ps1 -All
    Builds everything possible on current OS.

.EXAMPLE
    .\build_release.ps1 -Modern -Installer
    Builds Modern Portable App and Installer.
#>

param (
    [switch]$Modern,
    [switch]$Legacy,
    [switch]$Cli,
    [switch]$Pip,
    [switch]$Addons,
    [switch]$Installer,
    [switch]$All,
    [switch]$LocalDev
)

$ErrorActionPreference = "Stop"

# --- OS Detection (Use custom variable names to avoid read-only conflicts) ---
$IsWinBuild = $env:OS -match 'Windows_NT' -or $PSVersionTable.Platform -eq 'Win32NT'
$IsLinBuild = $PSVersionTable.Platform -eq 'Unix' -and -not ($IsMacBuild = (uname) -eq 'Darwin')
$IsMacBuild = $IsMacBuild -or ($PSVersionTable.Platform -eq 'Unix' -and (uname) -eq 'Darwin')

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SwitchCraft Release Builder            " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
if ($IsWinBuild) { Write-Host "Platform: Windows" -ForegroundColor Green }
elseif ($IsLinBuild) { Write-Host "Platform: Linux" -ForegroundColor Green }
elseif ($IsMacBuild) { Write-Host "Platform: MacOS" -ForegroundColor Green }

# --- Param Logic ---
if ($All) {
    if ($IsWinBuild) {
        $Modern = $true
        $Legacy = $true
        $Cli = $true
        $Pip = $true
        $Addons = $true
        $Installer = $true
    }
    else {
        # Linux/Mac only support Modern GUI and CLI/Pip
        $Modern = $true
        $Cli = $true
        $Pip = $true
        $Addons = $true
    }
}

# Default if nothing selected
if (-not $Modern -and -not $Legacy -and -not $Cli -and -not $Pip -and -not $Installer -and -not $Addons) {
    Write-Host "No targets selected. Defaulting to Modern GUI." -ForegroundColor Yellow
    $Modern = $true
}

# --- Validation ---
if ($Installer -and -not $IsWinBuild) {
    Write-Warning "Installers (Inno Setup) can only be built on Windows. Skipping Installer step."
    $Installer = $false
}
if ($Legacy -and -not $IsWinBuild) {
    Write-Warning "Legacy GUI is Windows-Only. Skipping Legacy specific steps on non-Windows platforms."
    $Legacy = $false
}

# --- Build Overview ---
$BuildPlan = @(
    @{ Name = "Modern GUI (Portable)"; Val = $Modern; Param = "-Modern" },
    @{ Name = "Legacy GUI (Portable)"; Val = $Legacy; Param = "-Legacy" },
    @{ Name = "CLI Tool"; Val = $Cli; Param = "-Cli" },
    @{ Name = "Addons (Zips)"; Val = $Addons; Param = "-Addons" },
    @{ Name = "Python Wheel"; Val = $Pip; Param = "-Pip" },
    @{ Name = "Windows Installers"; Val = $Installer; Param = "-Installer" }
)

Write-Host "`nBuild Plan:" -ForegroundColor Gray
foreach ($Target in $BuildPlan) {
    if ($Target.Val) {
        Write-Host "  [x] $($Target.Name.PadRight(25)) (via $($Target.Param))" -ForegroundColor White
    }
    else {
        Write-Host "  [ ] $($Target.Name.PadRight(25)) (hint: $($Target.Param))" -ForegroundColor Gray
    }
}
Write-Host "------------------------------------------" -ForegroundColor Gray

# --- Force Close SwitchCraft ---
if ($IsWinBuild) {
    Write-Host "`nStopping any running SwitchCraft processes to prevent file locks..." -ForegroundColor Yellow
    # Use taskkill for more robust tree killing (/T) and forceful termination (/F)
    # Redirect stderr to null to avoid noise if process not found
    try {
        taskkill /F /IM SwitchCraft.exe /T 2>&1 | Out-Null
        taskkill /F /IM SwitchCraft-windows.exe /T 2>&1 | Out-Null
        # Give it a second to release locks
        Start-Sleep -Seconds 1
    } catch {
        # Ignore errors if process not found
    }
}

# --- Setup Paths ---
$RepoRoot = Resolve-Path "$PSScriptRoot/.."
Set-Location $RepoRoot
Write-Host "Project Root: $RepoRoot" -ForegroundColor Gray

# Setup Dist dir
$DistDir = Join-Path $RepoRoot "dist"
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
}

# --- Cleanup Phase ---
Write-Host "`nCleaning up previous builds for selected targets..." -ForegroundColor Gray
$TargetFiles = @()
if ($Modern) {
    $TargetFiles += "SwitchCraft.exe", "SwitchCraft-windows.exe", "SwitchCraft-linux", "SwitchCraft-macos", "SwitchCraft"
}
if ($Legacy) {
    $TargetFiles += "SwitchCraft-Legacy.exe", "SwitchCraft-Legacy-Setup.exe"
}
if ($Cli) {
    $TargetFiles += "SwitchCraft-CLI.exe", "SwitchCraft-CLI-windows.exe"
}
if ($Installer) {
    $TargetFiles += "SwitchCraft-Setup.exe"
}

foreach ($f in $TargetFiles) {
    if (Test-Path (Join-Path $DistDir $f)) {
        Remove-Item (Join-Path $DistDir $f) -Force -Recurse -ErrorAction SilentlyContinue
    }
}

# --- Helper Functions ---
function Run-PyInstaller {
    param(
        [string]$SpecFile,
        [string]$Name
    )
    if (Test-Path $SpecFile) {
        Write-Host "`nBuilding $Name..." -ForegroundColor Cyan
        try {
            if ($IsWinBuild) {
                python -m PyInstaller $SpecFile --noconfirm --clean
            }
            else {
                python3 -m PyInstaller $SpecFile --noconfirm --clean
            }
            if ($LASTEXITCODE -ne 0) { throw "$Name build failed with code $LASTEXITCODE" }
            Write-Host "Built $Name successfully." -ForegroundColor Green
        }
        catch {
            Write-Error "Build Error ($Name): $_"
            exit 1
        }
    }
    else {
        Write-Error "Spec file not found: $SpecFile"
    }
}

# --- 0. PREPARE ASSETS ---
if ($LocalDev) {
    Write-Host "`nGenerating Bundled Addons (Local Dev Mode)..." -ForegroundColor Cyan
    try {
        if ($IsWinBuild) {
            python src/generate_addons.py
        }
        else {
            python3 src/generate_addons.py
        }
        if ($LASTEXITCODE -ne 0) { throw "Addon generation failed with code $LASTEXITCODE" }
    }
    catch {
        Write-Warning "Failed to generate addons: $_"
    }
}
else {
    # Clean up bundled addons to ensure clean release build
    $AddonAssetsDir = Join-Path $RepoRoot "src/switchcraft/assets/addons"
    if (Test-Path $AddonAssetsDir) {
        Write-Host "Cleaning bundled addons for Release Build..." -ForegroundColor Yellow
        Remove-Item "$AddonAssetsDir\*.zip" -Force -ErrorAction SilentlyContinue
    }
}

# --- 1. BUILD MODERN (Flet) ---
if ($Modern) {
    $Spec = "switchcraft_modern.spec"
    Run-PyInstaller -SpecFile $Spec -Name "Modern App"

    # Rename Artifact based on OS to match naming in README
    # Windows: SwitchCraft.exe (Standard) -> SwitchCraft-windows.exe (Portable)
    if ($IsWinBuild) {
        $Src = Join-Path $DistDir "SwitchCraft.exe"
        $Dest = Join-Path $DistDir "SwitchCraft-windows.exe"
        if (Test-Path $Src) {
            # We RENAME instead of Copy to avoid confusion of having two identical exes
            Move-Item $Src $Dest -Force
            Write-Host "Modern Portable created: $Dest" -ForegroundColor Green
        }
    }
    elseif ($IsLinBuild) {
        $Src = Join-Path $DistDir "SwitchCraft"
        $Dest = Join-Path $DistDir "SwitchCraft-linux"
        if (Test-Path $Src) { Move-Item $Src $Dest -Force; Write-Host "Linux Binary created: $Dest" }
    }
    elseif ($IsMacBuild) {
        $Src = Join-Path $DistDir "SwitchCraft"
        $Dest = Join-Path $DistDir "SwitchCraft-macos"
        if (Test-Path $Src) { Move-Item $Src $Dest -Force; Write-Host "MacOS Binary created: $Dest" }
    }
}

# --- 2. BUILD CLI ---
if ($Cli) {
    $Spec = "switchcraft_cli.spec"
    Run-PyInstaller -SpecFile $Spec -Name "CLI"

    if ($IsWinBuild) {
        $Src = Join-Path $DistDir "SwitchCraft-CLI.exe"
        $Dest = Join-Path $DistDir "SwitchCraft-CLI-windows.exe"
        if (Test-Path $Src) { Move-Item $Src $Dest -Force }
    }
}

# --- 3. ADDONS ---
if ($Addons) {
    Write-Host "`nPackaging Addons..." -ForegroundColor Cyan
    $AddonList = @("switchcraft_advanced", "switchcraft_ai", "switchcraft_winget")
    foreach ($Ad in $AddonList) {
        $SrcPath = Join-Path $RepoRoot "src/$Ad"
        $ZipPath = Join-Path $DistDir "$Ad.zip"
        if (Test-Path $SrcPath) {
            Compress-Archive -Path $SrcPath -DestinationPath $ZipPath -Force
            Write-Host "Packed: $Ad.zip" -ForegroundColor Green
        }
        else {
            Write-Warning "Addon source not found: $SrcPath"
        }
    }
}

# --- 4. PIP PACKAGE ---
if ($Pip) {
    Write-Host "`nBuilding Pip Package..." -ForegroundColor Cyan
    if ($IsWinBuild) { python -m build } else { python3 -m build }
    if ($LASTEXITCODE -ne 0) { throw "Pip build failed with code $LASTEXITCODE" }
}

# --- 5. INSTALLERS (Windows Only) ---
if ($Installer -and $IsWinBuild) {
    Write-Host "`nBuilding Modern Installer..." -ForegroundColor Cyan
    $IsccPath = (Get-Command "iscc" -ErrorAction SilentlyContinue).Source
    if (-not $IsccPath) {
        $PossiblePaths = @("C:\Program Files (x86)\Inno Setup 6\ISCC.exe", "C:\Program Files\Inno Setup 6\ISCC.exe")
        foreach ($p in $PossiblePaths) { if (Test-Path $p) { $IsccPath = $p; break } }
    }

    if ($IsccPath) {
        $ModernExe = Join-Path $DistDir "SwitchCraft.exe"
        $RenamedModern = Join-Path $DistDir "SwitchCraft-windows.exe"

        # Ensure we have a file named 'SwitchCraft.exe' for the Installer to bundle
        if (Test-Path $RenamedModern) {
            Copy-Item $RenamedModern $ModernExe -Force
        }

        if (Test-Path "switchcraft_modern.iss") {
            Write-Host "Compiling Modern Installer..."
            & $IsccPath "switchcraft_modern.iss" | Out-Null

            # Cleanup temporary SwitchCraft.exe used for bundling
            if (Test-Path $ModernExe) { Remove-Item $ModernExe -Force }

            Write-Host "Installer Created: SwitchCraft-Setup.exe" -ForegroundColor Green
        }
    }
    else {
        Write-Warning "Inno Setup not found. Skipping installers."
    }
}

# --- 6. BUILD LEGACY (Tkinter) - LAST as requested ---
if ($Legacy -and $IsWinBuild) {
    Write-Host "`nBuilding Legacy GUI..." -ForegroundColor Cyan
    Run-PyInstaller -SpecFile "switchcraft_legacy.spec" -Name "Legacy App"

    if ($Installer) {
        Write-Host "`nBuilding Legacy Installer..." -ForegroundColor Cyan
        $IsccPath = (Get-Command "iscc" -ErrorAction SilentlyContinue).Source
        if (-not $IsccPath) {
            $PossiblePaths = @("C:\Program Files (x86)\Inno Setup 6\ISCC.exe", "C:\Program Files\Inno Setup 6\ISCC.exe")
            foreach ($p in $PossiblePaths) { if (Test-Path $p) { $IsccPath = $p; break } }
        }
        if ($IsccPath -and (Test-Path "switchcraft_legacy.iss")) {
            & $IsccPath "switchcraft_legacy.iss" | Out-Null
            Write-Host "Installer Created: SwitchCraft-Legacy-Setup.exe" -ForegroundColor Green
        }
    }
}

Write-Host "`nBuild Process Complete!" -ForegroundColor Cyan

# --- Notification ---
if ($IsWinBuild) {
    try {
        $ToastTitle = "SwitchCraft Builder"
        $ToastText = "Build completed successfully!"

        # Use PowerShell BurntToast if available, else standard Import-Module or raw XML?
        # Raw XML via Windows.UI.Notifications is standard on Win10/11 without extra modules.

        $code = @"
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Windows.Data.Xml.Dom;
using Windows.UI.Notifications;

namespace ToastNotify
{
    public class Toaster
    {
        public static void Show(string appId, string title, string message)
        {
            var template = ToastNotificationManager.GetTemplateContent(ToastTemplateType.ToastText02);
            var textNodes = template.GetElementsByTagName("text");
            textNodes[0].AppendChild(template.CreateTextNode(title));
            textNodes[1].AppendChild(template.CreateTextNode(message));

            var notifier = ToastNotificationManager.CreateToastNotifier(appId);
            var notification = new ToastNotification(template);
            notifier.Show(notification);
        }
    }
}
"@
        # Try to compile C# snippet for Toast if not already loaded (Simple method)
        # OR simpler: Just use New-BurntToastNotification if installed?
        # User requested "via Powershell in Windows". The cleanest dependency-free way is minimal P/Invoke or just Audio.
        # But let's try a simple visual method using 'msg' as backup or just sound:
        [System.Console]::Beep(1000, 300)

        # Attempt Toast via plain PS (Windows 10+)
        $XmlString = @"
<toast>
  <visual>
    <binding template=""ToastGeneric"">
      <text>SwitchCraft Build</text>
      <text>Build process finished successfully.</text>
    </binding>
  </visual>
</toast>
"@

        $AppId = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"

        $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        $null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]

        $Xml = [Windows.Data.Xml.Dom.XmlDocument]::new()
        $Xml.LoadXml($XmlString)
        $Toast = [Windows.UI.Notifications.ToastNotification]::new($Xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($Toast)

    } catch {
        Write-Warning "Could not trigger toast notification: $_"
    }
}
