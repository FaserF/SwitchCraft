# SwitchCraft 🧙‍♂️

![SwitchCraft Logo](switchcraft_logo.png)

**SwitchCraft** is your ultimate cross-platform utility for identifying silent installation parameters for EXE and MSI packages. Designed for IT Admins, Packagers, and Developers.

## ✨ Features

- **🔎 Universal Analysis**:
  - **MSI**: Extracts `ProductCode`, `UpgradeCode`, and standard `/qn` switches.
  - **EXE**: Detects **NSIS**, **Inno Setup**, **InstallShield**, **Wise**, and **7-Zip SFX** archives.
  - **Metadata**: Parses internal metadata to find Developer, Version, and Product Name.
- **📦 Winget Integration**: Automatically checks if the package exists in the **Windows Package Manager** (winget) repository and provides a direct link to the manifest.
- **🖥️ GUI & Drag'n'Drop**: Modern, dark-mode friendly Desktop interface. Simply drag your installer onto the window!
- **⚔️ Brute Force Mode**: If no known signature is found, suggests standard help arguments (`/?`, `--help`, `-h`) to discover hidden switches.
- **🔧 Cross-Platform**: Built with Python, running on Windows, Linux, and macOS.
- **🚀 CI/CD Ready**: Fully automated build and release workflows.

## 🚀 Installation

### Pre-built Binaries
Download the latest standalone executable from the [Releases](https://github.com/FaserF/SwitchCraft/releases) page. No Python installation required!

### From Source
```bash
git clone https://github.com/FaserF/SwitchCraft.git
cd SwitchCraft
pip install .
```

## 💻 Usage

### GUI
Simply run the application:
```bash
switchcraft
# or
python -m switchcraft.gui.app
```
Then **Drag & Drop** your installer into the window.

### CLI
```bash
switchcraft analyze setup.exe --json
```

## 🛠️ Development

### Prerequisites
- Python 3.9+
- `pip install -r requirements.txt` (or via `pyproject.toml`)

### Running Tests
We enforce high code quality with comprehensive unit tests.
```bash
python -m unittest discover tests
```

### Building EXE
```bash
pyinstaller switchcraft.spec
```

## 🤝 Contributing
Open Source under the **MIT License**. PRs are welcome!

## 📜 License
MIT © 2025 FaserF
