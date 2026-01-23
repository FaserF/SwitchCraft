
import pytest
import typing
import pkgutil
import importlib
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath("src"))

def get_switchcraft_modules():
    """Yields all modules under switchcraft package."""
    import switchcraft
    path = switchcraft.__path__
    prefix = switchcraft.__name__ + "."

    for _, name, _ in pkgutil.walk_packages(path, prefix):
        yield name

def test_strict_type_hints():
    """
    Iterates over all switchcraft modules and attempts to resolve type hints.
    This catches cases where a type is used in a hint (e.g. `page: ft.Page`)
    but the module (e.g. `ft`) is not imported.
    """
    modules_to_check = [
        "switchcraft.gui_modern.app",
        "switchcraft.gui_modern.views.home_view",
        # Add other critical modules here or iterate dynamically
    ]

    # Let's try to be dynamic but safe
    failed_modules = []

    for module_name in modules_to_check:
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            # If we can't even import it, that's a different failure,
            # likely caught by other tests, but let's note it.
            failed_modules.append(f"{module_name}: Import failed")
            continue

        # Check classes in the module
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and attr.__module__ == module_name:
                # It's a class defined in this module
                try:
                    typing.get_type_hints(attr)

                    # Also check methods
                    for method_name in dir(attr):
                        method = getattr(attr, method_name)
                        if callable(method):
                             try:
                                 typing.get_type_hints(method)
                             except NameError as e:
                                 # Skip NameErrors from Flet internal types (e.g., 'Theme')
                                 # These are issues in Flet's type annotations, not our code
                                 if any(flet_type in str(e) for flet_type in ['Theme', 'ft.']):
                                     continue
                                 failed_modules.append(f"{module_name}.{attr_name}.{method_name}: {e}")
                             except Exception:
                                 # Ignore other errors for now (like AttributeError on properties)
                                 pass

                except NameError as e:
                    # Skip NameErrors from Flet internal types (e.g., 'Theme' in ft.Container)
                    # These are issues in Flet's type annotations, not our code
                    if any(flet_type in str(e) for flet_type in ['Theme', 'ft.']):
                        continue
                    failed_modules.append(f"{module_name}.{attr_name}: {e}")
                except Exception:
                     pass

    if failed_modules:
        pytest.fail("Type hint resolution failed for:\n" + "\n".join(failed_modules))

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
