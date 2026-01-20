# GPO/Intune Troubleshooting Guide

> [!TIP]
> **Quick Help**: If you see a list of failed policies (like `SignScripts_Enf`, `UpdateChannel_Enf`, etc. all with error -2016281112), read the [detailed troubleshooting guide](./INTUNE_ERROR_FIX.md) first.

## Error Code -2016281112 (Remediation Failed)

If you see error code **-2016281112** for your SwitchCraft policies in Intune, this means "Remediation failed" - the policy could not be applied to the device.

### Common Causes

1. **Incorrect Data Type**
   - **Problem**: Using "Integer" or "Boolean" instead of "String"
   - **Solution**: All ADMX-backed policies MUST use **String** (or "String (XML)") as the Data Type
   - **Example Error**: `DebugMode_Enf Integer` - The "Integer" suffix indicates wrong data type

2. **ADMX Not Installed**
   - **Problem**: The ADMX file was not ingested before configuring policies
   - **Solution**: Ensure the ADMX ingestion policy shows "Succeeded" status:
     - OMA-URI: `./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/switchcraft/Policy/SwitchCraftPolicy`
     - Data Type: **String**
     - Value: Full content of `SwitchCraft.admx` file

3. **Incorrect OMA-URI Path**
   - **Problem**: Wrong path structure or typos in the OMA-URI
   - **Solution**: Verify the exact path matches the documentation:
   - Base: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced`
   - Category suffix: `~[Category]_Enf/[PolicyName]_Enf`
   - Example: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/CompanyName_Enf`

4. **Malformed XML Value**
   - **Problem**: Invalid XML structure in the Value field
   - **Solution**: Ensure the XML follows the correct format:
     - For enabled/disabled policies: `<enabled/>` or `<disabled/>`
     - For policies with data: `<enabled/><data id="[ElementId]" value="[Value]"/>`
   - **Common Mistakes**:
     - Missing closing tags
     - Wrong element IDs (must match ADMX file)
     - Special characters not properly escaped

5. **Windows Version Compatibility**
   - **Problem**: Policy not supported on the target Windows version
   - **Solution**: Ensure devices are running Windows 10/11 (policies require Windows 10+)

6. **Registry Permissions**
   - **Problem**: Insufficient permissions to write to `HKCU\Software\Policies\FaserF\SwitchCraft`
   - **Solution**: Verify the user has write access to their own HKCU registry hive

### Step-by-Step Troubleshooting

#### Step 1: Verify ADMX Installation

Check if the ADMX ingestion policy is successful:
- Go to Intune Portal → Devices → Configuration Profiles
- Find the profile containing the ADMX ingestion policy
- Verify status is "Succeeded" (not "Error")

If it shows "Error":
1. Re-upload the ADMX file content
2. Ensure the entire file is copied (including XML header)
3. Verify no special characters were corrupted during copy-paste

#### Step 2: Check Data Types

For each policy showing error -2016281112:
1. Open the policy configuration in Intune
2. Verify **Data Type** is set to **"String"** (NOT "Integer" or "Boolean")
3. If wrong, delete and recreate the policy with correct Data Type

#### Step 3: Validate OMA-URI Paths

Compare your OMA-URI paths with the reference table:

| Policy | Correct OMA-URI |
|--------|----------------|
| Debug Mode | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced/DebugMode_Enf` |
| Update Channel | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Updates_Enf/UpdateChannel_Enf` |
| Company Name | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/CompanyName_Enf` |
| Enable Winget | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/EnableWinget_Enf` |
| Graph Tenant ID | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphTenantId_Enf` |
| Graph Client ID | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientId_Enf` |
| Graph Client Secret | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientSecret_Enf` |
| Intune Test Groups | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/IntuneTestGroups_Enf` |
| Sign Scripts | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Security_Enf/SignScripts_Enf` |
| AI Provider | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~AI_Enf/AIProvider_Enf` |

**Important Notes:**
- Use `~` (tilde) to separate namespace parts, NOT `/` (slash)
- Category names end with `_Enf` (e.g., `General_Enf`, `Intune_Enf`)
- Policy names end with `_Enf` (e.g., `DebugMode_Enf`, `CompanyName_Enf`)

#### Step 4: Validate XML Values

Verify the XML structure matches the expected format:

**For Boolean Policies (Enable/Disable):**
```xml
<enabled/>
```
or
```xml
<disabled/>
```

**For Policies with Data:**
```xml
<enabled/>
<data id="CompanyNameBox" value="Your Company Name"/>
```

**Element IDs must match the ADMX file:**
- `CompanyNameBox` (not `CompanyName` or `CompanyName_Enf`)
- `GraphTenantIdBox` (not `GraphTenantId` or `TenantId`)
- `UpdateChannelDropdown` (not `UpdateChannel` or `Channel`)
- `LanguageDropdown` (not `Language` or `Lang`)

#### Step 5: Test on Device

1. **Sync Policy**: On the target device, run:
   ```powershell
   gpupdate /force
   ```
   Or trigger a sync from Intune Portal → Devices → [Device] → Sync

2. **Check Registry**: Verify the policy was applied:
   ```powershell
   Get-ItemProperty -Path "HKCU:\Software\Policies\FaserF\SwitchCraft" -ErrorAction SilentlyContinue
   ```

3. **Check Event Logs**: Look for Group Policy errors:
   ```powershell
   Get-WinEvent -LogName "Microsoft-Windows-User Device Registration/Admin" | Where-Object {$_.LevelDisplayName -eq "Error"}
   ```

### Quick Fix Checklist

- [ ] ADMX ingestion policy shows "Succeeded"
- [ ] All policy Data Types are set to "String"
- [ ] OMA-URI paths match documentation exactly (including tildes)
- [ ] XML values use correct format (`<enabled/>` or `<enabled/><data id="..." value="..."/>`)
- [ ] Element IDs match ADMX file (e.g., `CompanyNameBox`, not `CompanyName`)
- [ ] Device has synced policies (`gpupdate /force`)
- [ ] Registry key exists: `HKCU\Software\Policies\FaserF\SwitchCraft`

### Still Not Working?

If policies still fail after following all steps:

1. **Delete and Recreate**: Remove all failing policies and recreate them from scratch
2. **Re-upload ADMX**: Delete and recreate the ADMX ingestion policy
3. **Check Intune Logs**: Review device compliance logs in Intune Portal
4. **Test with Single Policy**: Create a test profile with only one policy to isolate the issue
5. **Verify Windows Version**: Ensure target devices are Windows 10 1809+ or Windows 11

### Additional Resources

- [Intune Configuration Guide](./Intune_Configuration_Guide.md)
- [Policy Definitions README](./PolicyDefinitions/README.md)
- [Microsoft Docs: ADMX Ingestion](https://learn.microsoft.com/en-us/mem/intune/configuration/administrative-templates-windows)
