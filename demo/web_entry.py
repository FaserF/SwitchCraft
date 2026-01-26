import os
import sys

print("DEBUG: WEB ENTRY RELOADED")
print(f"BUILD_TIME: Mon Jan 26 09:41:55 UTC 2026")

# ============================================================
# CRITICAL: Patch ssl module BEFORE any urllib3 import
# Pyodide injects a MagicMock for ssl, breaking urllib3's version check
# ============================================================
if sys.platform == "emscripten":
    import types

    # Force patch if 'ssl' is a MagicMock or missing version info
    should_patch_ssl = "ssl" not in sys.modules
    if not should_patch_ssl:
        ssl_mod = sys.modules["ssl"]
        # Check if it's a MagicMock
        if "Mock" in str(type(ssl_mod)) or not hasattr(ssl_mod, "OPENSSL_VERSION_INFO"):
            should_patch_ssl = True
        else:
            try:
                if not isinstance(ssl_mod.OPENSSL_VERSION_INFO, tuple):
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
        ssl_mock.OPENSSL_VERSION = "OpenSSL 1.1.1 (Pyodide Mock)"
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
    # GLOBAL THREADING MONKEYPATCH FOR WASM
    # ============================================================
    import threading
    import asyncio

    class WASMThread(threading.Thread):
        """Bridge between standard threading and WASM-friendly asyncio tasks."""
        def start(self):
            async def _bridge():
                try:
                    self.run()
                except Exception as e:
                    print(f"ERROR in WASM background thread '{self.name}': {e}")

            try:
                asyncio.create_task(_bridge())
            except RuntimeError:
                self.run()

    threading.Thread = WASMThread
    print("DEBUG: Global threading monkeypatch applied")

# ============================================================
# Normal imports AFTER ssl patching
# ============================================================
import flet as ft
# Ensure current dir is in path
sys.path.insert(0, os.getcwd())
import switchcraft
switchcraft.IS_DEMO = True
import switchcraft.main

if __name__ == "__main__":
    # Use ft.run for modern Flet (0.80.0+)
    ft.run(switchcraft.main.main, assets_dir="assets")
