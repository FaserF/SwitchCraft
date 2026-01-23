# SwitchCraft CLI Reference

SwitchCraft provides a powerful command-line interface for automation, CI/CD pipelines, and scripting. This reference documents all available commands in Linux man-page style.

## NAME

**switchcraft** — The Ultimate Packaging Assistant CLI

## SYNOPSIS

```bash
switchcraft [OPTIONS] COMMAND [ARGS]...
```

## DESCRIPTION

SwitchCraft CLI enables you to analyze installers, manage Intune packages, interact with Winget, manage Entra ID groups, and automate deployment workflows — all from the command line.

## GLOBAL OPTIONS

| Option | Description |
|--------|-------------|
| `--version` | Show version information and exit |
| `--help` | Show help message and exit |
| `--json` | Output results in JSON format (where applicable) |

## ENVIRONMENT VARIABLES

| Variable | Description |
|----------|-------------|
| `SWITCHCRAFT_SUPPRESS_HEADER` | Set to suppress debug header in logs |

---

## COMMANDS

### analyze

Analyze an installer file to detect silent switches and metadata.

**Synopsis:**
```bash
switchcraft analyze <FILEPATH> [--json]
```

**Arguments:**
- `FILEPATH` — Path to the installer file (MSI, EXE, DMG, PKG)

**Options:**
- `--json` — Output analysis results in JSON format

**Examples:**
```bash
# Analyze an MSI installer
switchcraft analyze installer.msi

# Analyze with JSON output for scripting
switchcraft analyze setup.exe --json

# Analyze a macOS package
switchcraft analyze app.dmg
```

**Output:**
Returns product name, version, installer type, silent install/uninstall switches, and confidence level.

---

### config

Manage SwitchCraft configuration values and secrets.

**Synopsis:**
```bash
switchcraft config <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### config get

Read a configuration value.

```bash
switchcraft config get <KEY>
```

**Example:**
```bash
switchcraft config get Language
switchcraft config get IntuneTenantId
```

#### config set

Set a configuration value.

```bash
switchcraft config set <KEY> <VALUE>
```

**Example:**
```bash
switchcraft config set Language de-DE
switchcraft config set IntuneTenantId your-tenant-id
switchcraft config set IntuneClientId your-client-id
```

#### config set-secret

Securely store a secret in Windows Credential Manager.

```bash
switchcraft config set-secret <KEY> [-v VALUE]
```

If `-v` is not provided, the secret is prompted securely (hidden input).

**Example:**
```bash
# Prompted input (recommended)
switchcraft config set-secret IntuneClientSecret

# Direct value (use with caution)
switchcraft config set-secret IntuneClientSecret -v "my-secret"
```

#### config encrypt

Encrypt a value for use in Registry/GPO deployments.

```bash
switchcraft config encrypt [--plaintext VALUE]
```

**Example:**
```bash
switchcraft config encrypt
# Enter plaintext at prompt...
# Output: gAAAAABk... (Store in Registry with _ENC suffix)
```

---

### winget

Interact with the Windows Package Manager (Winget).

> **Note:** Requires the `winget` addon to be installed.

**Synopsis:**
```bash
switchcraft winget <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### winget search

Search for packages in the Winget repository.

```bash
switchcraft winget search <QUERY>
```

**Example:**
```bash
switchcraft winget search "Visual Studio Code"
switchcraft winget search chrome
```

#### winget install

Install a package via Winget.

```bash
switchcraft winget install <PKG_ID> [--scope user|machine]
```

**Options:**
- `--scope` — Install scope: `user` or `machine` (default: `machine`)

**Example:**
```bash
switchcraft winget install Microsoft.VisualStudioCode
switchcraft winget install Google.Chrome --scope user
```

#### winget info

Show detailed information about a package.

```bash
switchcraft winget info <PKG_ID> [--json]
```

**Example:**
```bash
switchcraft winget info Mozilla.Firefox
switchcraft winget info 7zip.7zip --json
```

#### winget list-installed

List all installed Winget packages.

```bash
switchcraft winget list-installed [--json]
```

---

### intune

Intune packaging and upload tools.

**Synopsis:**
```bash
switchcraft intune <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### intune tool

Check or download the IntuneWinAppUtil packaging tool.

```bash
switchcraft intune tool
```

Downloads the tool automatically if not present.

#### intune package

Create an `.intunewin` package for Intune deployment.

```bash
switchcraft intune package <SETUP_FILE> -o <OUTPUT> -s <SOURCE> [--quiet|--verbose]
```

**Options:**
- `-o, --output` — Output folder for the package (required)
- `-s, --source` — Source folder containing the installer (required)
- `--quiet/--verbose` — Control tool output verbosity (default: quiet)

**Example:**
```bash
switchcraft intune package setup.exe -o dist -s .
switchcraft intune package installer.msi -o C:\Packages -s C:\Source --verbose
```

#### intune upload

Upload an `.intunewin` package directly to Microsoft Intune.

```bash
switchcraft intune upload <INTUNEWIN> --name <NAME> --publisher <PUB> \
    --install-cmd <CMD> --uninstall-cmd <CMD> [--description <DESC>]
```

**Prerequisites:**
Configure credentials first:
```bash
switchcraft config set IntuneTenantId <your-tenant-id>
switchcraft config set IntuneClientId <your-client-id>
switchcraft config set-secret IntuneClientSecret
```

**Options:**
- `--name` — App display name (required)
- `--publisher` — App publisher (required)
- `--install-cmd` — Install command line (required)
- `--uninstall-cmd` — Uninstall command line (required)
- `--description` — App description (optional)

**Example:**
```bash
switchcraft intune upload myapp.intunewin \
    --name "My Application" \
    --publisher "Contoso Ltd" \
    --install-cmd "setup.exe /S" \
    --uninstall-cmd "uninstall.exe /S" \
    --description "Internal productivity tool"
```

---

### addons

Manage SwitchCraft extension addons.

**Synopsis:**
```bash
switchcraft addons <SUBCOMMAND>
```

**Subcommands:**

#### addons list

List installed addons and their status.

```bash
switchcraft addons list
```

#### addons install

Install an addon.

```bash
switchcraft addons install <ADDON_ID>
```

**Available Addon IDs:**
- `advanced` — Advanced analyzer features
- `winget` — Winget integration
- `ai` — AI-powered assistance
- `all` — Install all addons

**Example:**
```bash
switchcraft addons install winget
switchcraft addons install all
```

---

### logs

Manage session logging.

**Synopsis:**
```bash
switchcraft logs <SUBCOMMAND>
```

**Subcommands:**

#### logs export

Export session logs to a file.

```bash
switchcraft logs export [-o OUTPUT]
```

**Options:**
- `-o, --output` — Output file path (default: `switchcraft_session.log`)

**Example:**
```bash
switchcraft logs export
switchcraft logs export -o debug_session.log
```

---

### history

Manage analysis history.

**Synopsis:**
```bash
switchcraft history <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### history list

List analysis history entries.

```bash
switchcraft history list [--json] [-n LIMIT]
```

**Options:**
- `--json` — Output in JSON format
- `-n, --limit` — Number of entries to show (default: 20)

**Example:**
```bash
switchcraft history list
switchcraft history list -n 50 --json
```

#### history clear

Clear all analysis history.

```bash
switchcraft history clear
```

Prompts for confirmation before clearing.

#### history export

Export analysis history to a JSON file.

```bash
switchcraft history export -o <OUTPUT>
```

**Example:**
```bash
switchcraft history export -o history_backup.json
```

---

### detection

Test Intune detection rules locally before deployment.

**Synopsis:**
```bash
switchcraft detection test --type <TYPE> [OPTIONS]
```

**Detection Types:**

#### Registry Detection

Test if a registry key/value exists and matches expected value.

```bash
switchcraft detection test --type registry \
    --key <KEY_PATH> --value <VALUE_NAME> [--expected <VALUE>]
```

**Example:**
```bash
switchcraft detection test --type registry \
    --key "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion" \
    --value "ProgramFilesDir"

switchcraft detection test --type registry \
    --key "HKLM\SOFTWARE\MyApp" \
    --value "Version" \
    --expected "1.2.3"
```

#### MSI Detection

Test if an MSI product is installed by its Product Code.

```bash
switchcraft detection test --type msi --product-code <GUID>
```

**Example:**
```bash
switchcraft detection test --type msi \
    --product-code "{12345678-1234-1234-1234-123456789012}"
```

#### File Detection

Test if a file exists and optionally compare its version.

```bash
switchcraft detection test --type file \
    --path <FILE_PATH> [--version <VERSION>] [--operator eq|ge|le|gt|lt]
```

**Options:**
- `--operator` — Version comparison operator (default: `ge`)

**Example:**
```bash
switchcraft detection test --type file --path "C:\Program Files\MyApp\app.exe"

switchcraft detection test --type file \
    --path "C:\Program Files\MyApp\app.exe" \
    --version "2.0.0" \
    --operator ge
```

#### Script Detection

Test a PowerShell detection script.

```bash
switchcraft detection test --type script --script <SCRIPT_FILE>
```

**Example:**
```bash
switchcraft detection test --type script --script detection.ps1
```

---

### groups

Manage Entra ID (Azure AD) groups via Microsoft Graph API.

**Prerequisites:**
Configure Graph API credentials:
```bash
switchcraft config set IntuneTenantId <tenant>
switchcraft config set IntuneClientId <client>
switchcraft config set-secret IntuneClientSecret
```

**Synopsis:**
```bash
switchcraft groups <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### groups list

List Entra ID groups.

```bash
switchcraft groups list [-s SEARCH] [--json]
```

**Example:**
```bash
switchcraft groups list
switchcraft groups list -s "IT Department"
switchcraft groups list --json
```

#### groups create

Create a new Entra ID group.

```bash
switchcraft groups create -n <NAME> [-d DESCRIPTION] [--type security|m365]
```

**Example:**
```bash
switchcraft groups create -n "App Testers" -d "Beta testing group"
switchcraft groups create -n "Project Team" --type m365
```

#### groups delete

Delete an Entra ID group.

```bash
switchcraft groups delete --id <GROUP_ID>
```

Prompts for confirmation.

#### groups members

List members of a group.

```bash
switchcraft groups members --id <GROUP_ID> [--json]
```

#### groups add-member

Add a user to a group.

```bash
switchcraft groups add-member -g <GROUP_ID> -u <USER_ID>
```

#### groups remove-member

Remove a user from a group.

```bash
switchcraft groups remove-member -g <GROUP_ID> -u <USER_ID>
```

---

### exchange

Exchange Online management via Microsoft Graph API.

**Prerequisites:**
Same as `groups` — requires Graph API credentials.

**Synopsis:**
```bash
switchcraft exchange <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### exchange oof

Get or set Out of Office (OOF) settings.

```bash
# Get OOF settings
switchcraft exchange oof get -u <USER>

# Set OOF settings
switchcraft exchange oof set -u <USER> --enabled --message "I'm away"
switchcraft exchange oof set -u <USER> --disabled
```

**Example:**
```bash
switchcraft exchange oof get -u john@contoso.com
switchcraft exchange oof set -u john@contoso.com --enabled -m "On vacation until Monday"
```

#### exchange delegates

List mailbox delegates.

```bash
switchcraft exchange delegates -u <USER> [--json]
```

#### exchange mail-search

Search messages in a mailbox.

```bash
switchcraft exchange mail-search -u <USER> [-q QUERY] [--json]
```

**Example:**
```bash
switchcraft exchange mail-search -u john@contoso.com -q "project update"
```

---

### stacks

Manage deployment stacks for batch installations.

**Synopsis:**
```bash
switchcraft stacks <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### stacks list

List all deployment stacks.

```bash
switchcraft stacks list [--json]
```

#### stacks create

Create a new deployment stack.

```bash
switchcraft stacks create -n <NAME>
```

**Example:**
```bash
switchcraft stacks create -n "Developer Workstation"
```

#### stacks delete

Delete a deployment stack.

```bash
switchcraft stacks delete -n <NAME>
```

#### stacks add

Add an item to a stack.

```bash
switchcraft stacks add -n <STACK_NAME> -i <ITEM>
```

**Example:**
```bash
switchcraft stacks add -n "Developer Workstation" -i "Microsoft.VisualStudioCode"
switchcraft stacks add -n "Developer Workstation" -i "Git.Git"
switchcraft stacks add -n "Developer Workstation" -i "Docker.DockerDesktop"
```

#### stacks show

Show items in a stack.

```bash
switchcraft stacks show -n <NAME>
```

#### stacks deploy

Deploy (install) all items in a stack.

```bash
switchcraft stacks deploy -n <NAME> [--dry-run]
```

**Options:**
- `--dry-run` — Show what would be installed without actually installing

**Example:**
```bash
# Preview deployment
switchcraft stacks deploy -n "Developer Workstation" --dry-run

# Execute deployment
switchcraft stacks deploy -n "Developer Workstation"
```

---

### library

Manage the local `.intunewin` package library.

**Synopsis:**
```bash
switchcraft library <SUBCOMMAND> [OPTIONS]
```

**Subcommands:**

#### library scan

Scan directories for `.intunewin` files.

```bash
switchcraft library scan [-d DIRECTORY]... [--json]
```

**Options:**
- `-d, --dirs` — Directories to scan (default: Downloads, Desktop)

**Example:**
```bash
switchcraft library scan
switchcraft library scan -d "C:\Packages" -d "D:\IntuneApps"
switchcraft library scan --json
```

#### library info

Show detailed information about an `.intunewin` file.

```bash
switchcraft library info <INTUNEWIN_FILE> [--json]
```

**Example:**
```bash
switchcraft library info myapp.intunewin
switchcraft library info C:\Packages\app.intunewin --json
```

---

## EXIT CODES

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error or command failure |

## FILES

| Path | Description |
|------|-------------|
| `%APPDATA%\FaserF\SwitchCraft\` | Configuration and data directory |
| `%APPDATA%\FaserF\SwitchCraft\stacks.json` | Deployment stacks definition |
| `%APPDATA%\FaserF\SwitchCraft\history.json` | Analysis history |

## SEE ALSO

- [Installation Guide](/installation)
- [Intune Setup](/INTUNE_SETUP)
- [Winget Integration](/WINGET)
- [Security Guide](/SECURITY)

## REPORTING BUGS

Report bugs at: https://github.com/FaserF/SwitchCraft/issues
