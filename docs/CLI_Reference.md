# SwitchCraft CLI Reference

SwitchCraft can be used entirely from the command line for automation, CI/CD, and troubleshooting.

## Usage

```bash
switchcraft [OPTIONS] COMMAND [ARGS]...
```

### Global Options

*   `--json`: Output analysis results in JSON format (for the `analyze` command).
*   `--version`: Show version information.
*   `--help`: Show detailed help message.
*   `--factory-reset`: **Dangerous**. Wipe all user data and settings.

## Commands

### `analyze`
Analyze an installer file to detect silent switches and metadata.
```bash
switchcraft analyze <filepath> [--json]
```

### `config`
Manage configuration values and secrets.
*   `switchcraft config get <key>` - Read a value.
*   `switchcraft config set <key> <value>` - Set a preference.
*   `switchcraft config set-secret <key> [-v value]` - Securely store a secret (e.g. API Token) in Credential Manager.
*   `switchcraft config encrypt` - Encrypt a plain string for use in Registry GPO (outputs AES ciphertext).

### `logs`
Manage session logs.
*   `switchcraft logs export --output switchcraft_logs.zip` - Export current session diagnostics.

### `winget`
Interact with the Windows Package Manager.
*   `switchcraft winget search <query>` - Query the Winget repository.
*   `switchcraft winget install <pkg_id> [--scope user|machine]` - Install a package.

### `intune`
Intune packaging and upload tools.
*   `switchcraft intune tool`: Check/Download `IntuneWinAppUtil`.
*   `switchcraft intune package <setup_file> -o <out_folder> -s <source_folder>`: Create `.intunewin`.
*   `switchcraft intune upload <intunewin> --name "App Name" --publisher "Pub" ...`: Upload directly to Intune.
    *   **Prerequisites**: Requires `IntuneTenantId`, `IntuneClientId`, and `IntuneClientSecret` to be configured.

### `addons`
Manage SwitchCraft extensions.
*   `switchcraft addons list` - Show installed addons.
*   `switchcraft addons install <id>` - Install an addon (IDs: `advanced`, `winget`, `ai`).

## Examples

**Analyze an MSI and output JSON:**
```bash
switchcraft analyze installer.msi --json
```

**Securely store Intune Authentication Secret:**
```bash
switchcraft config set-secret IntuneClientSecret -v "my-secret-value-123"
```

**Create an Encrypted Value for GPO:**
```bash
switchcraft config encrypt
# Enter plaintext at prompt...
# Output: gAAAAABk... (Use this in Registry as KeyName_ENC)
```

**Package for Intune:**
```bash
switchcraft intune package setup.exe -o dist -s .
```

SwitchCraft can be used entirely from the command line.

## Usage

```bash
switchcraft [OPTIONS] COMMAND [ARGS]...
```

To analyze a file directly (backward compatibility):
```bash
switchcraft setup.exe
```

## Global Options

*   `--json`: Output analysis results in JSON format.
*   `--version`: Show version information.
*   `--help`: Show this message and exit.

## Commands

### `analyze`
Analyze an installer file.
```bash
switchcraft analyze <filepath> [--json]
```

### `config`
Manage configuration values.
*   `switchcraft config get <key>`
*   `switchcraft config set <key> <value>`
*   `switchcraft config set-secret <key> <value>` (Secure storage)

### `winget`
Interact with Winget.
*   `switchcraft winget search <query>`
*   `switchcraft winget install <pkg_id> [--scope user|machine]`

### `intune`
Intune packaging and upload tools.
*   `switchcraft intune tool`: Check/Download IntuneWinAppUtil.
*   `switchcraft intune package <setup_file> -o <out_folder> -s <source_folder>`
*   `switchcraft intune upload <intunewin> --name "App Name" --publisher "Pub" ...`
    *   Requires `IntuneTenantId`, `IntuneClientId`, `IntuneClientSecret` in config.

### `addons`
Manage addons.
*   `switchcraft addons list`
*   `switchcraft addons install <id>` (ids: `advanced`, `winget`, `ai`, `all`)

## Examples

**Analyze an MSI and output JSON:**
```bash
switchcraft analyze installer.msi --json
```

**Search for a package:**
```bash
switchcraft winget search "Google Chrome"
```

**Install a package:**
```bash
switchcraft winget install Google.Chrome
```

**Package for Intune:**
```bash
switchcraft intune package setup.exe -o dist -s .
```
