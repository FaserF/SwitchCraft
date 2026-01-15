# ✨ Features

- **🔎 Universal Analysis**:
  - **MSI**: Extracts `ProductCode`, `UpgradeCode`, manufacturer, version, and standard `/qn` switches
  - **EXE**: Auto-detects 20+ installer frameworks and suggests appropriate silent switches
  - **Metadata**: Parses PE version info for product name, version, and company
- **📦 Winget Integration**: Automatically checks if the package exists in the **Windows Package Manager** (winget) repository
- **🛒 Intune Store Browser**: Browse your Intune applications with logo display, metadata, and assignment management
- **📝 WingetCreate Manager**: Create and manage Winget manifests for publishing packages to Microsoft's repository
- **👥 Group Manager**: Manage Intune groups and assignments directly from SwitchCraft
- **🔔 Notification System**: Desktop notifications and in-app notification center with read/unread status
- **✍️ Script Signing**: Automatically sign generated PowerShell scripts with your code-signing certificate (auto-detected or PFX)
- **⚔️ Automatic Brute Force**: Runs 15+ help argument variations to discover switches
- **🧩 Project Stacks**: Group applications into named stacks for one-click batch deployment via Stack Manager
- **📊 Interactive Dashboard**: Visual overview of your packaging activity, statistics, charts, and recent actions
- **📚 My Library**: Personal collection of analyzed and packaged applications with search, filter, and folder management
- **🧪 Detection Tester**: Test Registry, File, or MSI detection rules locally before uploading to Intune
- **📤 Script Upload**: Upload and manage PowerShell scripts for Intune deployment
- **🍎 macOS Wizard**: Create install.sh scripts and DMG/PKG packages for macOS deployment
- **👥 Community Database**: Crowdsourced database of silent switches with automated IssueOps contributions
- **🌐 Multi-Language**: Full English and German (Du-Form) interface with immediate language switching
- **🤖 AI Helper**: Context-aware AI assistant supporting Local AI, OpenAI, and Google Gemini with copy-to-clipboard

## 🎯 Supported Installer Types

### Standard Installers

| Installer Type | Detection Confidence | Silent Install Switch |
|---------------|---------------------|----------------------|
| **MSI Database** | 100% | `/qn /norestart` |
| **NSIS** | 90% | `/S` |
| **Inno Setup** | 90% | `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` |
| **InstallShield** | 80% | `/s /v"/qn"` |
| **7-Zip SFX** | 90% | `/S` |
| **WiX Burn Bundle** | 85% | `/quiet /norestart` |
| **Advanced Installer** | 80% | `/exenoui /qn` |
| **Wise Installer** | 80% | `/S` |
| **Setup Factory** | 75% | `/S` |
| **Squirrel (Electron)** | 80% | `--silent` |

### Vendor-Specific Installers

| Vendor | Detection Confidence | Silent Install Switch |
|--------|---------------------|----------------------|
| **HP SoftPaq** | 85% | `-s -e <extract_path>` |
| **Dell Update Package** | 85% | `/s /l=<logfile>` |
| **SAP** | 80% | `/Silent` |
| **Lenovo** | 80% | `/SILENT /VERYSILENT /NOREBOOT` |
| **Intel** | 80% | `-s -a -s2 -norestart` |
| **NVIDIA** | 80% | `-s -noreboot -clean` |
| **AMD/ATI** | 75% | `/S` |
| **Visual C++ Redist** | 90% | `/quiet /norestart` |
| **Java/Oracle** | 80% | `/s INSTALL_SILENT=1` |

### Packaged Applications (Not Installers)

| Type | Detection Confidence |
|------|---------------------|
| **PyInstaller App** | 85% |
| **cx_Freeze App** | 80% |

## ⚔️ Brute Force Parameter Discovery

When no installer type is detected, SwitchCraft automatically tries these help arguments:

```
/?  --help  -h  /help  /h  -?  --info  -help  --usage  -V  --version  /info  -i  --silent  /silent
```

The output is analyzed for common patterns and displayed in the GUI.

## 📦 Archive Extraction & Nested Analysis

If no silent switches are found for the main EXE, SwitchCraft will:

1. **Attempt to extract** the EXE using 7-Zip (treats EXE as a self-extracting archive)
2. **Scan for nested installers** (MSI, EXE) inside the extracted content
3. **Analyze each nested executable** for silent install parameters
4. **Display alternative installation instructions** showing which file to run

> [!TIP]
> Requires 7-Zip installed (`C:\Program Files\7-Zip\7z.exe`). If a main installer shows no switches but contains a nested MSI, you can extract it manually and run `msiexec /i nested.msi /qn`.

### Silent Installation Disabled Detection

SwitchCraft can detect when developers have **intentionally disabled** silent installation:
- Binary flags like `SilentModeDisabled`, `RequireGUI`
- Help text indicating "silent mode not supported"

## 🎨 Modern UI Features

The Modern UI (Flet-based) includes several enhancements over the Legacy version:

### Navigation & Organization
- **Category-Based Sidebar**: Organized into Dashboard, Apps & Devices, Tools, and System categories
- **Home View**: Quick access to common actions and recent items
- **Dashboard**: Statistics, charts, and activity overview
- **Library**: Personal collection with folder management and search

### Intune Management
- **Intune Store Browser**: Browse all your Intune applications with:
  - Application logos and metadata
  - Assignment information
  - Direct packaging wizard integration
  - Group assignment details
- **Group Manager**: Comprehensive Entra ID (Azure AD) group management
  - Browse, search, and filter groups
  - Create new Security or Microsoft 365 groups
  - Delete groups (with safety toggle)
  - Manage group members (add/remove users)
  - Search users by name or email
- **Stack Manager**: Organize applications into deployment stacks

### Advanced Tools
- **Detection Tester**: Test detection rules (Registry, File, MSI) locally before uploading
- **WingetCreate Manager**: Create and manage Winget manifests with GitHub integration
- **macOS Wizard**: Generate install.sh scripts and create DMG/PKG packages
- **Script Upload**: Upload and manage PowerShell scripts for Intune

### User Experience
- **Notification Center**: In-app notification drawer with read/unread status
  - Desktop notifications for important events
  - Notification bell icon with unread count badge
  - Click to open/close notification drawer
  - Mark individual notifications as read
  - Clear all notifications
- **Loading Screen**: Professional loading experience similar to Remote Desktop Manager
- **Multi-Language**: Immediate language switching (English/German) without restart
- **Build Information**: Version and build date displayed in settings
- **Theme Support**: Light, Dark, and System theme modes
- **About Information**: "Brought by" and "Created with AI" credits in settings
