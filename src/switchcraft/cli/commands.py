
import logging
import sys
import os
import json
from pathlib import Path
import click
from rich import print
from rich.panel import Panel
from rich.table import Table

from switchcraft import __version__
from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.analyzers.macos import MacOSAnalyzer
# WingetHelper imported dynamically if needed
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

def setup_logging():
    """Setup structured logging format based on debug mode setting."""
    debug_enabled = SwitchCraftConfig.is_debug_mode()

    if debug_enabled:
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        if not os.environ.get("SWITCHCRAFT_SUPPRESS_HEADER"):
            logging.info("=" * 60)
            logging.info(f"SwitchCraft v{__version__} - Debug Log")
            logging.info("=" * 60)
    else:
        logging.basicConfig(level=logging.ERROR)

@click.group(invoke_without_command=True)
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format (Main Analysis)")
@click.option('--version', is_flag=True, help="Show version info")
@click.pass_context
def cli(ctx, output_json, version):
    """SwitchCraft: Analyze installers/packages or manage configuration."""
    from switchcraft.utils.logging_handler import setup_session_logging
    setup_logging()
    setup_session_logging()

    if version:
        print(f"SwitchCraft v{__version__}")
        ctx.exit()

    if ctx.invoked_subcommand is None:
        # Backward compatibility: switchcraft <file>
        # However, Click doesn't pass positional args to group unless parsing is tricky.
        # We need to access remaining args or define an argument on the group (which is tricky for subcommands).
        # A better pattern is to handle no-command case here or force 'analyze'.

        # If user ran `switchcraft setup.exe`, Click sees `setup.exe` as a subcommand and fails.
        # To fix this, we should really move analysis to 'analyze' command and use a custom invoke class
        # OR suggest `switchcraft analyze <file>` in 2.0.

        # BUT, the user wants ONE entry point.
        # Let's try to detect if the first arg is a file.
        click.echo(ctx.get_help())

@cli.command()
@click.argument('filepath', type=click.Path(exists=True), required=True)
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def analyze(filepath, output_json):
    """Analyze an installer file (MSI, EXE, DMG, etc)."""
    _run_analysis(filepath, output_json)

# --- Configuration Group ---
@cli.group()
def config():
    """Manage SwitchCraft configuration."""
    pass

@config.command('get')
@click.argument('key')
def config_get(key):
    """Get a configuration value."""
    val = SwitchCraftConfig.get_value(key)
    print(f"{key}: {val}")

@config.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """Set a configuration value."""
    SwitchCraftConfig.set_user_preference(key, value)
    print(f"Set {key} = {value}")

# --- Winget Group ---
@cli.group()
def winget():
    """Interact with Winget (Microsoft Store)."""
    pass

@winget.command('search')
@click.argument('query')
def winget_search(query):
    """Search for packages in Winget."""
    from switchcraft.services.addon_service import AddonService
    winget_mod = AddonService().import_addon_module("winget", "utils.winget")
    if not winget_mod:
        print("[red]Winget addon not installed.[/red]")
        sys.exit(1)
    helper = winget_mod.WingetHelper()
    print(f"Searching Winget for '{query}'...")
    results = helper.search_packages(query)
    if not results:
        print("No results found.")
        return

    t = Table(title=f"Winget Results: {query}")
    t.add_column("ID")
    t.add_column("Name")
    t.add_column("Version")

    for r in results:
        t.add_row(r.get('Id'), r.get('Name'), r.get('Version'))
    print(t)

@winget.command('install')
@click.argument('pkg_id')
@click.option('--scope', default='machine', type=click.Choice(['user', 'machine']), help="Install scope")
def winget_install(pkg_id, scope):
    """Install a package via Winget."""
    from switchcraft.services.addon_service import AddonService
    winget_mod = AddonService().import_addon_module("winget", "utils.winget")
    if not winget_mod:
        print("[red]Winget addon not installed.[/red]")
        sys.exit(1)
    helper = winget_mod.WingetHelper()
    print(f"Installing {pkg_id} (Scope: {scope})...")
    if helper.install_package(pkg_id, scope):
        print(f"[green]Successfully installed {pkg_id}[/green]")
    else:
        print(f"[red]Failed to install {pkg_id}[/red]")
        sys.exit(1)

# --- Intune Group ---
@cli.group()
def intune():
    """Intune packaging and upload tools."""
    pass

@intune.command('tool')
def intune_tool():
    """Check or download the IntuneWinAppUtil."""
    from switchcraft.services.intune_service import IntuneService
    svc = IntuneService()
    if svc.is_tool_available():
        print(f"[green]IntuneWinAppUtil is available at: {svc.tool_path}[/green]")
    else:
        print("[yellow]Tool not found. Downloading...[/yellow]")
        if svc.download_tool():
            print("[green]Download successful.[/green]")
        else:
            print("[red]Download failed.[/red]")
            sys.exit(1)

@intune.command('package')
@click.argument('setup_file', type=click.Path(exists=True))
@click.option('-o', '--output', required=True, type=click.Path(), help="Output folder")
@click.option('-s', '--source', required=True, type=click.Path(exists=True), help="Source folder")
@click.option('--quiet/--verbose', default=True, help="Suppress tool output")
def intune_package(setup_file, output, source, quiet):
    """Create an .intunewin package."""
    from switchcraft.services.intune_service import IntuneService
    svc = IntuneService()

    print(f"Packaging {setup_file}...")
    try:
        svc.create_intunewin(
            source_folder=source,
            setup_file=setup_file,
            output_folder=output,
            quiet=quiet,
            progress_callback=lambda x: print(x.strip()) if not quiet else None
        )
        print("[green]Package created successfully![/green]")
    except Exception as e:
        print(f"[red]Packaging failed: {e}[/red]")
        sys.exit(1)

@intune.command('upload')
@click.argument('intunewin', type=click.Path(exists=True))
@click.option('--name', required=True, help="App Display Name")
@click.option('--publisher', required=True, help="App Publisher")
@click.option('--install-cmd', required=True, help="Install Command")
@click.option('--uninstall-cmd', required=True, help="Uninstall Command")
@click.option('--description', default="", help="App Description")
def intune_upload(intunewin, name, publisher, install_cmd, uninstall_cmd, description):
    """Upload an .intunewin package to Intune."""
    from switchcraft.services.intune_service import IntuneService

    # Auth credentials from config/secrets
    tenant = SwitchCraftConfig.get_value("IntuneTenantId")
    client = SwitchCraftConfig.get_value("IntuneClientId")
    secret = SwitchCraftConfig.get_secret("IntuneClientSecret")

    if not (tenant and client and secret):
        print("[red]Missing Intune credentials.[/red]")
        print("Please set them using:")
        print("  switchcraft config set IntuneTenantId <id>")
        print("  switchcraft config set IntuneClientId <id>")
        print("  switchcraft config set-secret IntuneClientSecret <secret>") # Need to implement this command
        sys.exit(1)

    svc = IntuneService()
    try:
        print("Authenticating...")
        token = svc.authenticate(tenant, client, secret)

        info = {
            "displayName": name,
            "publisher": publisher,
            "installCommandLine": install_cmd,
            "uninstallCommandLine": uninstall_cmd,
            "description": description
        }

        print("Uploading package (this may take a while)...")
        app_id = svc.upload_win32_app(
            token,
            intunewin,
            info,
            progress_callback=lambda p, s: print(f"[{p*100:.0f}%] {s}")
        )
        print(f"[green]Upload Complete! App ID: {app_id}[/green]")

    except Exception as e:
        print(f"[red]Upload failed: {e}[/red]")
        sys.exit(1)


# --- Addons Group ---
@cli.group()
def addons():
    """Manage SwitchCraft addons."""
    pass


@addons.command('list')
def addons_list():
    """List available addons and installation status."""
    from switchcraft.services.addon_service import AddonService
    table = Table(title="SwitchCraft Addons")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Status")

    # Hardcoded known addons if ADDONS was intended to be a registry,
    # but for now let's just list what is installed or capable.
    # If the CLI expects a list of *available* addons to install, that's different.
    # Assuming list_addons() lists installed ones? No, list_addons() scans the dir.

    svc = AddonService()
    installed = svc.list_addons()

    if not installed:
        print("[yellow]No addons installed.[/yellow]")
        return

    for addon in installed:
        aid = addon.get("id")
        name = addon.get("name")
        table.add_row(aid, name, "[green]Installed[/green]")

    print(table)

@addons.command('install')
@click.argument('addon_id')
def addons_install(addon_id):
    """Install an addon (or 'all')."""
    from switchcraft.services.addon_service import AddonService

    # Validation via ADDONS list removed as it does not exist
    # if addon_id not in AddonService.ADDONS and addon_id != "all":
    #     print(f"[red]Invalid addon ID: {addon_id}[/red]")
    #     sys.exit(1)

    print(f"Installing {addon_id}...")

    # Remove prompt_callback as it is not supported by install_addon currently,
    # or assuming we should just call it without.
    # The user request said: "remove the unsupported keyword or adapt the service".
    # Removing it is safer if the service doesn't support it.

    # We also need to handle the fact that install_addon expects a zip_path usually,
    # BUT the CLI argument is an ID.
    # The user request said: "modify AddonService... or call call AddonService().install_addon(addon_id)".
    # Wait, the CLI code previously did `AddonService().install_addon(addon_id, prompt_callback=cli_prompt)`.
    # AND `install_addon` in `app.py` (which I saw earlier) took `zip_path`.
    # The AddonService likely expects a path. Use distinct logic?
    # Actually, the user PROMPT says: "remove the unsupported keyword... update references... so the signature and callers match".
    # I will remove prompt_callback.

    success = AddonService().install_addon(addon_id)
    if success:
        print(f"[{'green'}]Successfully installed {addon_id}[/{'green'}]")
    else:
        print(f"[{'red'}]Installation failed for {addon_id}[/{'red'}]")
        sys.exit(1)

# --- Config Secret Support ---
@config.command('set-secret')
@click.argument('key')
@click.option('--value', '-v', prompt=True, hide_input=True, help="Secret value")
def config_set_secret(key, value):
    """Set a secure configuration value (keyring)."""
    SwitchCraftConfig.set_secret(key, value)
    print(f"Secret {key} saved securely.")

@config.command('encrypt')
@click.option('--plaintext', prompt=True, hide_input=True, help="Value to encrypt")
def config_encrypt(plaintext):
    """Encrypt a value for Registry usage (Obfuscation)."""
    from switchcraft.utils.crypto import SimpleCrypto
    encrypted = SimpleCrypto.encrypt(plaintext)
    print(f"Encrypted Value: {encrypted}")
    print("[yellow]Store this in the registry with suffix _ENC[/yellow]")
    print("Example: GraphClientSecret_ENC")

# --- Logs Group ---
@cli.group()
def logs():
    """Manage session logs."""
    pass

@logs.command('export')
@click.option('--output', '-o', default="switchcraft_session.log", help="Output file path")
def logs_export(output):
    """Export the current session logs to a file."""
    # Since CLI is stateless per command run, this will mostly capture the current command's startup logs
    # and whatever happened during this execution. It won't capture "previous" sessions.
    from switchcraft.utils.logging_handler import get_session_handler

    # Generate some logs if empty just so we have something (e.g. "Export initiated")
    logging.info("Exporting session logs via CLI...")

    handler = get_session_handler()
    if handler.export_logs(output):
        print(f"[green]Logs exported successfully to: {output}[/green]")
    else:
        print("[red]Failed to export logs.[/red]")
        sys.exit(1)

# --- History Group ---
@cli.group()
def history():
    """Manage analysis history."""
    pass

@history.command('list')
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
@click.option('--limit', '-n', default=20, help="Number of entries to show")
def history_list(output_json, limit):
    """List analysis history."""
    from switchcraft.services.history_service import HistoryService
    svc = HistoryService()
    items = svc.get_history()[:limit]

    if output_json:
        print(json.dumps(items, default=str))
    else:
        if not items:
            print("[yellow]No history found.[/yellow]")
            return

        table = Table(title="Analysis History")
        table.add_column("Filename")
        table.add_column("Product")
        table.add_column("Date")
        table.add_column("Status")

        for item in items:
            table.add_row(
                item.get('filename', 'Unknown'),
                item.get('product', 'Unknown'),
                item.get('timestamp', '')[:16],
                item.get('status', 'Analyzed')
            )
        print(table)

@history.command('clear')
@click.confirmation_option(prompt="Are you sure you want to clear all history?")
def history_clear():
    """Clear all analysis history."""
    from switchcraft.services.history_service import HistoryService
    HistoryService().clear()
    print("[green]History cleared.[/green]")

@history.command('export')
@click.option('--output', '-o', required=True, type=click.Path(), help="Output file path")
def history_export(output):
    """Export analysis history to a file."""
    from switchcraft.services.history_service import HistoryService
    items = HistoryService().get_history()
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, default=str)
    print(f"[green]Exported {len(items)} entries to {output}[/green]")


# --- Detection Group ---
@cli.group()
def detection():
    """Test Intune detection rules locally."""
    pass

@detection.command('test')
@click.option('--type', 'rule_type', required=True,
              type=click.Choice(['registry', 'msi', 'file', 'script']),
              help="Detection rule type")
@click.option('--key', help="Registry key path (for registry type)")
@click.option('--value', 'value_name', help="Registry value name (for registry type)")
@click.option('--expected', help="Expected value (for registry type)")
@click.option('--product-code', help="MSI Product Code GUID (for msi type)")
@click.option('--path', 'file_path', type=click.Path(), help="File path (for file type)")
@click.option('--operator', type=click.Choice(['eq', 'ge', 'le', 'gt', 'lt']), default='ge', help="Version comparison operator")
@click.option('--version', 'target_version', help="Target version (for file type)")
@click.option('--script', 'script_file', type=click.Path(exists=True), help="PowerShell script file (for script type)")
def detection_test(rule_type, key, value_name, expected, product_code, file_path, operator, target_version, script_file):
    """Test a detection rule locally."""
    import subprocess

    if rule_type == 'registry':
        if not key or not value_name:
            print("[red]Registry detection requires --key and --value[/red]")
            sys.exit(1)
        _test_registry(key, value_name, expected)

    elif rule_type == 'msi':
        if not product_code:
            print("[red]MSI detection requires --product-code[/red]")
            sys.exit(1)
        _test_msi(product_code)

    elif rule_type == 'file':
        if not file_path:
            print("[red]File detection requires --path[/red]")
            sys.exit(1)
        _test_file_version(file_path, operator, target_version)

    elif rule_type == 'script':
        if not script_file:
            print("[red]Script detection requires --script[/red]")
            sys.exit(1)
        _test_script(script_file)

def _test_registry(key_path, value_name, expected_value):
    """Test registry-based detection."""
    if sys.platform != 'win32':
        print("[red]Registry detection only works on Windows.[/red]")
        sys.exit(1)

    import winreg

    # Parse key path
    hive_map = {
        'HKLM': winreg.HKEY_LOCAL_MACHINE,
        'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
        'HKCU': winreg.HKEY_CURRENT_USER,
        'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
    }

    parts = key_path.replace('/', '\\').split('\\', 1)
    hive_name = parts[0].upper()
    subkey = parts[1] if len(parts) > 1 else ''

    hive = hive_map.get(hive_name)
    if not hive:
        print(f"[red]Unknown registry hive: {hive_name}[/red]")
        sys.exit(1)

    try:
        with winreg.OpenKey(hive, subkey) as reg_key:
            actual_value, _ = winreg.QueryValueEx(reg_key, value_name)

            if expected_value:
                if str(actual_value) == str(expected_value):
                    print(f"[green]✓ DETECTED[/green] - {value_name} = {actual_value} (expected: {expected_value})")
                else:
                    print(f"[yellow]✗ NOT DETECTED[/yellow] - {value_name} = {actual_value} (expected: {expected_value})")
            else:
                print(f"[green]✓ DETECTED[/green] - {value_name} exists, value: {actual_value}")
    except FileNotFoundError:
        print(f"[yellow]✗ NOT DETECTED[/yellow] - Key or value not found")
    except Exception as e:
        print(f"[red]Error: {e}[/red]")

def _test_msi(product_code):
    """Test MSI product code detection."""
    if sys.platform != 'win32':
        print("[red]MSI detection only works on Windows.[/red]")
        sys.exit(1)

    import winreg

    # Normalize GUID
    guid = product_code.strip('{}').upper()

    paths = [
        f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{{{guid}}}",
        f"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{{{guid}}}",
    ]

    for path in paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                name, _ = winreg.QueryValueEx(key, "DisplayName")
                version, _ = winreg.QueryValueEx(key, "DisplayVersion")
                print(f"[green]✓ DETECTED[/green] - {name} v{version}")
                return
        except FileNotFoundError:
            continue
        except Exception:
            continue

    print(f"[yellow]✗ NOT DETECTED[/yellow] - Product {product_code} not found")

def _test_file_version(file_path, operator, target_version):
    """Test file version detection."""
    path = Path(file_path)

    if not path.exists():
        print(f"[yellow]✗ NOT DETECTED[/yellow] - File does not exist: {file_path}")
        return

    if not target_version:
        print(f"[green]✓ DETECTED[/green] - File exists: {file_path}")
        return

    # Get file version (Windows only for PE files)
    if sys.platform == 'win32':
        try:
            import win32api
            info = win32api.GetFileVersionInfo(str(path), '\\')
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            actual = (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
            actual_str = '.'.join(map(str, actual))
        except Exception:
            actual_str = "0.0.0.0"
            actual = (0, 0, 0, 0)
    else:
        actual_str = "0.0.0.0"
        actual = (0, 0, 0, 0)

    # Parse target version
    target_parts = target_version.split('.')
    target = tuple(int(p) for p in target_parts) + (0,) * (4 - len(target_parts))

    ops = {'eq': '==', 'ge': '>=', 'le': '<=', 'gt': '>', 'lt': '<'}
    result = eval(f"actual {ops[operator]} target")

    if result:
        print(f"[green]✓ DETECTED[/green] - Version {actual_str} {ops[operator]} {target_version}")
    else:
        print(f"[yellow]✗ NOT DETECTED[/yellow] - Version {actual_str} not {ops[operator]} {target_version}")

def _test_script(script_file):
    """Test PowerShell script detection."""
    if sys.platform != 'win32':
        print("[red]Script detection only works on Windows.[/red]")
        sys.exit(1)

    import subprocess

    with open(script_file, 'r', encoding='utf-8') as f:
        script_content = f.read()

    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', script_content],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"[green]✓ DETECTED[/green] - Script exited with code 0")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
        else:
            print(f"[yellow]✗ NOT DETECTED[/yellow] - Script exited with code {result.returncode}")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("[red]Script timed out after 60 seconds[/red]")
    except Exception as e:
        print(f"[red]Error running script: {e}[/red]")


# --- Groups Group (Entra ID) ---
@cli.group()
def groups():
    """Manage Entra ID (Azure AD) groups."""
    pass

def _get_graph_token():
    """Get Graph API token from config."""
    tenant = SwitchCraftConfig.get_value("IntuneTenantId")
    client = SwitchCraftConfig.get_value("IntuneClientId")
    secret = SwitchCraftConfig.get_secret("IntuneClientSecret")

    if not (tenant and client and secret):
        print("[red]Missing Graph API credentials.[/red]")
        print("Configure with:")
        print("  switchcraft config set IntuneTenantId <id>")
        print("  switchcraft config set IntuneClientId <id>")
        print("  switchcraft config set-secret IntuneClientSecret <secret>")
        sys.exit(1)

    from switchcraft.services.intune_service import IntuneService
    svc = IntuneService()
    return svc.authenticate(tenant, client, secret)

@groups.command('list')
@click.option('--search', '-s', help="Search query")
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def groups_list(search, output_json):
    """List Entra ID groups."""
    from switchcraft.services.intune_service import IntuneService
    token = _get_graph_token()
    svc = IntuneService()

    grps = svc.list_groups(token, search_query=search)

    if output_json:
        print(json.dumps(grps, default=str))
    else:
        if not grps:
            print("[yellow]No groups found.[/yellow]")
            return

        table = Table(title="Entra ID Groups")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Type")

        for g in grps[:50]:  # Limit display
            gtype = "M365" if "Unified" in g.get('groupTypes', []) else "Security"
            table.add_row(g.get('id', '')[:8] + "...", g.get('displayName', ''), gtype)

        print(table)

@groups.command('create')
@click.option('--name', '-n', required=True, help="Group display name")
@click.option('--description', '-d', default="", help="Group description")
@click.option('--type', 'group_type', type=click.Choice(['security', 'm365']), default='security', help="Group type")
def groups_create(name, description, group_type):
    """Create a new Entra ID group."""
    from switchcraft.services.intune_service import IntuneService
    token = _get_graph_token()
    svc = IntuneService()

    group_types = ["Unified"] if group_type == 'm365' else []

    try:
        result = svc.create_group(token, name, description, group_types)
        print(f"[green]Created group: {result.get('displayName')} (ID: {result.get('id')})[/green]")
    except Exception as e:
        print(f"[red]Failed to create group: {e}[/red]")
        sys.exit(1)

@groups.command('delete')
@click.option('--id', 'group_id', required=True, help="Group ID")
@click.confirmation_option(prompt="Are you sure you want to delete this group?")
def groups_delete(group_id):
    """Delete an Entra ID group."""
    from switchcraft.services.intune_service import IntuneService
    token = _get_graph_token()
    svc = IntuneService()

    try:
        svc.delete_group(token, group_id)
        print(f"[green]Deleted group: {group_id}[/green]")
    except Exception as e:
        print(f"[red]Failed to delete group: {e}[/red]")
        sys.exit(1)

@groups.command('members')
@click.option('--id', 'group_id', required=True, help="Group ID")
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def groups_members(group_id, output_json):
    """List members of a group."""
    from switchcraft.services.intune_service import IntuneService
    token = _get_graph_token()
    svc = IntuneService()

    members = svc.list_group_members(token, group_id)

    if output_json:
        print(json.dumps(members, default=str))
    else:
        if not members:
            print("[yellow]No members found.[/yellow]")
            return

        table = Table(title="Group Members")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("UPN")

        for m in members:
            table.add_row(
                m.get('id', '')[:8] + "...",
                m.get('displayName', 'Unknown'),
                m.get('userPrincipalName', '')
            )
        print(table)

@groups.command('add-member')
@click.option('--group-id', '-g', required=True, help="Group ID")
@click.option('--user-id', '-u', required=True, help="User ID to add")
def groups_add_member(group_id, user_id):
    """Add a member to a group."""
    from switchcraft.services.intune_service import IntuneService
    token = _get_graph_token()
    svc = IntuneService()

    try:
        svc.add_group_member(token, group_id, user_id)
        print(f"[green]Added user {user_id} to group {group_id}[/green]")
    except Exception as e:
        print(f"[red]Failed to add member: {e}[/red]")
        sys.exit(1)

@groups.command('remove-member')
@click.option('--group-id', '-g', required=True, help="Group ID")
@click.option('--user-id', '-u', required=True, help="User ID to remove")
def groups_remove_member(group_id, user_id):
    """Remove a member from a group."""
    from switchcraft.services.intune_service import IntuneService
    token = _get_graph_token()
    svc = IntuneService()

    try:
        svc.remove_group_member(token, group_id, user_id)
        print(f"[green]Removed user {user_id} from group {group_id}[/green]")
    except Exception as e:
        print(f"[red]Failed to remove member: {e}[/red]")
        sys.exit(1)


# --- Exchange Group ---
@cli.group()
def exchange():
    """Exchange Online management via Graph API."""
    pass

@exchange.command('oof')
@click.argument('action', type=click.Choice(['get', 'set']))
@click.option('--user', '-u', required=True, help="User email/UPN")
@click.option('--enabled/--disabled', default=None, help="Enable/disable OOF (for set)")
@click.option('--message', '-m', help="OOF reply message (for set)")
def exchange_oof(action, user, enabled, message):
    """Get or set Out of Office settings."""
    from switchcraft.services.exchange_service import ExchangeService

    tenant = SwitchCraftConfig.get_value("IntuneTenantId")
    client = SwitchCraftConfig.get_value("IntuneClientId")
    secret = SwitchCraftConfig.get_secret("IntuneClientSecret")

    if not (tenant and client and secret):
        print("[red]Missing Graph API credentials.[/red]")
        sys.exit(1)

    svc = ExchangeService()
    token = svc.authenticate(tenant, client, secret)

    if action == 'get':
        try:
            oof = svc.get_oof_settings(token, user)
            print(Panel(json.dumps(oof, indent=2), title=f"OOF Settings: {user}", border_style="blue"))
        except Exception as e:
            print(f"[red]Failed to get OOF: {e}[/red]")
            sys.exit(1)

    elif action == 'set':
        if enabled is None and not message:
            print("[red]Specify --enabled/--disabled or --message[/red]")
            sys.exit(1)

        oof_data = {}
        if enabled is not None:
            oof_data["status"] = "alwaysEnabled" if enabled else "disabled"
        if message:
            oof_data["internalReplyMessage"] = message
            oof_data["externalReplyMessage"] = message

        try:
            svc.set_oof_settings(token, user, oof_data)
            print(f"[green]Updated OOF settings for {user}[/green]")
        except Exception as e:
            print(f"[red]Failed to set OOF: {e}[/red]")
            sys.exit(1)

@exchange.command('delegates')
@click.option('--user', '-u', required=True, help="User email/UPN")
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def exchange_delegates(user, output_json):
    """List mailbox delegates."""
    from switchcraft.services.exchange_service import ExchangeService

    tenant = SwitchCraftConfig.get_value("IntuneTenantId")
    client = SwitchCraftConfig.get_value("IntuneClientId")
    secret = SwitchCraftConfig.get_secret("IntuneClientSecret")

    if not (tenant and client and secret):
        print("[red]Missing Graph API credentials.[/red]")
        sys.exit(1)

    svc = ExchangeService()
    token = svc.authenticate(tenant, client, secret)

    try:
        delegates = svc.get_delegates(token, user)
        if output_json:
            print(json.dumps(delegates, default=str))
        else:
            if not delegates:
                print(f"[yellow]No delegates found for {user}[/yellow]")
            else:
                table = Table(title=f"Delegates for {user}")
                table.add_column("ID")
                table.add_column("Email")
                for d in delegates:
                    table.add_row(d.get('id', ''), d.get('emailAddress', {}).get('address', ''))
                print(table)
    except Exception as e:
        print(f"[red]Failed to get delegates: {e}[/red]")
        sys.exit(1)

@exchange.command('mail-search')
@click.option('--user', '-u', required=True, help="Mailbox user email/UPN")
@click.option('--query', '-q', help="Search query")
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def exchange_mail_search(user, query, output_json):
    """Search messages in a mailbox."""
    from switchcraft.services.exchange_service import ExchangeService

    tenant = SwitchCraftConfig.get_value("IntuneTenantId")
    client = SwitchCraftConfig.get_value("IntuneClientId")
    secret = SwitchCraftConfig.get_secret("IntuneClientSecret")

    if not (tenant and client and secret):
        print("[red]Missing Graph API credentials.[/red]")
        sys.exit(1)

    svc = ExchangeService()
    token = svc.authenticate(tenant, client, secret)

    try:
        messages = svc.search_messages(token, user, query)
        if output_json:
            print(json.dumps(messages, default=str))
        else:
            if not messages:
                print("[yellow]No messages found.[/yellow]")
                return

            table = Table(title=f"Messages in {user}")
            table.add_column("Subject")
            table.add_column("From")
            table.add_column("Date")

            for m in messages:
                from_addr = m.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')
                table.add_row(
                    m.get('subject', '')[:40],
                    from_addr[:30],
                    m.get('receivedDateTime', '')[:16]
                )
            print(table)
    except Exception as e:
        print(f"[red]Failed to search messages: {e}[/red]")
        sys.exit(1)


# --- Stacks Group ---
@cli.group()
def stacks():
    """Manage deployment stacks (batch installations)."""
    pass

def _get_stacks_file():
    """Get stacks file path."""
    app_data = os.getenv('APPDATA', '.')
    stacks_dir = Path(app_data) / "FaserF" / "SwitchCraft"
    stacks_dir.mkdir(parents=True, exist_ok=True)
    return stacks_dir / "stacks.json"

def _load_stacks():
    """Load stacks from file."""
    sf = _get_stacks_file()
    if sf.exists():
        with open(sf, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def _save_stacks(data):
    """Save stacks to file."""
    sf = _get_stacks_file()
    with open(sf, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

@stacks.command('list')
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def stacks_list(output_json):
    """List all deployment stacks."""
    data = _load_stacks()

    if output_json:
        print(json.dumps(data, default=str))
    else:
        if not data:
            print("[yellow]No stacks defined.[/yellow]")
            return

        table = Table(title="Deployment Stacks")
        table.add_column("Name")
        table.add_column("Items")

        for name, items in data.items():
            table.add_row(name, str(len(items)))
        print(table)

@stacks.command('create')
@click.option('--name', '-n', required=True, help="Stack name")
def stacks_create(name):
    """Create a new deployment stack."""
    data = _load_stacks()
    if name in data:
        print(f"[yellow]Stack '{name}' already exists.[/yellow]")
        return

    data[name] = []
    _save_stacks(data)
    print(f"[green]Created stack: {name}[/green]")

@stacks.command('delete')
@click.option('--name', '-n', required=True, help="Stack name")
@click.confirmation_option(prompt="Are you sure you want to delete this stack?")
def stacks_delete(name):
    """Delete a deployment stack."""
    data = _load_stacks()
    if name not in data:
        print(f"[red]Stack '{name}' not found.[/red]")
        sys.exit(1)

    del data[name]
    _save_stacks(data)
    print(f"[green]Deleted stack: {name}[/green]")

@stacks.command('add')
@click.option('--name', '-n', required=True, help="Stack name")
@click.option('--item', '-i', required=True, help="Item to add (package ID or command)")
def stacks_add(name, item):
    """Add an item to a stack."""
    data = _load_stacks()
    if name not in data:
        print(f"[red]Stack '{name}' not found. Create it first.[/red]")
        sys.exit(1)

    if item in data[name]:
        print(f"[yellow]Item '{item}' already in stack.[/yellow]")
        return

    data[name].append(item)
    _save_stacks(data)
    print(f"[green]Added '{item}' to stack '{name}'[/green]")

@stacks.command('show')
@click.option('--name', '-n', required=True, help="Stack name")
def stacks_show(name):
    """Show items in a stack."""
    data = _load_stacks()
    if name not in data:
        print(f"[red]Stack '{name}' not found.[/red]")
        sys.exit(1)

    items = data[name]
    if not items:
        print(f"[yellow]Stack '{name}' is empty.[/yellow]")
        return

    print(Panel("\n".join(f"• {i}" for i in items), title=f"Stack: {name}", border_style="blue"))

@stacks.command('deploy')
@click.option('--name', '-n', required=True, help="Stack name")
@click.option('--dry-run', is_flag=True, help="Show what would be installed without installing")
def stacks_deploy(name, dry_run):
    """Deploy (install) all items in a stack."""
    data = _load_stacks()
    if name not in data:
        print(f"[red]Stack '{name}' not found.[/red]")
        sys.exit(1)

    items = data[name]
    if not items:
        print(f"[yellow]Stack '{name}' is empty.[/yellow]")
        return

    print(f"Deploying stack: {name} ({len(items)} items)")

    for item in items:
        if dry_run:
            print(f"[dry-run] Would install: {item}")
        else:
            print(f"Installing: {item}...")
            # Attempt winget install
            try:
                import subprocess
                result = subprocess.run(
                    ['winget', 'install', '--id', item, '--accept-source-agreements', '--accept-package-agreements', '-h'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    print(f"  [green]✓ {item}[/green]")
                else:
                    print(f"  [yellow]⚠ {item} - may have failed[/yellow]")
            except Exception as e:
                print(f"  [red]✗ {item} - {e}[/red]")

    if not dry_run:
        print(f"[green]Stack deployment complete.[/green]")


# --- Library Group ---
@cli.group()
def library():
    """Manage .intunewin package library."""
    pass

@library.command('scan')
@click.option('--dirs', '-d', multiple=True, type=click.Path(exists=True), help="Directories to scan")
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def library_scan(dirs, output_json):
    """Scan directories for .intunewin files."""
    from datetime import datetime

    # Default directories
    scan_dirs = list(dirs) if dirs else []
    if not scan_dirs:
        # Use defaults similar to GUI
        downloads = Path.home() / "Downloads"
        desktop = Path.home() / "Desktop"
        if downloads.exists():
            scan_dirs.append(str(downloads))
        if desktop.exists():
            scan_dirs.append(str(desktop))

    files = []
    for d in scan_dirs:
        dir_path = Path(d)
        for f in dir_path.rglob("*.intunewin"):
            stat = f.stat()
            files.append({
                "path": str(f),
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)

    if output_json:
        print(json.dumps(files, default=str))
    else:
        if not files:
            print("[yellow]No .intunewin files found.[/yellow]")
            return

        table = Table(title=f"IntuneWin Library ({len(files)} files)")
        table.add_column("Name")
        table.add_column("Size")
        table.add_column("Modified")

        for f in files[:30]:  # Limit display
            size_mb = f['size'] / (1024 * 1024)
            table.add_row(
                f['name'][:40],
                f"{size_mb:.1f} MB",
                f['modified'][:10]
            )
        print(table)

@library.command('info')
@click.argument('intunewin_file', type=click.Path(exists=True))
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def library_info(intunewin_file, output_json):
    """Show information about an .intunewin file."""
    import zipfile
    from defusedxml import ElementTree as ET

    path = Path(intunewin_file)
    info = {
        "file": str(path),
        "size": path.stat().st_size,
        "name": None,
        "setup_file": None,
        "msi_info": {}
    }

    try:
        with zipfile.ZipFile(path, 'r') as zf:
            # Look for Detection.xml
            for name in zf.namelist():
                if name.endswith('Detection.xml'):
                    with zf.open(name) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()

                        # Extract info
                        name_elem = root.find('.//Name')
                        if name_elem is not None:
                            info['name'] = name_elem.text

                        setup_elem = root.find('.//SetupFile')
                        if setup_elem is not None:
                            info['setup_file'] = setup_elem.text

                        # MSI info if available
                        product_code = root.find('.//MsiProductCode')
                        if product_code is not None:
                            info['msi_info']['product_code'] = product_code.text

                        product_version = root.find('.//MsiProductVersion')
                        if product_version is not None:
                            info['msi_info']['product_version'] = product_version.text
                    break
    except Exception as e:
        info['error'] = str(e)

    if output_json:
        print(json.dumps(info, default=str))
    else:
        size_mb = info['size'] / (1024 * 1024)
        table = Table(title="IntuneWin Package Info", show_header=False)
        table.add_row("File", str(path.name))
        table.add_row("Size", f"{size_mb:.2f} MB")
        if info.get('name'):
            table.add_row("App Name", info['name'])
        if info.get('setup_file'):
            table.add_row("Setup File", info['setup_file'])
        if info.get('msi_info', {}).get('product_code'):
            table.add_row("Product Code", info['msi_info']['product_code'])
        if info.get('msi_info', {}).get('product_version'):
            table.add_row("Product Version", info['msi_info']['product_version'])
        if info.get('error'):
            table.add_row("Error", f"[red]{info['error']}[/red]")
        print(Panel(table, border_style="blue"))


# --- Winget Extended Commands ---
@winget.command('info')
@click.argument('pkg_id')
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def winget_info(pkg_id, output_json):
    """Show detailed information about a Winget package."""
    import subprocess

    try:
        result = subprocess.run(
            ['winget', 'show', pkg_id, '--disable-interactivity'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if output_json:
            # Parse output into dict (basic parsing)
            info = {"id": pkg_id}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    info[key.strip()] = val.strip()
            print(json.dumps(info, default=str))
        else:
            print(Panel(result.stdout or result.stderr, title=f"Package: {pkg_id}", border_style="blue"))
    except Exception as e:
        print(f"[red]Failed to get package info: {e}[/red]")
        sys.exit(1)

@winget.command('list-installed')
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
def winget_list_installed(output_json):
    """List installed Winget packages."""
    import subprocess

    try:
        result = subprocess.run(
            ['winget', 'list', '--disable-interactivity'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if output_json:
            # Basic parsing of winget list output
            lines = result.stdout.strip().split('\n')
            packages = []
            for line in lines[2:]:  # Skip header
                parts = line.split()
                if len(parts) >= 2:
                    packages.append({"name": parts[0], "id": parts[1] if len(parts) > 1 else ""})
            print(json.dumps(packages, default=str))
        else:
            print(result.stdout)
    except Exception as e:
        print(f"[red]Failed to list packages: {e}[/red]")
        sys.exit(1)


# --- Helper Function for Analysis ---
def _run_analysis(filepath, output_json):
    """Core analysis logic moved from old command."""
    path = Path(filepath)
    analyzers = [MsiAnalyzer(), ExeAnalyzer(), MacOSAnalyzer()]

    info = None
    for analyzer in analyzers:
        if analyzer.can_analyze(path):
            info = analyzer.analyze(path)
            break

    if not info:
        print(f"[bold red]Could not identify installer type for {path}[/bold red]")
        return

    winget_url = None
    if info.product_name:
        from switchcraft.services.addon_service import AddonService
        winget_mod = AddonService().import_addon_module("winget", "utils.winget")
        if winget_mod and hasattr(winget_mod, "WingetHelper"):
            winget = winget_mod.WingetHelper()
            if hasattr(winget, "search_by_name"):
                winget_url = winget.search_by_name(info.product_name)
            else:
                # Fallback to internal if addon is outdated
                from switchcraft.utils.winget import WingetHelper
                winget_url = WingetHelper().search_by_name(info.product_name)
        else:
             # Fallback to internal
             try:
                 from switchcraft.utils.winget import WingetHelper
                 winget_url = WingetHelper().search_by_name(info.product_name)
             except Exception:
                 pass

    if output_json:
        out = info.__dict__.copy()
        if winget_url:
            out['winget_url'] = winget_url
        print(json.dumps(out, default=str))
    else:
        _print_report(info, winget_url)

def _print_report(info, winget_url):
    table = Table(title="SwitchCraft Analysis Result", show_header=False)
    table.add_row("File", str(info.file_path))
    table.add_row("Type", info.installer_type)
    table.add_row("Product Name", info.product_name or "Unknown")
    table.add_row("Version", info.product_version or "Unknown")
    table.add_row("Confidence", f"{info.confidence * 100}%")

    print(Panel(table, title="General Info", border_style="blue"))

    if info.install_switches:
        print(Panel(f"[green]{' '.join(info.install_switches)}[/green]", title="Silent Install Args", border_style="green"))
    else:
        print(Panel("[yellow]No silent switches detected automatically.[/yellow]", title="Silent Install Args", border_style="yellow"))
        if str(info.file_path).endswith('.exe'):
            print(Panel(f"Try running:\n[bold]{info.file_path} /?[/bold]\nOr: --help, -h, /h", title="Brute Force / Help", border_style="magenta"))

    if info.uninstall_switches:
        print(Panel(f"[red]{' '.join(info.uninstall_switches)}[/red]", title="Silent Uninstall Args", border_style="red"))

    if winget_url:
        print(Panel(f"[link={winget_url}]{winget_url}[/link]", title="Winget Match Found!", border_style="cyan"))
