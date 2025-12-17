<#
    .NOTES
    Created at 17.12.2025
    Fabian Seitz - PARI GmbH
    .DESCRIPTION
    Installerscript for SwitchCraft
    .OUTPUTS
    C:\ProgramData\Microsoft\IntuneManagementExtension\Logs\
    .EXAMPLE
    Installation:   "%systemroot%\sysnative\WindowsPowerShell\v1.0\powershell.exe" -noprofile -executionpolicy bypass -file .\SwitchCraft.ps1 -InstallMode Install -AdminPermissions
    Uninstallation: "%systemroot%\sysnative\WindowsPowerShell\v1.0\powershell.exe" -noprofile -executionpolicy bypass -file .\SwitchCraft.ps1 -InstallMode Uninstall -AdminPermissions
    .PARAMETER InstallMode
    Specifies the installation mode (install or uninstall)
    .PARAMETER logpath
    Specifies a custom folder location for the script log files (Default: see variable $logpath)
    WARNING: Seems to break Intune installation for unknown reason. Do not use a custom logpath for now!
    .PARAMETER -AdminPermissions
    Specifies if the script needs administration rights for permissions. If no administrator permissions are needed do not set this parameter
    .LINK
    https://github.com/pari-medical-holding-gmbh/Intune-packaging
#>

param(
    [Parameter(Mandatory = $True)] [ValidateSet("Install", "Uninstall", "install", "uninstall")] [Alias('install')] [String] $InstallMode,
    [Parameter(Mandatory = $False)] [Alias('Path')] [String] $logpath = "$env:ProgramData\Microsoft\IntuneManagementExtension\Logs\",
    [Parameter(Mandatory = $False)] [Switch] $AdminPermissions = $false
)
$ExitCode = 0
#$UserFeedback = "true"

# Check if Logfolder exists
If (!(test-path $logpath)) {
    New-Item -ItemType Directory -Force -Path $logpath >$null 2>&1
}

# Log Name will be Log Path provided above + ScriptName
$logpathfolder = $logpath
$logpath = $logpath + "PARI-App-System-" + $MyInvocation.MyCommand.Name + ".log"
$logpathAlternative = $logpath + "_alternative.log"

function Test-PathWritePermission {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    # First, check if the provided path exists and is a directory.
    # You can't write to a path that doesn't exist.
    if (-not (Test-Path -Path $Path -PathType Container)) {
        return $false
    }

    # Generate a unique name for a temporary file. A GUID is perfect for this.
    $TempFile = Join-Path -Path $Path -ChildPath ([System.Guid]::NewGuid().ToString() + ".tmp")

    try {
        # Attempt to create a new empty file.
        # -ErrorAction Stop is crucial. It turns a non-terminating error
        # into a terminating one, which is required to trigger the catch block.
        New-Item -Path $TempFile -ItemType File -ErrorAction Stop | Out-Null

        # If the command above succeeded, we have permission.
        # Clean up the temporary file immediately.
        Remove-Item -Path $TempFile -Force

        # Return true, indicating success.
        return $true
    }
    catch {
        # If any error occurred during New-Item (e.g., UnauthorizedAccessException),
        # the catch block is executed. This means we do not have write permissions.
        return $false
    }
}
$TestPathAccess = Test-PathWritePermission -Path $logpathfolder
if (-not $TestPathAccess) {
    $LogPathAlternativeFolder = "$env:SystemDrive\temp\"
    If (!(test-path $LogPathAlternativeFolder)) {
        New-Item -ItemType Directory -Force -Path $LogPathAlternativeFolder >$null 2>&1
    }
    Write-Warning "No write access to log path $logpathfolder . Writing it to the alternative log path instead:  $LogPathAlternativeFolder "
    $LogPath = $LogPathAlternativeFolder + "PARI-App-System-" + $MyInvocation.MyCommand.Name + ".log"
}

#Check Log file for file length and delete input if file input exceeded limit.
function CheckLogFile ($FilePath, $MaxLineLength) {
    # Check if the file exists
    if (Test-Path $FilePath) {
        # Read the content of the file
        $Lines = Get-Content $FilePath

        if ($Lines.Count -gt $MaxLineLength) {

            # Keep the last 3 lines
            $LinesToKeep = $Lines[-3..-1]

            # Clear content of the file
            Clear-Content $FilePath

            # Append the last three lines back to the file
            Add-Content -Path $FilePath -Value $LinesToKeep
            Write-ToLog -Warning 1 -LogText "Log content cleared, except the last 3 lines, due to exceeding maximum amount of lines."
        }
    }
}

##Log Creation Function
function Write-ToLog {
    param (
        [string]$Warning,
        [string]$LogText
    )
    if ($null -eq $Warning -Or $Warning -eq "1") {
        $WarningText = "INFO:   "
    }
    elseif ($Warning -eq "2") {
        $WarningText = "WARNING:"
    }
    elseif ($Warning -eq "3") {
        $WarningText = "ERROR:  "
    }
    else {
        $WarningText = "        "
    }
    $TimeStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    if ($Warning -eq "9") {
        Try {
            Add-Content $LogPath "$TimeStr || $WarningText || ##### $LogText #####" -ErrorAction Stop
        }
        Catch {
            Write-Warning "Cannot access log file $LogPath . Writing it to the alternative log file instead:  $LogPathAlternative "
            Add-Content $LogPathAlternative "$TimeStr || $WarningText || ##### $LogText #####"
        }
    }
    else {
        Try {
            Add-Content $LogPath "$TimeStr || $WarningText || $LogText" -ErrorAction Stop
        }
        Catch {
            Write-Warning "Cannot access log file $LogPath . Writing it to the alternative log file instead:  $LogPathAlternative "
            Add-Content $LogPathAlternative "$TimeStr || $WarningText || $LogText"
        }
    }
}

# Default Log Input
$DateTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-ToLog -Warning 9 -LogText "Starting Log File of App Installation $($MyInvocation.MyCommand.Name) from $DateTime"
Write-ToLog -Warning 9 -LogText "############"
Write-ToLog -Warning 1 -LogText "Work Directory: $(Get-Location)"
CheckLogFile -FilePath $LogPath -MaxLineLength 200

#Check for Administrator permissions if needed
if (($AdminPermissions -eq $true)) {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not ($currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))) {
        Write-ToLog -Warning 3 -LogText "Current user has no administrator permissions, but administrator permissions are needed due to parameter -AdminPermissions $AdminPermissions"
        Exit 2
    }
}

function Start-Process-Function {
    param(
        [Parameter(Mandatory = $False, Position = 0, ValueFromPipeline = $false)]
        [System.String]
        $FilePath,

        [Parameter(Mandatory = $False, Position = 1, ValueFromPipeline = $false)]
        [System.String]
        $ArgumentList
    )

    If (test-path $FilePath) {
        $timeoutMinutes = 15
        $timeout = $timeoutMinutes * 60

        Write-ToLog -Warning 1 -LogText "Starting file $($InstallMode): $FilePath with arguments '$ArgumentList'. Timeout: $timeoutMinutes minutes."
        try {
            if (-not ([String]::IsNullOrEmpty($ArgumentList))) {
                $proc = Start-Process -filePath $FilePath -ArgumentList $ArgumentList -PassThru -WindowStyle hidden
            }
            else {
                $proc = Start-Process -filePath $FilePath -PassThru -WindowStyle hidden
            }
        }
        Catch {
            Write-ToLog -Warning 3 -LogText "Error $_ while executing $FilePath with ArgumentList $ArgumentList"
            return "unknown"
        }
        # wait up to $timeout seconds for normal termination
        $proc | Wait-Process -Timeout $timeout -ErrorAction SilentlyContinue -ErrorVariable timeouted
        $ExitCode = $proc.ExitCode

        if ($timeouted) {
            # terminate the process
            if (-not ([String]::IsNullOrEmpty($proc))) {
                $proc | Stop-Process
            }
            # Set ExitCode to TimeOut
            Write-ToLog -Warning 3 -LogText "$InstallMode went into timeout - Return Code $ExitCode of $FilePath"
            return "timeout"
        }
        elseif ($ExitCode -in @(0, 3, 129, 130, 144, 145, 146, 3010, 1641, 1707)) {
            Write-ToLog -Warning 1 -LogText "$InstallMode successful - Return Code $ExitCode of $FilePath"
            return $ExitCode
        }
        elseif ($ExitCode -eq 1618) {
            CheckRunningInstaller #-Kill
            Start-Process-Function -FilePath $FilePath -ArgumentList $ArgumentList
        }
        else {
            Write-ToLog -Warning 3 -LogText "$InstallMode failed - Return Code $ExitCode of $FilePath"
            return $ExitCode
        }
    }
    else {
        Write-ToLog -Warning 3 -LogText "$FilePath does not exist. Can not install then."
        return "unavailable"
    }
}

Function CheckRunningInstaller {
    param(
        [switch]$Kill
    )

    Write-ToLog -Warning 1 -LogText "This package installer has been blocked by another installer. Searching for active MSI installations..."

    # Get all running msiexec processes
    $msiProcs = Get-CimInstance Win32_Process -Filter "Name='msiexec.exe'" | Sort-Object CreationDate

    if (-not $msiProcs) {
        Write-ToLog -Warning 1 -LogText "No active msiexec process found."
        return
    }

    foreach ($p in $msiProcs) {
        Write-ToLog -Warning 1 -LogText "PID $($p.ProcessId) - $($p.CommandLine)"

        # Try to find a related MSI installer event in the Application log
        $evt = Get-WinEvent -LogName "Application" -MaxEvents 50 |
        Where-Object { $_.ProviderName -eq "MsiInstaller" -and $_.TimeCreated -gt $p.CreationDate } |
        Select-Object -First 1

        if ($evt) {
            Write-ToLog -Warning 1 -LogText "Possible installation in progress: $($evt.Message)"
        }
        else {
            Write-ToLog -Warning 1 -LogText "(No related event found - process might be service or helper instance)"
        }

        # If -Kill switch is specified, try to terminate the process
        if ($Kill) {
            try {
                Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
                Write-ToLog -Warning 1 -LogText "Process $($p.ProcessId) has been terminated."
            }
            catch {
                Write-ToLog -Warning 3 -LogText "Failed to terminate process $($p.ProcessId): $_"
            }
        }
        else {
            Write-ToLog -Warning 1 -LogText "Waiting 30 seconds for other installer to finish."
            Start-Sleep -Seconds 30
        }
    }
}

# Function to Check for RegKey Values (f.e. to compare Software Versions)
Function Get-RegistryContent ($RegKey, $RegKeyName) {
    $CheckRegKey = Get-ItemProperty -Path $RegKey -Name $RegKeyName -ErrorAction Ignore
    if ($CheckRegKey -and $CheckRegKey.$RegKeyName) {
        Write-ToLog -Warning 1 -LogText "Read from Registry $RegKey $RegKeyName : $($CheckRegKey.$RegKeyName)"
        return $CheckRegKey.$RegKeyName
    }
}

# Function to Set RegKey Values
Function Set-RegistryContent ($RegKey, $RegKeyName, $RegKeyValue, $RegKeyType) {
    $CheckRegKeyPath = Get-ItemProperty -Path $RegKey -ErrorAction Ignore
    if ([String]::IsNullOrEmpty($CheckRegKeyPath)) {
        try {
            New-Item -Path $RegKey -Force -ErrorAction Stop
        }
        Catch {
            Write-ToLog -Warning 3 -LogText "Error $_ while creating RegKey Path $RegKey"
        }
    }
    $CheckRegKey = Get-ItemProperty -Path $RegKey -Name $RegKeyName -ErrorAction Ignore
    if ([String]::IsNullOrEmpty($CheckRegKey)) {
        Write-ToLog -Warning 1 -LogText "Writing to Registry $RegKey $RegKeyName Key: $RegKeyValue with type $RegKeyType"
        try {
            New-ItemProperty -Path $RegKey -Name $RegKeyName -Value $RegKeyValue -PropertyType $RegKeyType -Force -ErrorAction Stop
        }
        Catch {
            Write-ToLog -Warning 3 -LogText "Error $_ while creating RegKey property $RegKey"
        }
    }
    else {
        Write-ToLog -Warning 1 -LogText "RegKey for $RegKey $RegKeyName already existed. Overwriting the old RegKey: $($CheckRegKey.$RegKeyName)"
        try {
            Set-ItemProperty -Path $RegKey -Name $RegKeyName -Value $RegKeyValue -Type $RegKeyType -Force
        }
        Catch {
            Write-ToLog -Warning 3 -LogText "Error $_ while setting RegKey $RegKey"
        }
        Write-ToLog -Warning 1 -LogText "Writing to Registry $RegKey $RegKeyName Key: $RegKeyValue with type $RegKeyType"
    }
}

# Function to Set RegKey Values for all Users in HKEY_USERS Hive
function Set-RegistryForAllUsers {
    param (
        [string]$RelativePath,
        [string]$RegKeyName,
        [string]$RegKeyValue,
        [string]$RegKeyType
    )

    $allUserSids = Get-ChildItem -Path "Registry::HKEY_USERS" | Where-Object { $_.Name -match 'S-\d-\d+-(\d+-){1,14}\d+$' }
    foreach ($user in $allUserSids) {
        $userRegPath = "Registry::HKEY_USERS\$($user.PSChildName)\$RelativePath"
        Set-RegistryContent -RegKey $userRegPath -RegKeyName $RegKeyName -RegKeyValue $RegKeyValue -RegKeyType $RegKeyType
    }
}

# Function to Delete RegKey or RegValue
Function Remove-RegistryContent {
    param(
        [Parameter(Mandatory = $True)] [String] $RegKey,
        [Parameter(Mandatory = $False)] [String] $RegKeyName
    )

    try {
        # Prüfen, ob der Schlüssel existiert
        if (Test-Path $RegKey) {
            if ($RegKeyName) {
                # Wenn ein spezifischer Wert angegeben ist, prüfen, ob er existiert
                $CheckRegValue = Get-ItemProperty -Path $RegKey -Name $RegKeyName -ErrorAction SilentlyContinue
                if ($null -ne $CheckRegValue) {
                    Write-ToLog -Warning 1 -LogText "RegValue '$RegKeyName' in Key '$RegKey' will now be removed"
                    try {
                        Remove-ItemProperty -Path $RegKey -Name $RegKeyName -Force -ErrorAction Stop
                    }
                    catch {
                        Write-ToLog -Warning 3 -LogText "Error $_ while removing RegValue '$RegKeyName' from '$RegKey'"
                    }
                }
                else {
                    Write-ToLog -Warning 1 -LogText "RegValue '$RegKeyName' does not exist in Key '$RegKey'. Nothing removed"
                }
            }
            else {
                # Wenn kein spezifischer Wert angegeben ist, den gesamten Schlüssel löschen
                Write-ToLog -Warning 1 -LogText "RegKey '$RegKey' will now be removed"
                try {
                    Remove-Item -Path $RegKey -Recurse -Force -ErrorAction Stop
                }
                catch {
                    Write-ToLog -Warning 3 -LogText "Error $_ while removing RegKey '$RegKey'"
                }
            }
        }
        else {
            Write-ToLog -Warning 1 -LogText "RegKey '$RegKey' does not exist. Nothing removed"
        }
    }
    catch {
        Write-ToLog -Warning 3 -LogText "Unexpected error $_ while processing RegKey '$RegKey'"
    }
}

Function Uninstall-SoftwareByFilter {
    param(
        [Parameter(Mandatory = $true)]
        [string] $NameFilter,

        [Parameter(Mandatory = $false)]
        [string] $Publisher,

        [Parameter(Mandatory = $false)]
        [switch] $RemoveOrphanedEntries # Optional parameter to remove registry entries in the end - only needed for faulty software
    )

    $UninstallPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    )

    $FoundSomething = $false

    foreach ($Path in $UninstallPaths) {
        $SubKeys = Get-ChildItem -Path $Path -ErrorAction SilentlyContinue

        foreach ($SubKey in $SubKeys) {
            $App = Get-ItemProperty -Path $SubKey.PSPath -ErrorAction SilentlyContinue

            if ($App.DisplayName -like "*$NameFilter*" -and (-not $Publisher -or $App.Publisher -eq $Publisher)) {
                $FoundSomething = $true
                $DisplayName = $App.DisplayName
                $UninstallString = $App.UninstallString
                $ProductCode = $null

                if ($UninstallString -match "msiexec\.exe.*?(/x|/I)\s*({.*?})") {
                    $ProductCode = $matches[2]
                }

                if ($ProductCode) {
                    $LogFileNameWithFolder = Join-Path -Path $LogPathFolder -ChildPath "$($DisplayName)_uninstall_$($ProductCode).log"
                    Write-ToLog -Warning 1 -LogText "Uninstalling $DisplayName with ProductCode: $ProductCode"
                    $Script:ExitCode = Start-Process-Function -FilePath "C:\Windows\System32\msiexec.exe" -ArgumentList "/x $ProductCode /log `"$LogFileNameWithFolder`""
                }
                elseif ($UninstallString) {
                    Write-ToLog -Warning 1 -LogText "Uninstalling $DisplayName using raw UninstallString (non-MSI): $UninstallString"

                    # Split the UninstallString into the executable file and the arguments
                    $executable = $UninstallString
                    $arguments = ""

                    # Check if the string starts with a quote to properly extract the executable path
                    if ($UninstallString.StartsWith('"')) {
                        $endQuoteIndex = $UninstallString.IndexOf('"', 1)
                        if ($endQuoteIndex -ne -1) {
                            $executable = $UninstallString.Substring(1, $endQuoteIndex - 1)
                            $arguments = $UninstallString.Substring($endQuoteIndex + 1).Trim()
                        }
                    }
                    else {
                        # Simple split at the first space if no quotes are present
                        $parts = $UninstallString.Split(' ', 2)
                        $executable = $parts[0]
                        if ($parts.Length -gt 1) {
                            $arguments = $parts[1]
                        }
                    }

                    # Resolve the full path of the executable if it's not a direct path
                    $resolvedExecutable = $executable
                    try {
                        $commandInfo = Get-Command $executable -ErrorAction Stop
                        if ($commandInfo) {
                            $resolvedExecutable = $commandInfo.Source
                            Write-ToLog -Warning 1 -LogText "Resolved executable '$executable' to full path: '$resolvedExecutable'"
                        }
                    }
                    catch {
                        Write-ToLog -Warning 2 -LogText "Could not resolve full path for '$executable'. Will proceed with the original value. This may fail if it's not a full path."
                    }

                    Write-ToLog -Warning 1 -LogText "Executing parsed command -> Executable: '$resolvedExecutable', Arguments: '$arguments'"
                    $Script:ExitCode = Start-Process-Function -FilePath $resolvedExecutable -ArgumentList $arguments
                }
                else {
                    Write-ToLog -Warning 2 -LogText "No uninstall method found for $DisplayName. Skipping."
                }
                if ($RemoveOrphanedEntries) {
                    Write-ToLog -Warning 1 -LogText "Removing orphaned registry entry for $DisplayName from $($SubKey.PSPath)"
                    try {
                        Remove-Item -Path $SubKey.PSPath -Recurse -Force
                        Write-ToLog -Info "Removed orphaned registry entry: $DisplayName"
                    }
                    catch {
                        Write-ToLog -Warning 2 -LogText "Failed to remove orphaned registry entry for $($DisplayName): $_"
                    }
                }
            }
        }
    }

    if (-not $FoundSomething) {
        $pubText = if ($Publisher) { " and Publisher '$Publisher'" } else { "" }
        Write-ToLog -Warning 1 -LogText "No installation found for filter '$NameFilter'$pubText. Skipping uninstallation."
    }
}

Write-ToLog -Warning 9 -LogText "Starting $InstallMode"


# ## PRE-INSTALLATION / CONFIGURATION
# Check for custom template and set registry default if not already set
$TemplatePath = "$env:USERPROFILE\GitHub\Intune-packaging\Apps\_Intune_App_Installer_Template.ps1"
if (Test-Path $TemplatePath) {
    Write-ToLog -Warning 1 -LogText "Found custom template at $TemplatePath. Setting as default."
    # The app uses HKCU\Software\FaserF\SwitchCraft -> "custom_template_path"
    $RegKey = "HKCU:\Software\FaserF\SwitchCraft"
    if (!(Test-Path $RegKey)) {
        New-Item -Path $RegKey -Force -ErrorAction SilentlyContinue | Out-Null
    }
    # Only set if not already set (preserve user choice) or force it?
    # User said: "Registry Einstellungen die gleich vorab gesetzt werden (Standard Template...)"
    # Implies setting it initially.
    $CurrentVal = Get-ItemProperty -Path $RegKey -Name "custom_template_path" -ErrorAction SilentlyContinue
    if (-not $CurrentVal) {
        Set-ItemProperty -Path $RegKey -Name "custom_template_path" -Value $TemplatePath -Type String -Force
        Write-ToLog -Warning 1 -LogText "Set Registry 'custom_template_path' to '$TemplatePath'"
    } else {
        Write-ToLog -Warning 1 -LogText "Registry 'custom_template_path' already set. Skipping."
    }
}

# Set Release Type to Beta (User Request)
$RegKey = "HKCU:\Software\FaserF\SwitchCraft"
if (!(Test-Path $RegKey)) { New-Item -Path $RegKey -Force -ErrorAction SilentlyContinue | Out-Null }
$ChannelVal = Get-ItemProperty -Path $RegKey -Name "UpdateChannel" -ErrorAction SilentlyContinue
if (-not $ChannelVal) {
    Set-ItemProperty -Path $RegKey -Name "UpdateChannel" -Value "beta" -Type String -Force
    Write-ToLog -Warning 1 -LogText "Set Registry 'UpdateChannel' to 'beta'"
}

# ## INSTALLATION
if (($InstallMode -eq "Install") -or ($InstallMode -eq "i")) {
    $Installer = Join-Path -Path $PSScriptRoot -ChildPath "SwitchCraft-Setup.exe"
    $ExitCode = Start-Process-Function -FilePath $Installer -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
}

# ## UNINSTALLATION
if (($InstallMode -eq "Uninstall") -or ($InstallMode -eq "u")) {
    # SwitchCraft uses Inno Setup. UninstallString is usually consistent.
    # Name: "SwitchCraft" Pub: "FaserF"
    Uninstall-SoftwareByFilter -NameFilter "SwitchCraft" -Publisher "FaserF"
}

Write-ToLog -Warning 1 -LogText "Script finished with Exitcode $ExitCode"
Write-Host "Script finished with Exitcode $ExitCode"
Exit $ExitCode
