---
description: Deploy SwitchCraft Web (Flet WASM) to production
---

# Web Deployment Workflow

This workflow publishes SwitchCraft as a Flet Web App (Pyodide/WASM) and fixes the SSL mock issue.

## Prerequisites
- Flet installed (`pip install flet`)
- `build_web/web_entry.py` contains the SSL patch

## Steps

// turbo
1. Navigate to project root:
```powershell
cd c:\Users\fseitz\GitHub\SwitchCraft
```

2. Run Flet Publish:
```powershell
flet publish src/switchcraft/main.py --web-output-dir docs/public/demo --module-name switchcraft.main
```

// turbo
3. Patch web_entry.py with SSL fix (CRITICAL - fixes Pyodide urllib3 crash):
```powershell
Copy-Item build_web/web_entry.py docs/public/demo/web_entry.py -Force
```

// turbo
4. Verify the patch was applied:
```powershell
Select-String "SSL module patched" docs/public/demo/web_entry.py
```

5. Deploy the `docs/public/demo` folder to your web server.

## Verification
After deployment, open the browser console. You should see:
```
DEBUG: WEB ENTRY RELOADED (Version 2026.1.6-FIXED-V3)
DEBUG: SSL module patched successfully
DEBUG: pyodide_http patched successfully
```

If you still see the `MagicMock` error, the old `web_entry.py` is cached - hard refresh with `Ctrl+Shift+R`.
