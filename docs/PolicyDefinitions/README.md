# SwitchCraft ADMX Policy Template

Administrative templates for managing SwitchCraft settings via Group Policy (GPO) or Microsoft Intune.

## Available Policies

| Policy | Category | Description |
|--------|----------|-------------|
| **Enable Debug Logging** | SwitchCraft | Enable/disable verbose debug logging |
| **Update Channel** | Updates | Configure update channel (Stable/Beta/Dev) |

## Installation

### Local Group Policy

1. Copy `SwitchCraft.admx` to `C:\Windows\PolicyDefinitions\`
2. Copy `en-US\SwitchCraft.adml` to `C:\Windows\PolicyDefinitions\en-US\`
3. Copy `de-DE\SwitchCraft.adml` to `C:\Windows\PolicyDefinitions\de-DE\`
4. Open `gpedit.msc` → User Configuration → Administrative Templates → SwitchCraft

### Active Directory (Domain GPO)

1. Copy `SwitchCraft.admx` to `\\domain.local\SYSVOL\domain.local\Policies\PolicyDefinitions\`
2. Copy language folders (`en-US`, `de-DE`) with `.adml` files to the same location
3. Create/edit a GPO and configure under **User Configuration → Administrative Templates → SwitchCraft**

### Microsoft Intune

Method 1: **Settings Catalog** (Recommended for new policies)
1. Create a new Configuration Profile → Settings Catalog
2. Search for the registry path: `HKCU\Software\FaserF\SwitchCraft`
3. Add values manually:
   - `DebugMode` (Integer): `1` = enabled, `0` = disabled
   - `UpdateChannel` (String): `stable`, `beta`, or `dev`

Method 2: **Custom OMA-URI** (Preferred for Intune)

SwitchCraft fully supports Intune's custom OMA-URI policies that target the `Software\Policies` keys.

**Debug Mode Example:**
```
OMA-URI: ./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/DebugMode
Data type: Integer
Value: 1
```

**Update Channel Example:**
```
OMA-URI: ./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/UpdateChannel
Data type: String
Value: stable
```

Method 3: **ADMX Ingestion**
1. Create a new Device Configuration Profile
2. Select "Templates" → "Custom"
3. Upload the ADMX/ADML files using OMA-URI:
   - `./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/SwitchCraft/Policy/SwitchCraftPolicy`
   - Data type: String
   - Value: Contents of `SwitchCraft.admx`

## Registry Reference & Precedence

SwitchCraft reads configuration with the following precedence order:

1. **Machine Policy** (`HKLM\Software\Policies\FaserF\SwitchCraft`) - *Highest Priority (Intune/GPO)*
2. **User Policy** (`HKCU\Software\Policies\FaserF\SwitchCraft`) - *High Priority (Intune/GPO)*
3. **Machine Preference** (`HKLM\Software\FaserF\SwitchCraft`)
4. **User Preference** (`HKCU\Software\FaserF\SwitchCraft`) - *Default User Settings*

This ensures that Policies managed by your organization (via Intune/GPO) always override local user settings.

| Policy | Value Name | Type | Values |
|--------|---------------|------|--------|
| Debug Logging | `DebugMode` | REG_DWORD | `0` = Off, `1` = On |
| Update Channel | `UpdateChannel` | REG_SZ | `stable`, `beta`, `dev` |

## PowerShell Deployment

```powershell
# Enable Debug Mode for all users (requires admin)
$users = Get-ChildItem "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList" |
         ForEach-Object { $_.GetValue("ProfileImagePath") }

foreach ($user in $users) {
    $sid = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\*" |
            Where-Object { $_.ProfileImagePath -eq $user }).PSChildName

    reg load "HKU\$sid" "$user\NTUSER.DAT" 2>$null
    reg add "HKU\$sid\Software\FaserF\SwitchCraft" /v DebugMode /t REG_DWORD /d 1 /f
    reg unload "HKU\$sid" 2>$null
}
```

## File Structure

```
PolicyDefinitions/
├── SwitchCraft.admx      # Policy definitions
├── en-US/
│   └── SwitchCraft.adml  # English strings
├── de-DE/
│   └── SwitchCraft.adml  # German strings
└── README.md             # This file
```
