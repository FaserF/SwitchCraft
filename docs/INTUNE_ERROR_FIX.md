# Intune Policy Error -2016281112: Detailed Troubleshooting

## Problem

All SwitchCraft policies show error code **-2016281112** (Remediation Failed), while the ADMX installation is successful.

## Quick Diagnosis

If you see this error list:
```
SignScripts_Enf          → Error -2016281112
UpdateChannel_Enf        → Error -2016281112
EnableWinget_Enf         → Error -2016281112
AIProvider_Enf           → Error -2016281112
GraphTenantId_Enf        → Error -2016281112
CompanyName_Enf          → Error -2016281112
GraphClientId_Enf        → Error -2016281112
IntuneTestGroups_Enf     → Error -2016281112
GraphClientSecret_Enf    → Error -2016281112
```

But:
```
SwitchCraftPolicy (ADMX Install) → Succeeded ✅
```

Then the problem is **NOT** the ADMX installation, but the **individual policy configurations**.

## Most Common Causes (in order of probability)

### 1. ❌ Incorrect Data Type (90% of cases)

**Problem**: In Intune, the Data Type was set to "Integer", "Boolean", or "String (Integer)" instead of "String".

**Solution**:
1. Open each failed policy in Intune
2. Check the **Data Type** - it MUST be **"String"** (sometimes also labeled "String (XML)")
3. If incorrect: **Delete the policy completely** and recreate it with Data Type **"String"**

**IMPORTANT**: Even if a policy is logically a Boolean or Integer (e.g., `SignScripts_Enf` = Enable/Disable), the Data Type must still be **"String"** because the value is an XML snippet!

### 2. ❌ Incorrect XML Format

**Problem**: The XML in the Value field is incorrectly formatted or uses wrong element IDs.

**Correct XML Formats**:

#### For Boolean Policies (Enable/Disable):
```xml
<enabled/>
```
or
```xml
<disabled/>
```

**Examples**:
- `SignScripts_Enf` → `<enabled/>`
- `EnableWinget_Enf` → `<enabled/>`

#### For Policies with Values:
```xml
<enabled/>
<data id="[ELEMENT_ID]" value="[VALUE]"/>
```

**IMPORTANT**: The `id` must **exactly** match the ADMX file!

**Correct Element IDs** (from SwitchCraft.admx):

| Policy | Element ID (MUST be exactly this!) |
|--------|-----------------------------------|
| `UpdateChannel_Enf` | `UpdateChannelDropdown` |
| `CompanyName_Enf` | `CompanyNameBox` |
| `GraphTenantId_Enf` | `GraphTenantIdBox` |
| `GraphClientId_Enf` | `GraphClientIdBox` |
| `GraphClientSecret_Enf` | `GraphClientSecretBox` |
| `IntuneTestGroups_Enf` | `IntuneTestGroupsBox` |
| `AIProvider_Enf` | `AIProviderDropdown` |

**Incorrect Examples** (will NOT work):
- ❌ `<data id="UpdateChannel" value="stable"/>` → Wrong! Must be `UpdateChannelDropdown`
- ❌ `<data id="CompanyName" value="Acme"/>` → Wrong! Must be `CompanyNameBox`
- ❌ `<data id="GraphTenantId" value="..."/>` → Wrong! Must be `GraphTenantIdBox`

**Correct Examples**:

```xml
<!-- UpdateChannel_Enf -->
<enabled/>
<data id="UpdateChannelDropdown" value="stable"/>
```

```xml
<!-- CompanyName_Enf -->
<enabled/>
<data id="CompanyNameBox" value="Acme Corp"/>
```

```xml
<!-- GraphTenantId_Enf -->
<enabled/>
<data id="GraphTenantIdBox" value="00000000-0000-0000-0000-000000000000"/>
```

```xml
<!-- GraphClientId_Enf -->
<enabled/>
<data id="GraphClientIdBox" value="00000000-0000-0000-0000-000000000000"/>
```

```xml
<!-- GraphClientSecret_Enf -->
<enabled/>
<data id="GraphClientSecretBox" value="your-secret-here"/>
```

```xml
<!-- IntuneTestGroups_Enf -->
<enabled/>
<data id="IntuneTestGroupsBox" value="GroupID1,GroupID2"/>
```

```xml
<!-- AIProvider_Enf -->
<enabled/>
<data id="AIProviderDropdown" value="openai"/>
```

### 3. ❌ Incorrect OMA-URI Path

**Problem**: The OMA-URI path contains typos or uses incorrect separators.

**Correct OMA-URI Paths** (complete):

| Policy | Complete OMA-URI |
|--------|----------------------|
| `SignScripts_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Security_Enf/SignScripts_Enf` |
| `UpdateChannel_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Updates_Enf/UpdateChannel_Enf` |
| `EnableWinget_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/EnableWinget_Enf` |
| `AIProvider_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~AI_Enf/AIProvider_Enf` |
| `GraphTenantId_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphTenantId_Enf` |
| `CompanyName_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/CompanyName_Enf` |
| `GraphClientId_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientId_Enf` |
| `IntuneTestGroups_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/IntuneTestGroups_Enf` |
| `GraphClientSecret_Enf` | `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientSecret_Enf` |

**IMPORTANT Rules**:
- Use `~` (tilde) to separate namespace parts, NOT `/` (slash)
- Category names end with `_Enf` (e.g., `General_Enf`, `Intune_Enf`, `Security_Enf`)
- Policy names end with `_Enf` (e.g., `SignScripts_Enf`, `CompanyName_Enf`)

### 4. ❌ Registry Path Does Not Exist

**Problem**: The registry path `HKCU\Software\Policies\FaserF\SwitchCraft` does not exist on the device.

**Solution**: Create the registry path manually or via script:

```powershell
# Create registry path
New-Item -Path "HKCU:\Software\Policies\FaserF\SwitchCraft" -Force | Out-Null

# Check if it exists
Get-ItemProperty -Path "HKCU:\Software\Policies\FaserF\SwitchCraft" -ErrorAction SilentlyContinue
```

**Note**: Normally, this path should be created automatically when the ADMX installation was successful. If not, it may be a permissions issue.

## Step-by-Step Repair

### Step 1: Check the Data Type

For **each** failed policy:

1. Open the policy in Intune Portal
2. Check the **Data Type**
3. If it is **NOT** "String":
   - **Delete the policy completely**
   - Recreate it with Data Type **"String"**

### Step 2: Check the XML Format

For each policy with a value (not just Enable/Disable):

1. Open the policy
2. Check the **Value** field
3. Ensure that:
   - The XML is correctly formatted
   - The `id` exactly matches the table above
   - There are no typos

**Example for `GraphTenantId_Enf`**:
```xml
<enabled/>
<data id="GraphTenantIdBox" value="00000000-0000-0000-0000-000000000000"/>
```

**NOT**:
```xml
<enabled/>
<data id="GraphTenantId" value="00000000-0000-0000-0000-000000000000"/>
```
(Missing `Box` at the end!)

### Step 3: Check the OMA-URI Path

Compare each OMA-URI path character by character with the table above.

**Common Errors**:
- ❌ Using `/` instead of `~`
- ❌ Forgetting `_Enf` at the end
- ❌ Wrong category name (e.g., `General` instead of `General_Enf`)

### Step 4: Test on a Device

1. **Trigger Sync**: On the test device:
   ```powershell
   gpupdate /force
   ```
   Or: Intune Portal → Devices → [Device] → Sync

2. **Check Registry**:
   ```powershell
   Get-ItemProperty -Path "HKCU:\Software\Policies\FaserF\SwitchCraft" -ErrorAction SilentlyContinue
   ```

3. **Check Event Logs**:
   ```powershell
   Get-WinEvent -LogName "Microsoft-Windows-User Device Registration/Admin" -MaxEvents 50 |
       Where-Object {$_.LevelDisplayName -eq "Error"} |
       Format-List TimeCreated, Message
   ```

## Complete Example Configuration

Here is a complete, correct configuration for all failed policies:

### 1. SignScripts_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Security_Enf/SignScripts_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/>`

### 2. UpdateChannel_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Updates_Enf/UpdateChannel_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/><data id="UpdateChannelDropdown" value="stable"/>`

### 3. EnableWinget_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/EnableWinget_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/>`

### 4. AIProvider_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~AI_Enf/AIProvider_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/><data id="AIProviderDropdown" value="local"/>`

### 5. GraphTenantId_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphTenantId_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/><data id="GraphTenantIdBox" value="YOUR-TENANT-ID"/>`

### 6. CompanyName_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/CompanyName_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/><data id="CompanyNameBox" value="Your Company Name"/>`

### 7. GraphClientId_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientId_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/><data id="GraphClientIdBox" value="YOUR-CLIENT-ID"/>`

### 8. IntuneTestGroups_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/IntuneTestGroups_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/><data id="IntuneTestGroupsBox" value="GroupID1,GroupID2"/>`

### 9. GraphClientSecret_Enf
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientSecret_Enf`
- **Data Type**: `String`
- **Value**: `<enabled/><data id="GraphClientSecretBox" value="YOUR-CLIENT-SECRET"/>`

## Checklist Before Recreating

Before recreating a policy, check:

- [ ] ADMX installation shows "Succeeded" ✅
- [ ] Data Type is **"String"** (not "Integer" or "Boolean")
- [ ] OMA-URI path matches documentation **exactly** (including tildes)
- [ ] XML format is correct (`<enabled/>` or `<enabled/><data id="..." value="..."/>`)
- [ ] Element ID matches ADMX file exactly (e.g., `GraphTenantIdBox`, not `GraphTenantId`)
- [ ] No typos in Value (e.g., in UUIDs or secrets)

## If Nothing Helps

1. **Delete ALL failed policies** completely
2. **Wait 5-10 minutes** (Intune needs time to synchronize)
3. **Recreate the policies** - one by one, starting with a simple one (e.g., `EnableWinget_Enf`)
4. **Test each policy individually** before creating the next one
5. If errors persist: **Delete and recreate the ADMX installation**

## Additional Resources

- [GPO Troubleshooting Guide](./GPO_TROUBLESHOOTING.md)
- [Intune Configuration Guide](./Intune_Configuration_Guide.md)
- [Policy Definitions README](./PolicyDefinitions/README.md)
