import os
import shutil
import subprocess
import sys
import site

def build_web_demo():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Use a temporary build directory that is ignored
    build_dir = os.path.join(root_dir, "build_web")
    dist_dir = os.path.join(root_dir, "dist")
    docs_public_dir = os.path.join(root_dir, "docs", "public", "demo")

    print(f"Root dir: {root_dir}")
    print("Cleaning up previous builds...")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    if os.path.exists(docs_public_dir):
        # Clean build target
        print(f"Cleaning existing demo dir: {docs_public_dir}")
        shutil.rmtree(docs_public_dir)

    os.makedirs(build_dir, exist_ok=True)

    print("Copying source files to build_web (gitignored)...")
    src_switchcraft = os.path.join(root_dir, "src", "switchcraft")
    shutil.copytree(src_switchcraft, os.path.join(build_dir, "switchcraft"))

    print("Creating web_entry.py...")
    # This simulates the CI generation step
    web_entry_content = """import os
import sys

print("DEBUG: WEB ENTRY RELOADED (Version 2026.1.6-FIXED-V2)")

# SSL and Request patching is handled in switchcraft/__init__.py

import flet as ft
# Ensure current dir is in path
sys.path.insert(0, os.getcwd())
import switchcraft.main

if __name__ == "__main__":
    # Use ft.app for web (flet publish) - this is the standard entry point
    # assets_dir needs to match where assets are relative to URL root or how they are served
    # switchcraft/assets should be correct relative to the published root
    ft.app(target=switchcraft.main.main, assets_dir="switchcraft/assets")
"""
    with open(os.path.join(build_dir, "web_entry.py"), "w") as f:
        f.write(web_entry_content)

    # Splash Generation
    print("Generating Splash Screen...")
    try:
        # Get Version
        import src.switchcraft as s
        version = s.__version__
        print(f"Detected version: {version}")

        # Run script
        subprocess.check_call([
            sys.executable,
            os.path.join(root_dir, "scripts", "generate_splash.py"),
            "--version", version,
            "--output", os.path.join(build_dir, "switchcraft", "assets", "splash.png")
        ])
    except Exception as e:
        print(f"Splash generation failed: {e}")

    print("Creating requirements.txt...")
    req_content = """flet==0.80.3
pyodide-http
pefile
olefile
requests
click
rich
PyYAML
defusedxml
PyJWT
anyio>=4.12.1
"""
    with open(os.path.join(build_dir, "requirements.txt"), "w") as f:
        f.write(req_content)

    print("Running flet publish...")
    original_cwd = os.getcwd()
    os.chdir(build_dir)
    try:
        # Locate flet.exe logic (simplified for local run)
        cmd = [sys.executable, "-m", "flet", "publish", "web_entry.py"]

        # PWA Arguments
        pwa_args = [
            "--app-name", "SwitchCraft Demo", # Display Name
            "--app-short-name", "SwitchCraft", # Home Screen Name
            "--app-description", "SwitchCraft Web Demo",
            "--base-url", "/demo/",
            "--distpath", "../dist",
            "--assets", "switchcraft/assets"
        ]

        subprocess.check_call(cmd + pwa_args)

    except subprocess.CalledProcessError as e:
        print(f"Error running flet publish: {e}")
        # sys.exit(1) # Continue to copy check
    finally:
        os.chdir(original_cwd)

    print("Moving artifacts to docs/public/demo...")
    if os.path.exists(dist_dir):

        # Icon Overwrite (Local simulation of CI 'cp' commands)
        print("Overwriting PWA Icons...")
        assets_dir = os.path.join(root_dir, "src", "switchcraft", "assets")
        dist_icons = os.path.join(dist_dir, "icons")

        shutil.copy(os.path.join(assets_dir, "icon-192.png"), os.path.join(dist_icons, "icon-192.png"))
        shutil.copy(os.path.join(assets_dir, "icon-512.png"), os.path.join(dist_icons, "icon-512.png"))
        shutil.copy(os.path.join(assets_dir, "favicon.png"), os.path.join(dist_dir, "favicon.png"))
        try:
             shutil.copy(os.path.join(assets_dir, "apple-touch-icon.png"), os.path.join(dist_dir, "apple-touch-icon.png"))
        except: pass

        # We need to copy contents of dist to docs/public/demo
        shutil.copytree(dist_dir, docs_public_dir)
        print("Cleaning up dist...")
        shutil.rmtree(dist_dir)

        print(f"Build complete. Served at {docs_public_dir}")
        print("To test, verify docs/public/demo/web_entry.py (if visible) or check console log.")
    else:
        print("Error: dist directory was not created.")
        sys.exit(1)

if __name__ == "__main__":
    build_web_demo()
