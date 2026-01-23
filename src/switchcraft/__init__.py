__version__ = "2026.1.5.dev0+31ac967"

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
        ssl_mock = types.ModuleType("ssl")
        # Add minimal ssl module attributes that might be checked
        ssl_mock.SSLContext = type("SSLContext", (), {"__init__": lambda *a, **kw: None})
        ssl_mock.PROTOCOL_TLS = 2
        ssl_mock.PROTOCOL_TLS_CLIENT = 16
        ssl_mock.create_default_context = lambda *a, **kw: None
        ssl_mock.HAS_SNI = True
        ssl_mock.CERT_NONE = 0
        ssl_mock.CERT_OPTIONAL = 1
        ssl_mock.CERT_REQUIRED = 2
        sys.modules["ssl"] = ssl_mock

    # Note: In Flet 0.70+, ft.run() is the correct method (ft.app is deprecated)
    # No patching needed for ft.run - web_entry.py should call it correctly.
    # The SSL mock above is still needed.
