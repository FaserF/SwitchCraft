__version__ = "2026.1.5.dev0+7278de8"

import sys
# --- WEB / PYODIDE PATCHES (run immediately on package import) ---
if sys.platform == "emscripten":
    try:
        # Patch requests/urllib3 to use browser fetch
        import pyodide_http
        pyodide_http.patch_all()
    except ImportError:
        pass

    # Mock SSL to prevent import errors in libraries (like urllib3) that expect it
    import types
    if "ssl" not in sys.modules:
        sys.modules["ssl"] = types.ModuleType("ssl")
