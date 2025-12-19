
import sys
from pathlib import Path

# Ensure 'src' is in sys.path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    """
    CLI-Only entry point.
    Strictly avoids importing any GUI modules.
    """
    try:
        from switchcraft.cli.commands import cli
        cli()
    except Exception as e:
        print(f"Critical Error in CLI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
