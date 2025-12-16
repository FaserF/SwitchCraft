import click
import logging
from pathlib import Path
from rich import print
from rich.panel import Panel
from rich.table import Table

from switchcraft import __version__
from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.utils.winget import WingetHelper

logging.basicConfig(level=logging.ERROR)

@click.command()
@click.argument('filepath', type=click.Path(exists=True), required=False)
@click.option('--json', 'output_json', is_flag=True, help="Output in JSON format")
@click.version_option(__version__)
def cli(filepath, output_json):
    """SwitchCraft: Analyze installers for silent switches."""

    if not filepath:
        # Launch GUI if no file provided
        try:
            from switchcraft.gui.app import main as gui_main
            gui_main()
            return
        except ImportError as e:
            print(f"[bold red]GUI dependencies not found. Please install 'customtkinter' and 'tkinterdnd2'. Error: {e}[/bold red]")
            return

    path = Path(filepath)

    # Analyzers
    analyzers = [MsiAnalyzer(), ExeAnalyzer()]

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
