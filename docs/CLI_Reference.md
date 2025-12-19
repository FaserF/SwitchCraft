# SwitchCraft CLI Reference

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
