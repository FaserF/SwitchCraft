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
        shutil.rmtree(docs_public_dir)

    os.makedirs(build_dir, exist_ok=True)

    print("Copying source files to build_web (gitignored)...")
    src_switchcraft = os.path.join(root_dir, "src", "switchcraft")
    shutil.copytree(src_switchcraft, os.path.join(build_dir, "switchcraft"))

    print("Creating web_entry.py...")
    # This simulates the CI generation step
    import sys
import os

# Notes:
# SSL and Request patching is now handled in switchcraft/__init__.py
# to ensure it runs within the package context and works reliably.

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

    print("Creating requirements.txt...")
    req_content = """flet
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
        # Locate flet.exe
        flet_exe = None

        # 1. PATH
        if shutil.which("flet"):
            flet_exe = "flet"

        # 2. Sys Executable Scripts
        if not flet_exe:
            scripts_dir = os.path.join(os.path.dirname(sys.executable), "Scripts")
            candidate = os.path.join(scripts_dir, "flet.exe")
            if os.path.exists(candidate):
                flet_exe = candidate

        # 3. User Base Scripts
        if not flet_exe:
            try:
                user_base = site.getuserbase()
                # Typical location: AppData/Roaming/Python/Python313/Scripts/flet.exe
                # We need to find the correct python version component if generic
                # But usually it mirrors the python version.
                # Hardcoded check based on investigation
                candidate = os.path.join(user_base, "Python313", "Scripts", "flet.exe")
                if os.path.exists(candidate):
                    flet_exe = candidate
                else:
                    # General User Scripts check
                    candidate = os.path.join(user_base, "Scripts", "flet.exe") # Linux/Mac maybe
                    if os.path.exists(candidate):
                        flet_exe = candidate
                    else:
                        # Windows specific user scripts path which might be different depends on install
                        # We saw: c:\Users\fseitz\AppData\Roaming\Python\Python313\Scripts\flet.exe
                        # Let's try to construct it dynamically
                        candidate = os.path.join(user_base, f"Python{sys.version_info.major}{sys.version_info.minor}", "Scripts", "flet.exe")
                        if os.path.exists(candidate):
                             flet_exe = candidate
            except:
                pass

        # 4. Fallback to hardcoded known path from investigation
        if not flet_exe:
             candidate = r"c:\Users\fseitz\AppData\Roaming\Python\Python313\Scripts\flet.exe"
             if os.path.exists(candidate):
                 flet_exe = candidate

        if not flet_exe:
             # Last resort: python -m flet
             print("Could not find flet executable. Trying python -m flet...")
             subprocess.check_call([sys.executable, "-m", "flet", "publish", "web_entry.py", "--app-name", "SwitchCraft", "--app-short-name", "SwitchCraft Demo", "--app-description", "SwitchCraft Web Demo", "--base-url", "/demo/", "--distpath", "../dist", "--assets", "switchcraft/assets"])
        else:
            print(f"Using flet executable: {flet_exe}")
            subprocess.check_call([flet_exe, "publish", "web_entry.py", "--app-name", "SwitchCraft", "--app-short-name", "SwitchCraft Demo", "--app-description", "SwitchCraft Web Demo", "--base-url", "/demo/", "--distpath", "../dist", "--assets", "switchcraft/assets"])

    except subprocess.CalledProcessError as e:
        print(f"Error running flet publish: {e}")
        sys.exit(1)
    finally:
        os.chdir(original_cwd)

    print("Moving artifacts to docs/public/demo...")
    if os.path.exists(dist_dir):
        # We need to copy contents of dist to docs/public/demo
        shutil.copytree(dist_dir, docs_public_dir)
        print("Cleaning up dist...")
        shutil.rmtree(dist_dir)

        # Cleanup build_web directory to avoid file duplication in user's workspace
        # if os.path.exists(build_dir):
        #     print(f"Cleaning up temporary build directory: {build_dir}")
        #     shutil.rmtree(build_dir, ignore_errors=True)

        print(f"Build complete. Served at {docs_public_dir}")
        print("To test, run python -m http.server --directory docs/public")
    else:
        print("Error: dist directory was not created.")
        sys.exit(1)

if __name__ == "__main__":
    build_web_demo()
