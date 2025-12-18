import click
import logging
import sys
import os
from pathlib import Path

# Ensure 'src' is in sys.path to prioritize local source over installed package
# This prevents "Shadowing" issues where an old installed version is imported instead of the local code.
if __name__ == "__main__":
    # If running as script, add project root (src) to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich import print
from rich.panel import Panel
from rich.table import Table

from switchcraft import __version__
from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.analyzers.macos import MacOSAnalyzer
from switchcraft.utils.winget import WingetHelper
from switchcraft.utils.config import SwitchCraftConfig

# PyInstaller Static Analysis Hint
if False:
    import switchcraft.gui.app




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
        logging.info("=" * 60)
        logging.info(f"SwitchCraft v{__version__} - Debug Log")
        logging.info("=" * 60)
        logging.info(f"Python: {sys.version}")
        logging.info(f"Platform: {sys.platform}")
        logging.info(f"Executable: {sys.executable}")
        logging.info(f"Debug enabled via: {SwitchCraftConfig.is_debug_mode()}")
        logging.info("=" * 60)
    else:
        logging.basicConfig(level=logging.ERROR)

setup_logging()
logger = logging.getLogger(__name__)

@click.command()
@click.argument('filepath', type=click.Path(exists=True), required=False)
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
@click.version_option(__version__, message='SwitchCraft, version %(version)s')
def cli(filepath, output_json):
    """SwitchCraft: Analyze installers for silent switches."""

    if not filepath:
        # Launch GUI if no file provided
        try:
            from switchcraft.gui.app import main as gui_main
            gui_main()
            return
        except ImportError as e:
            print(f"[bold red]GUI dependencies not found or failed to load.[/bold red]")
            print(f"[red]Detailed Error: {e}[/red]")
            # Diagnositc info
            print(f"Sys Path: {sys.path}")

            # List contents of switchcraft package if possible
            try:
                import switchcraft
                print(f"SwitchCraft Module: {switchcraft}")
                if hasattr(switchcraft, '__path__'):
                    print(f"SwitchCraft Path: {switchcraft.__path__}")
                    # Recursively walk to see ALL files
                    for p in switchcraft.__path__:
                        for root, dirs, files in os.walk(p):
                            print(f"Content of {root}: {files}")

                        # Read the init file if it exists
                        init_file = os.path.join(p, '__init__.py')
                        if os.path.exists(init_file):
                            print(f"--- CONTENT OF {init_file} ---")
                            try:
                                with open(init_file, 'r') as f:
                                    print(f.read())
                            except:
                                print("Could not read file.")
                            print("--- END CONTENT ---")
            except Exception as ex:
                print(f"Could not list package contents: {ex}")

            import traceback
            traceback.print_exc()
            input("\nPress Enter to close...")
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
        import json as json_lib
        out = info.__dict__.copy()
        if winget_url:
            out['winget_url'] = winget_url
        print(json_lib.dumps(out, default=str))
    else:
        print_report(info, winget_url)

def print_report(info, winget_url):
    table = Table(title="SwitchCraft Analysis Result", show_header=False)
    table.add_row("File", info.file_path)
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
        if info.file_path.endswith('.exe'):
            print(Panel(f"Try running:\n[bold]{info.file_path} /?[/bold]\nOr: --help, -h, /h", title="Brute Force / Help", border_style="magenta"))

    if info.uninstall_switches:
        print(Panel(f"[red]{' '.join(info.uninstall_switches)}[/red]", title="Silent Uninstall Args", border_style="red"))

    if winget_url:
        print(Panel(f"[link={winget_url}]{winget_url}[/link]", title="Winget Match Found!", border_style="cyan"))

if __name__ == "__main__":
    cli()
