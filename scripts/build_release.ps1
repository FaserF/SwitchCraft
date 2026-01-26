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
    [switch]$LocalDev,
    [int]$BuildNumber = 0
)

$ErrorActionPreference = "Stop"

# --- Capture Build Start Time ---
$BuildStartTime = Get-Date
$BuildStartTimeString = $BuildStartTime.ToString("yyyy-MM-dd HH:mm:ss")

# --- OS Detection (Use custom variable names to avoid read-only conflicts) ---
$IsWinBuild = $env:OS -match 'Windows_NT' -or $PSVersionTable.Platform -eq 'Win32NT'
$IsLinBuild = $PSVersionTable.Platform -eq 'Unix' -and -not ($IsMacBuild = (uname) -eq 'Darwin')
$IsMacBuild = $IsMacBuild -or ($PSVersionTable.Platform -eq 'Unix' -and (uname) -eq 'Darwin')


Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SwitchCraft Release Builder            " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Build started at: $BuildStartTimeString" -ForegroundColor Gray
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

# --- Version Extraction ---
function Extract-VersionInfo {
    param(
        [string]$VersionString,
        [int]$BuildNum = 0
    )
    # Extract numeric version only (remove .dev0, +build, -dev, etc.) for VersionInfoVersion
    # Pattern: extract MAJOR.MINOR.PATCH from any version format
    $Numeric = if ($VersionString -match '^(\d+\.\d+\.\d+)') { $Matches[1] } else { $VersionString -replace '[^0-9.].*', '' }
    # VersionInfoVersion requires 4 numeric components (Major.Minor.Patch.Build)
    $Info = "$Numeric.$BuildNum"
    return @{
        Full = $VersionString
        Numeric = $Numeric
        Info = $Info
    }
}

$PyProjectFile = Join-Path $RepoRoot "pyproject.toml"
# Fallback version if extraction fails (can be overridden via env variable)
# Normalize and validate the fallback version
$RawFallbackVersion = if ($env:SWITCHCRAFT_VERSION) { $env:SWITCHCRAFT_VERSION } else { "2026.1.5" }
# Strip common prefixes like "v" and whitespace
$CleanedFallbackVersion = $RawFallbackVersion.Trim() -replace '^v', ''
# Extract version info from cleaned value
$FallbackVersionInfo = Extract-VersionInfo -VersionString $CleanedFallbackVersion -BuildNum $BuildNumber
# Validate that the numeric component is non-empty and matches MAJOR.MINOR.PATCH pattern
$IsValidFallback = -not [string]::IsNullOrWhiteSpace($FallbackVersionInfo.Numeric) -and
                   $FallbackVersionInfo.Numeric -match '^\d+\.\d+\.\d+$'
if (-not $IsValidFallback) {
    Write-Warning "Fallback version from SWITCHCRAFT_VERSION is malformed (got: '$($FallbackVersionInfo.Numeric)'), expected MAJOR.MINOR.PATCH format. Using hardcoded default: 2026.1.5"
    $FallbackVersion = "2026.1.5"
    $VersionInfo = Extract-VersionInfo -VersionString $FallbackVersion -BuildNum $BuildNumber
} else {
    $FallbackVersion = $CleanedFallbackVersion
    $VersionInfo = $FallbackVersionInfo
}
# Ensure Info still appends a fourth component (Build number)
if (-not $VersionInfo.Info -match '\.\d+$') {
    $VersionInfo.Info = "$($VersionInfo.Numeric).$BuildNumber"
}
$AppVersion = $VersionInfo.Full
$AppVersionNumeric = $VersionInfo.Numeric
$AppVersionInfo = $VersionInfo.Info

if (Test-Path $PyProjectFile) {
    try {
        $VersionLine = Get-Content -Path $PyProjectFile | Select-String "version = " | Select-Object -First 1
        if ($VersionLine -match 'version = "(.*)"') {
            $VersionInfo = Extract-VersionInfo -VersionString $Matches[1] -BuildNum $BuildNumber
            # Validate that the parsed version is non-empty and well-formed (MAJOR.MINOR.PATCH format)
            $IsValidVersion = -not [string]::IsNullOrWhiteSpace($VersionInfo.Numeric) -and
                              $VersionInfo.Numeric -match '^\d+\.\d+\.\d+$'
            if (-not $IsValidVersion) {
                Write-Warning "Parsed version from pyproject.toml is malformed (got: '$($VersionInfo.Numeric)'), expected MAJOR.MINOR.PATCH format. Using fallback: $FallbackVersion"
                $VersionInfo = Extract-VersionInfo -VersionString $FallbackVersion -BuildNum $BuildNumber
            }
            $AppVersion = $VersionInfo.Full
            $AppVersionNumeric = $VersionInfo.Numeric
            $AppVersionInfo = $VersionInfo.Info
            Write-Host "Detected Version: $AppVersion (Numeric base: $AppVersionNumeric, Info: $AppVersionInfo)" -ForegroundColor Cyan
        } else {
            Write-Warning "Could not parse version from pyproject.toml, using fallback: $AppVersion"
        }
    } catch {
        Write-Warning "Failed to extract version from pyproject.toml: $_, using fallback: $AppVersion"
    }
} else {
    Write-Warning "pyproject.toml not found, using fallback version: $AppVersion"
}

# --- Local Dev Versioning ---
$IsCI = $env:CI -or $env:GITHUB_ACTIONS
if (-not $IsCI -and (Test-Path (Join-Path $RepoRoot ".git"))) {
    try {
        $GitCommit = (git rev-parse --short HEAD).Trim()
        if ($GitCommit) {
            # Append local dev suffix only if not already present
            if (-not ($AppVersion -like "*$GitCommit*")) {
                 # If version is already a dev version (has .dev), just append +commit if missing?
                 # Or typically we want "X.Y.Z.dev0+commit"
                 # If AppVersion is "2026.1.5", we make "2026.1.5.dev0+commit"
                 # If AppVersion is "2026.1.5.dev0+oldcommit", we might be in trouble, but assuming standard flow:

                 if ($AppVersion -match "dev\d+") {
                     # Already has dev tag, maybe just missing commit or has different one?
                     # Ideally we replace the existing build metadata?
                     # For safety/simplicity in this script: Don't append .dev0 again if it has dev match
                     $AppVersion = "$AppVersion+$GitCommit"
                 } else {
                     $AppVersion = "$AppVersion.dev0+$GitCommit"
                 }
                 Write-Host "Local Dev Build Detected: Appending commit hash $GitCommit" -ForegroundColor Cyan
                 Write-Host "New Version: $AppVersion" -ForegroundColor Cyan
            } else {
                 Write-Host "Local Dev Build: Version already contains current commit hash ($GitCommit). Skipping append." -ForegroundColor Gray
            }
        }
    } catch {
        Write-Warning "Failed to get git commit hash: $_"
    }
}


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

function Get-InnoSetupPath {
    $IsccPath = (Get-Command "iscc" -ErrorAction SilentlyContinue).Source
    if ($IsccPath) {
        Write-Host "Found Inno Setup in PATH: $IsccPath" -ForegroundColor Gray
        return $IsccPath
    }

    # Search in common installation paths for Inno Setup (multiple versions)
    $PossiblePaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 5\ISCC.exe"
    )
    foreach ($p in $PossiblePaths) {
        if (Test-Path $p) {
            Write-Host "Found Inno Setup at: $p" -ForegroundColor Gray
            return $p
        }
    }
    return $null
}

# --- 0. PREPARE ASSETS ---
Write-Host "`nGenerating Splash Screen..." -ForegroundColor Cyan
try {
    $SplashScript = Join-Path $RepoRoot "scripts/generate_splash.py"
    if (Test-Path $SplashScript) {
        if ($IsWinBuild) {
            python $SplashScript --version "v$AppVersion"
        }
        else {
            python3 $SplashScript --version "v$AppVersion"
        }
    } else {
        Write-Warning "Splash generation script not found at $SplashScript"
    }
} catch {
    Write-Warning "Failed to generate dynamic splash screen: $_. Using existing fallback."
}

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
        # Use Join-Path for cross-platform compatibility
        $ZipPattern = Join-Path $AddonAssetsDir "*.zip"
        # Wildcard expansion by Remove-Item
        if (Test-Path $ZipPattern) {
             Remove-Item $ZipPattern -Force -ErrorAction SilentlyContinue
        }
    }
}

# --- 1. BUILD MODERN (Flet) ---
if ($Modern) {
    $Spec = "switchcraft.spec"
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
    $IsccPath = Get-InnoSetupPath

    if ($IsccPath) {
        $ModernExe = Join-Path $DistDir "SwitchCraft.exe"
        $RenamedModern = Join-Path $DistDir "SwitchCraft-windows.exe"

        # Ensure we have a file named 'SwitchCraft.exe' for the Installer to bundle
        if (Test-Path $RenamedModern) {
            Copy-Item $RenamedModern $ModernExe -Force
        }

        if (Test-Path "switchcraft.iss") {
            Write-Host "Compiling Modern Installer..."
            & $IsccPath "/DMyAppVersion=$AppVersion" "/DMyAppVersionNumeric=$AppVersionNumeric" "/DMyAppVersionInfo=$AppVersionInfo" "switchcraft.iss" | Out-Null

            # Cleanup temporary SwitchCraft.exe used for bundling
            if (Test-Path $ModernExe) { Remove-Item $ModernExe -Force }

            # Get full path to created installer (OutputDir is "dist" in switchcraft_modern.iss)
            $InstallerPath = Join-Path (Resolve-Path "dist") "SwitchCraft-Setup.exe"
            if (Test-Path $InstallerPath) {
                Write-Host "Installer Created: $InstallerPath" -ForegroundColor Green
            } else {
                Write-Host "Installer Created: SwitchCraft-Setup.exe (in dist)" -ForegroundColor Green
            }
        }
    }
    else {
        Write-Warning "Inno Setup not found. Skipping installers."
        Write-Host "`nTo build installers, please install Inno Setup:" -ForegroundColor Yellow
        Write-Host "  - Download from: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
        Write-Host "  - Or install via winget: winget install JRSoftware.InnoSetup" -ForegroundColor Yellow
        Write-Host "  - Or install via chocolatey: choco install innosetup" -ForegroundColor Yellow

        # Offer to install via winget if available (only in interactive sessions)
        if (-not $env:CI -and -not $env:GITHUB_ACTIONS) {
            $wingetAvailable = (Get-Command "winget" -ErrorAction SilentlyContinue)
            if ($wingetAvailable) {
                $response = Read-Host "`nWould you like to install Inno Setup via winget now? (y/N)"
                if ($response -in 'y','Y') {
                    Write-Host "Installing Inno Setup via winget..." -ForegroundColor Cyan
                    try {
                        winget install --id JRSoftware.InnoSetup --silent --accept-package-agreements --accept-source-agreements
                        Write-Host "Inno Setup installed successfully. Please run the build script again." -ForegroundColor Green
                    } catch {
                        Write-Warning "Failed to install Inno Setup via winget: $_"
                    }
                }
            }
        } else {
            Write-Host "Skipping interactive Inno Setup install in CI." -ForegroundColor Yellow
        }
    }
}

# --- 6. BUILD LEGACY (Tkinter) - LAST as requested ---
if ($Legacy -and $IsWinBuild) {
    Write-Host "`nBuilding Legacy GUI..." -ForegroundColor Cyan
    Run-PyInstaller -SpecFile "switchcraft_legacy.spec" -Name "Legacy App"

    if ($Installer) {
        Write-Host "`nBuilding Legacy Installer..." -ForegroundColor Cyan
        $IsccPath = Get-InnoSetupPath
        if ($IsccPath -and (Test-Path "switchcraft_legacy.iss")) {
            & $IsccPath "/DMyAppVersion=$AppVersion" "/DMyAppVersionNumeric=$AppVersionNumeric" "/DMyAppVersionInfo=$AppVersionInfo" "switchcraft_legacy.iss" | Out-Null
            # Get full path to created installer (OutputDir is "dist" in switchcraft_legacy.iss)
            $LegacyInstallerPath = Join-Path (Resolve-Path "dist") "SwitchCraft-Legacy-Setup.exe"
            if (Test-Path $LegacyInstallerPath) {
                Write-Host "Installer Created: $LegacyInstallerPath" -ForegroundColor Green
            } else {
                Write-Host "Installer Created: SwitchCraft-Legacy-Setup.exe (in dist)" -ForegroundColor Green
            }
        }
    }
}

# --- 7. CLEANUP / RESTORE SPLASH ---
Write-Host "`nRestoring original Splash Screen..." -ForegroundColor Cyan
try {
    $SplashScript = Join-Path $RepoRoot "scripts/generate_splash.py"
    if (Test-Path $SplashScript) {
        if ($IsWinBuild) {
            python $SplashScript --restore
        }
        else {
            python3 $SplashScript --restore
        }
    }
} catch {
    Write-Warning "Failed to restore splash screen: $_"
}

# --- Capture Build End Time and Calculate Duration ---
$BuildEndTime = Get-Date
$BuildEndTimeString = $BuildEndTime.ToString("yyyy-MM-dd HH:mm:ss")
$BuildDuration = $BuildEndTime - $BuildStartTime
$DurationString = "{0:D2}:{1:D2}:{2:D2}" -f $BuildDuration.Hours, $BuildDuration.Minutes, $BuildDuration.Seconds

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Build Process Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Build started at:  $BuildStartTimeString" -ForegroundColor Gray
Write-Host "Build ended at:    $BuildEndTimeString" -ForegroundColor Gray
Write-Host "Total duration:    $DurationString" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

# --- Notification ---
if ($IsWinBuild) {
    $toastSent = $false

    # Method 1: Try BurntToast module (if installed)
    try {
        if (Get-Module -ListAvailable -Name BurntToast -ErrorAction SilentlyContinue) {
            Import-Module BurntToast -ErrorAction Stop
            New-BurntToastNotification -Text "SwitchCraft Build", "Build process finished successfully."
            $toastSent = $true
        }
    } catch {
        # BurntToast failed, continue to fallback
    }

    # Method 2: Just beep (WinRT is unreliable on PS7+)
    if (-not $toastSent) {
        try {
            [System.Console]::Beep(1000, 300)
        } catch {
            # Beep failed, ignore
        }
    }

    # --- Launch Prompt ---
    $BuiltExe = ""
    if (Test-Path "$DistDir\SwitchCraft-windows.exe") {
        $BuiltExe = "$DistDir\SwitchCraft-windows.exe"
    } elseif (Test-Path "$DistDir\SwitchCraft-Legacy.exe") {
        $BuiltExe = "$DistDir\SwitchCraft-Legacy.exe"
    }

    if ($BuiltExe) {
        Write-Host "`nBuild Complete!" -ForegroundColor Green
        $response = Read-Host "Would you like to start SwitchCraft now? (y/N)"
        if ($response -match "^[yY]$") {
             Write-Host "Launching SwitchCraft..." -ForegroundColor Green
             Start-Process $BuiltExe
        }
    }
}
