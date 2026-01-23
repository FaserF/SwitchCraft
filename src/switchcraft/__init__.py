__version__ = "2026.1.5.dev0+a6c7e67"

import sys
# --- WEB / PYODIDE PATCHES (run immediately on package import) ---
if sys.platform == "emscripten":
    import types
    if "ssl" not in sys.modules:
        ssl_mock = types.ModuleType("ssl")
        # Add minimal ssl module attributes that might be checked by urllib3
        ssl_mock.SSLContext = type("SSLContext", (), {"__init__": lambda *a, **kw: None})
        ssl_mock.PROTOCOL_TLS = 2
        ssl_mock.PROTOCOL_TLS_CLIENT = 16
        ssl_mock.create_default_context = lambda *a, **kw: None
        ssl_mock.HAS_SNI = True
        ssl_mock.CERT_NONE = 0
        ssl_mock.CERT_OPTIONAL = 1
        ssl_mock.CERT_REQUIRED = 2
        # Critical: urllib3 checks these version numbers
        ssl_mock.OPENSSL_VERSION_NUMBER = 0x101010CF  # Fake version >= 3.5.4
        ssl_mock.OPENSSL_VERSION = "OpenSSL 3.5.4 (Pyodide Mock)"
        ssl_mock.OPENSSL_VERSION_INFO = (1, 1, 1, 15, 15)
        ssl_mock.HAS_NEVER_CHECK_COMMON_NAME = True
        sys.modules["ssl"] = ssl_mock

    try:
        # Patch requests/urllib3 to use browser fetch
        import pyodide_http
        pyodide_http.patch_all()
    except ImportError:
        pass
