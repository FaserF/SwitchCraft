param(
    [string]$InstallPath = "$env:LOCALAPPDATA\FaserF\SwitchCraft",
    [switch]$Silent,
    [switch]$Portable,
    [string]$Version = "latest"
)

$ErrorActionPreference = 'Stop'
$Repo = "FaserF/SwitchCraft"
$ApiUrl = "https://api.github.com/repos/$Repo/releases/latest"

Write-Host "🧙‍♂️  SwitchCraft Installer" -ForegroundColor Cyan

try {
    Write-Host "Fetching release info for: $Version..." -ForegroundColor Gray

    if ($Version -eq "latest") {
        $Release = Invoke-RestMethod -Uri $ApiUrl
    } else {
        $Release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/tags/$Version"
    }

    $Tag = $Release.tag_name
    Write-Host "Identified version: $Tag" -ForegroundColor Gray

    # Detect OS
    $IsWindows = $true
    $IsLinux = $false
    $IsMacOS = $false

    if ($PSVersionTable.PSVersion.Major -ge 6) {
        if ($IsWindows -and $env:OS -ne 'Windows_NT') { # PowerShell Core on non-Windows?
           # Better detection
           if ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Linux)) {
               $IsWindows = $false; $IsLinux = $true
           } elseif ([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::OSX)) {
               $IsWindows = $false; $IsMacOS = $true
           }
        }
    }

    # Determine Asset
    $Assets = $Release.assets
    $TargetAsset = $null
    $DownloadPath = ""
    $IsInstaller = $false

    if ($IsWindows) {
        if ($Portable) {
            $TargetAsset = $Assets | Where-Object { $_.name -like "*windows.exe" -and $_.name -notlike "*Setup.exe" } | Select-Object -First 1
            $DownloadPath = "$env:USERPROFILE\Desktop\SwitchCraft-$Tag.exe"
            $ModeName = "Portable Executable (Windows)"
        } else {
            # Try Installer First
            $TargetAsset = $Assets | Where-Object { $_.name -like "*Setup.exe" } | Select-Object -First 1
            if ($TargetAsset) {
                 $DownloadPath = "$env:TEMP\SwitchCraft-Setup.exe"
                 $ModeName = "Installer (Windows)"
                 $IsInstaller = $true
            } else {
                 Write-Warning "Setup.exe not found in release. Falling back to Portable version."
                 $TargetAsset = $Assets | Where-Object { $_.name -like "*windows.exe" } | Select-Object -First 1
                 $DownloadPath = "$env:USERPROFILE\Desktop\SwitchCraft-$Tag.exe"
                 $ModeName = "Portable Executable (Fallback)"
            }
        }
    } elseif ($IsLinux) {
        $TargetAsset = $Assets | Where-Object { $_.name -like "*linux*" } | Select-Object -First 1
        $DownloadPath = "./SwitchCraft-$Tag"
        $ModeName = "Binary (Linux)"
    } elseif ($IsMacOS) {
        $TargetAsset = $Assets | Where-Object { $_.name -like "*macos*" } | Select-Object -First 1
        $DownloadPath = "./SwitchCraft-$Tag"
        $ModeName = "Binary (MacOS)"
    } else {
        throw "Unsupported Operating System."
    }

    if (-not $TargetAsset) {
        throw "No suitable asset found for this platform in release $Tag."
    }

    $DownloadUrl = $TargetAsset.browser_download_url

    Write-Host "Downloading $ModeName..." -ForegroundColor Yellow
    Write-Host "URL: $DownloadUrl" -ForegroundColor Gray

    Invoke-WebRequest -Uri $DownloadUrl -OutFile $DownloadPath

    if ($IsWindows -and $IsInstaller) {
        Write-Host "Installing..." -ForegroundColor Green
        $ArgsList = "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
        if ($Silent) { $ArgsList += "/DEBUGMODE" } # Optional debug

        Start-Process -FilePath $DownloadPath -ArgumentList $ArgsList -Wait
        Write-Host "✅ Installation complete!" -ForegroundColor Green
        Write-Host "Run 'switchcraft' to start." -ForegroundColor Cyan
    } elseif ($IsWindows) {
         Write-Host "✅ Downloaded to: $DownloadPath" -ForegroundColor Green
    } else {
         # Linux/Mac
         try {
             if ($IsLinux -or $IsMacOS) {
                 chmod +x $DownloadPath
             }
         } catch {}
         Write-Host "✅ Downloaded to: $DownloadPath" -ForegroundColor Green
         Write-Host "You may need to run: chmod +x $DownloadPath" -ForegroundColor Gray
    }

} catch {
    Write-Error "Installation failed: $_"
    exit 1
}
