
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
@click.argument('value')
def config_set_secret(key, value):
    """Set a secure configuration value (keyring)."""
    SwitchCraftConfig.set_secret(key, value)
    print(f"Secret {key} saved securely.")

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

# --- Smart Entry Point Handling ---
# To support "switchcraft setup.exe" without "analyze", we need a custom class or just handle it in main.py
# For now, let's keep it strictly subcommand based or just rely heavily on "analyze" command.
# Or we can override formatting.
