# ✨ Features

- **🔎 Universal Analysis**:
  - **MSI**: Extracts `ProductCode`, `UpgradeCode`, manufacturer, version, and standard `/qn` switches
  - **EXE**: Auto-detects 20+ installer frameworks and suggests appropriate silent switches
  - **Metadata**: Parses PE version info for product name, version, and company
- **📦 Winget Integration**: Automatically checks if the package exists in the **Windows Package Manager** (winget) repository
- **🔔 Notification System**: Get native desktop alerts when analysis completes or packages are created
- **✍️ Script Signing**: Automatically sign generated PowerShell scripts with your code-signing certificate (auto-detected or PFX)
- **⚔️ Automatic Brute Force**: Runs 15+ help argument variations to discover switches
- **🧩 Project Stacks**: Group applications into named stacks for one-click batch deployment
- **📊 Interactive Dashboard**: Visual overview of your packaging activity, statistics, and recent actions
- **📚 My Library**: Personal history of analyzed and packaged applications with search and filter capabilities
- **👥 Community Database**: Crowdsourced database of silent switches with automated IssueOps contributions
- **🌐 Multi-Language**: English and German interface

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
