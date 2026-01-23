import os
import sys

print("DEBUG: WEB ENTRY RELOADED (Version 2026.1.6-FIXED-V3)")

# ============================================================
# CRITICAL: Patch ssl module BEFORE any urllib3 import
# Pyodide injects a MagicMock for ssl, breaking urllib3's version check
# ============================================================
if sys.platform == "emscripten":
    import types
    should_patch_ssl = "ssl" not in sys.modules
    if not should_patch_ssl:
        try:
            if not isinstance(sys.modules["ssl"].OPENSSL_VERSION_INFO, tuple):
                should_patch_ssl = True
        except (AttributeError, TypeError):
            should_patch_ssl = True

    if should_patch_ssl:
        ssl_mock = types.ModuleType("ssl")
        ssl_mock.SSLContext = type("SSLContext", (), {"__init__": lambda *a, **kw: None})
        ssl_mock.PROTOCOL_TLS = 2
        ssl_mock.PROTOCOL_TLS_CLIENT = 16
        ssl_mock.create_default_context = lambda *a, **kw: None
        ssl_mock.HAS_SNI = True
        ssl_mock.CERT_NONE = 0
        ssl_mock.CERT_OPTIONAL = 1
        ssl_mock.CERT_REQUIRED = 2
        ssl_mock.OPENSSL_VERSION_NUMBER = 0x101010CF
        ssl_mock.OPENSSL_VERSION = "OpenSSL 3.5.4 (Pyodide Mock)"
        ssl_mock.OPENSSL_VERSION_INFO = (1, 1, 1, 15, 15)
        ssl_mock.HAS_NEVER_CHECK_COMMON_NAME = True
        sys.modules["ssl"] = ssl_mock
        print("DEBUG: SSL module patched successfully")

    # Now safe to patch pyodide_http
    try:
        import pyodide_http
        pyodide_http.patch_all()
        print("DEBUG: pyodide_http patched successfully")
    except ImportError:
        pass

# ============================================================
# Normal imports AFTER ssl patching
# ============================================================
import flet as ft
sys.path.insert(0, os.getcwd())
import switchcraft.main

if __name__ == "__main__":
    ft.app(target=switchcraft.main.main, assets_dir="switchcraft/assets")
