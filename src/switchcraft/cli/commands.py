
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
from switchcraft.utils.winget import WingetHelper
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

def setup_logging():
    """Setup structured logging format based on debug mode setting."""
    debug_enabled = SwitchCraftConfig.is_debug_mode()

    if debug_enabled:
        # Structured debug logging format for easy parsing
        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        if not os.environ.get("SWITCHCRAFT_SUPPRESS_HEADER"):
            logging.info("=" * 60)
            logging.info(f"SwitchCraft v{__version__} - Debug Log")
            logging.info("=" * 60)
            logging.info(f"Python: {sys.version}")
            logging.info(f"Platform: {sys.platform}")
    else:
        logging.basicConfig(level=logging.ERROR)

@click.command()
@click.argument('filepath', type=click.Path(exists=True), required=False)
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
@click.version_option(__version__, message='SwitchCraft, version %(version)s')
@click.pass_context
def cli(ctx, filepath, output_json):
    """SwitchCraft: Analyze installers for silent switches."""
    setup_logging()

    if not filepath:
        # In CLI-only mode, or if passed via wrapper with args, no file = help
        # The main.py wrapper handles the GUI launch generic case.
        click.echo(ctx.get_help())
        return

    path = Path(filepath)

    # Analyzers
    analyzers = [MsiAnalyzer(), ExeAnalyzer(), MacOSAnalyzer()]

    info = None
    for analyzer in analyzers:
        if analyzer.can_analyze(path):
            info = analyzer.analyze(path)
            break

    if not info:
        print(f"[bold red]Could not identify installer type for {path}[/bold red]")
        return

    # Winget check
    winget = WingetHelper()
    winget_url = None
    if info.product_name:
        winget_url = winget.search_by_name(info.product_name)

    # Output
    if output_json:
        out = info.__dict__.copy()
        if winget_url:
            out['winget_url'] = winget_url
        print(json.dumps(out, default=str))
    else:
        print_report(info, winget_url)

def print_report(info, winget_url):
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
        # Brute Force Suggestion
        if str(info.file_path).endswith('.exe'):
            print(Panel(f"Try running:\n[bold]{info.file_path} /?[/bold]\nOr: --help, -h, /h", title="Brute Force / Help", border_style="magenta"))

    if info.uninstall_switches:
        print(Panel(f"[red]{' '.join(info.uninstall_switches)}[/red]", title="Silent Uninstall Args", border_style="red"))

    if winget_url:
        print(Panel(f"[link={winget_url}]{winget_url}[/link]", title="Winget Match Found!", border_style="cyan"))
