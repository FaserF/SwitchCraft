from click.testing import CliRunner
import click
from switchcraft.cli.commands import cli

def get_all_commands(cli_obj, ctx):
    """Recursively yield all command paths and command objects."""
    yield [], cli_obj
    if isinstance(cli_obj, click.Group):
        for name, cmd in cli_obj.commands.items():
            for sub_path, sub_cmd in get_all_commands(cmd, ctx):
                yield [name] + sub_path, sub_cmd

def test_dynamic_cli_help():
    """
    Dynamically discover all CLI commands and verify they run with --help.
    This ensures that:
    1. Every command can be imported and loaded.
    2. No syntax errors in command definitions.
    3. Dependencies for every command are available (or optional).
    """
    runner = CliRunner()

    # Create a context to introspect
    with click.Context(cli) as ctx:
        # If the main cli is a simple command, list_commands might not exist or be relevant
        # SwitchCraft currently uses a single command @click.command, but if it evolves to @click.group:

        if isinstance(cli, click.Group):
            commands = list(get_all_commands(cli, ctx))
        else:
            # Single command structure
            commands = [([], cli)]

        assert len(commands) > 0, "No commands found to test!"

        for path_parts, cmd in commands:
            # Construct arg list
            args = path_parts + ['--help']
            print(f"Testing command: switchcraft {' '.join(args)}")

            result = runner.invoke(cli, args)

            assert result.exit_code == 0, f"Command {' '.join(path_parts)} failed with --help"
            assert "Usage:" in result.output
            assert "Options:" in result.output

def test_cli_json_flag():
    """Verify the --json flag on the main entry point."""
    runner = CliRunner()
    # We pass no arguments, which should trigger help or specific behavior
    # But here we want to test if --json flag is accepted even without file (might fail validation but check it exists)

    # Actually, main cli requires filepath argument?
    # Let's check commands.py: @click.argument('filepath', required=False)

    result = runner.invoke(cli, ['--json'])
    assert result.exit_code == 0
    # Expected: empty JSON output with maybe default values or handled gracefully
    # Based on commands.py: if not filepath: click.echo(ctx.get_help()) -> output_json not reached.
    # Wait, commands.py logic:
    # if not filepath: click.echo(ctx.get_help())

    # So --json without file just shows help.
    assert "Usage:" in result.output
