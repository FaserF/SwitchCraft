
import pytest
import importlib
import ast
from pathlib import Path

def get_hidden_imports_from_spec():
    """Parses switchcraft_modern.spec to extract the hidden_imports list."""
    spec_path = Path("switchcraft_modern.spec")
    if not spec_path.exists():
        pytest.fail("switchcraft_modern.spec not found")

    with open(spec_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    hidden_imports = []

    # Simple AST walker to find assignment to 'hidden_imports'
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'hidden_imports':
                    # Extract list elements
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant): # Python 3.8+
                                hidden_imports.append(elt.value)
                            elif isinstance(elt, ast.Str): # Python < 3.8
                                hidden_imports.append(elt.s)

    return hidden_imports

def test_hidden_imports_exist():
    """Verifies that all modules listed in hidden_imports can be found."""
    imports = get_hidden_imports_from_spec()
    assert imports, "No hidden_imports found in spec file"

    for module_name in imports:
        # Skip checking external libraries that might not be in the dev env
        # but ALWAYS check internal current project modules
        if not module_name.startswith("switchcraft"):
            continue

        try:
            # find_spec checks for existence without executing code
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                pytest.fail(f"Hidden import '{module_name}' not found (find_spec returned None)")
        except ModuleNotFoundError:
             pytest.fail(f"Hidden import '{module_name}' not found")
        except Exception as e:
            # Some other error (e.g. parent package import error)
            pytest.fail(f"Error checking '{module_name}': {e}")

if __name__ == "__main__":
    test_hidden_imports_exist()
