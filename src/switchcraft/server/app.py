import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer
import httpx
import tempfile
import shutil

import flet as ft
import pyotp

from switchcraft.main import main as flet_main
from switchcraft.server.auth_config import AuthConfigManager
from switchcraft.server.user_manager import UserManager
import switchcraft
from switchcraft.server.update_checker import check_for_updates

# Configuration
auth_manager = AuthConfigManager()
# We also instantiate UserManager
user_manager = UserManager(auth_manager.config_dir)

config = auth_manager.load_config()
SECRET_KEY = auth_manager.get_secret_key()
serializer = URLSafeTimedSerializer(SECRET_KEY)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SwitchCraftServer")

ASSETS_DIR = Path(__file__).parent.parent / "assets"

def _ensure_pwa_manifest():
    """
    Ensure a PWA manifest.json exists in the assets directory with the correct version.
    This enables PWA installation for the self-hosted Docker version.
    """
    import json
    from pathlib import Path
    try:
        import switchcraft
        version = switchcraft.__version__
    except Exception:
        version = "Unknown"

    # Resolve assets dir correctly relative to this file
    assets_dir = Path(__file__).parent.parent / "assets"
    manifest_path = assets_dir / "manifest.json"

    # Define PWA Manifest content
    manifest_data = {
        "name": "SwitchCraft",
        "short_name": "SwitchCraft",
        "id": "/",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#202020",
        "theme_color": "#202020",
        "description": f"SwitchCraft Modern Software Management (v{version})",
        "icons": [
            {
                "src": "icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            },
            {
                "src": "switchcraft_logo.png",
                "sizes": "any",
                "type": "image/png"
            },
            {
                "src": "apple-touch-icon.png",
                "sizes": "180x180",
                "type": "image/png"
            }
        ]
    }

    try:
        if not assets_dir.exists():
            assets_dir.mkdir(parents=True, exist_ok=True)

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        logger.info(f"PWA Manifest successfully ensured at {manifest_path}")
    except Exception as e:
        logger.error(f"Failed to write manifest.json: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SwitchCraft Server...")
    conf = auth_manager.load_config()

    # Feature Flags
    if conf.get("demo_mode"):
        logger.info("Applying DEMO MODE globally.")
        switchcraft.IS_DEMO = True

    # Ensure PWA Manifest is current and correct
    try:
        _ensure_pwa_manifest()
    except Exception as e:
        logger.warning(f"Failed to generate PWA manifest: {e}")

    yield
    logger.info("Shutting down SwitchCraft Server...")

app = FastAPI(lifespan=lifespan)

# Asset redirection to fix Flet engine looking in /assets/ for its own files
@app.get("/assets/{path:path}")
async def catch_all_assets(path: str):
    # Try local user assets first
    local_file = ASSETS_DIR / path
    if local_file.exists() and local_file.is_file():
        return FileResponse(local_file)

    # If not found in user assets, it might be an internal Flet engine file
    # (like FontManifest.json, main.dart.js, etc.) which are at root or in root/assets
    # Instead of redirecting (which triggers auth middleware again),
    # we return a 404 or let the main flet app handle it.
    # However, Flet's engine often expects these at /assets/ but Flet serves them at /.
    # To avoid 307 redirects and potential auth loops, we'll try to find them.
    # For now, let's stick to the 307 redirect but ensure the whitelist handles it.
    return RedirectResponse(url=f"/{path}")

# Still mount /assets for StaticFiles as a backup, but the route above takes precedence for 404 handling
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# --- Auth Helpers ---
def get_current_user(request: Request):
    """Retrieve user from session cookie."""
    token = request.cookies.get("sc_session")
    if not token:
        conf = auth_manager.load_config()
        if conf.get("auth_disabled", False):
            return "admin" # Auto-login as admin
        return None

    try:
        data = serializer.loads(token, max_age=86400)
        return data.get("username")
    except Exception:
        return None

def login_required(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})

    # Check for enforced MFA (skip if already on setup page or logout)
    if not request.url.path.startswith("/mfa/setup") and not request.url.path.startswith("/logout"):
        conf = auth_manager.load_config()
        if conf.get("enforce_mfa"):
             # If user is admin and using global MFA, skip?
             # No, if enforce_mfa is on, everyone needs a PERSONAL secret.
             if not user_manager.get_totp_secret(user):
                 logger.info(f"Redirecting user '{user}' to MFA setup (enforced)")
                 raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/mfa/setup"})

    return user

def admin_required(request: Request):
    user_name = login_required(request)
    u_info = user_manager.get_user(user_name)
    if not u_info or u_info.get("role") != "admin":
         # Allow fallback if using auth_disabled (which implies admin rights for simplicity)
         conf = auth_manager.load_config()
         if conf.get("auth_disabled"): return "admin"

         raise HTTPException(status_code=403, detail="Admin privileges required")
    return user_name

# --- HTML Templates (Partial) ---

# Shared Footer Template
FOOTER_TEMPLATE = """
<footer style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #333; text-align: center; font-size: 0.85em; color: #888;">
    <p>SwitchCraft v{version}</p>
    <p>
        <a href="https://github.com/FaserF/SwitchCraft" target="_blank" style="color: #0066cc; text-decoration: none;">GitHub</a>
        {admin_link}
    </p>
    <p style="color: #666;">© 2026 FaserF - Intune Packaging & Management Platform</p>
</footer>
"""

MFA_SETUP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SwitchCraft - MFA Setup</title>
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; background-color: #111315; color: white; margin: 0; padding: 20px; box-sizing: border-box; }}
        .card {{ background: #1e2124; padding: 2.5rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 320px; text-align: center; }}
        .secret {{ background: #222; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 1.2rem; cursor: pointer; border: 1px solid #333; display: block; width: 100%; box-sizing: border-box; margin: 15px 0; }}
        input {{ width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #333; background: #2b2f33; color: white; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: #00aa44; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 1rem; margin-top: 10px; }}
        button:hover {{ background: #008833; }}
        .instructions {{ text-align: left; font-size: 0.9em; color: #aaa; margin-bottom: 15px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🔒 MFA Setup</h2>
        <p class="instructions">Scan the secret below with your Authenticator app (Google, Microsoft, Authy, etc.):</p>

        <code class="secret">{secret}</code>

        <p class="instructions">Then enter the 6-digit code to verify:</p>

        <form action="/mfa/setup" method="post">
            <input type="hidden" name="secret" value="{secret}">
            <input type="text" name="code" placeholder="6-digit code" required pattern="[0-9]{6}" autocomplete="off" autofocus>
            <button type="submit">Verify & Save</button>
        </form>

        {error_msg}
    </div>
</body>
</html>
"""


# --- I18n Dictionaries ---
TRANSLATIONS = {
    "en": {
        "title": "SwitchCraft Web",
        "desc": "Intune Packaging & Management Platform<br>Simplify your Windows app deployment workflow.",
        "username": "Username",
        "password": "Password",
        "login": "Log In",
        "footer_rights": "© 2026 FaserF",
        "admin_panel": "Admin Panel",
        "sso_ms": "Log in with Microsoft",
        "sso_gh": "Log in with GitHub",
        "not_configured": "Not Configured",
        "default_creds_warning": "⚠️ Security Notice: Default credentials active (admin/admin). Change immediately!",
        "settings_saved": "Global settings saved.",
        "admin_title": "Server Administration",
        "back_to_app": "Back to App",
        "logout": "Logout",
        "change_password": "Change Admin Password",
        "curr_pw": "Current Password",
        "new_pw": "New Password",
        "confirm_pw": "Confirm Password",
        "user_mgmt": "User Management",
        "add_user": "Add User",
        "role": "Role",
        "active": "Active",
        "actions": "Actions",
        "global_settings": "Global Settings",
        "enable_demo": "Enable Demo Mode",
        "disable_auth": "Disable Auth (Auto-Login)",
        "allow_sso": "Allow SSO Registration (Auto-Provision)",
        "enforce_mfa": "Enforce MFA for All Users",
        "save_settings": "Save Settings",
        "sso_config": "SSO Configuration",
        "backup_reset": "Backup & Reset",
        "exp_backup": "Export Backup",
        "fac_reset": "Factory Reset",
    },
    "de": {
        "title": "SwitchCraft Web",
        "desc": "Intune Packaging & Management Plattform<br>Vereinfachen Sie Ihren Windows-App-Deployment-Workflow.",
        "username": "Benutzername",
        "password": "Passwort",
        "login": "Anmelden",
        "footer_rights": "© 2026 FaserF",
        "admin_panel": "Admin-Bereich",
        "sso_ms": "Mit Microsoft anmelden",
        "sso_gh": "Mit GitHub anmelden",
        "not_configured": "Nicht konfiguriert",
        "default_creds_warning": "⚠️ Sicherheitshinweis: Standard-Zugangsdaten aktiv (admin/admin). Bitte sofort ändern!",
        "settings_saved": "Einstellungen gespeichert.",
        "admin_title": "Server-Verwaltung",
        "back_to_app": "Zurück zur App",
        "logout": "Abmelden",
        "change_password": "Admin-Passwort ändern",
        "curr_pw": "Aktuelles Passwort",
        "new_pw": "Neues Passwort",
        "confirm_pw": "Passwort bestätigen",
        "user_mgmt": "Benutzerverwaltung",
        "add_user": "Benutzer hinzufügen",
        "role": "Rolle",
        "active": "Aktiv",
        "actions": "Aktionen",
        "global_settings": "Globale Einstellungen",
        "enable_demo": "Demo-Modus aktivieren",
        "disable_auth": "Authentifizierung deaktivieren (Auto-Login)",
        "allow_sso": "SSO-Registrierung erlauben",
        "enforce_mfa": "MFA für alle erzwingen",
        "save_settings": "Einstellungen speichern",
        "sso_config": "SSO-Konfiguration",
        "backup_reset": "Backup & Reset",
        "exp_backup": "Backup exportieren",
        "fac_reset": "Werksreset / Zurücksetzen",
    }
}

def get_locale(request: Request) -> str:
    accept = request.headers.get("Accept-Language", "").lower()
    logger.info(f"Language Detection: Header='{accept}' -> Detected='{'de' if 'de' in accept else 'en'}'")
    if "de" in accept:
        return "de"
    return "en"

def t(key: str, request: Request) -> str:
    lang = get_locale(request)
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; background-color: #111315; color: white; margin: 0; padding: 20px; box-sizing: border-box; }}
        .container {{ max-width: 400px; width: 100%; }}
        .card {{ background: #1e2124; padding: 2.5rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; }}
        .logo {{ width: 80px; height: 80px; margin-bottom: 15px; }}
        .description {{ color: #aaa; font-size: 0.9em; margin-bottom: 20px; line-height: 1.5; }}
        input {{ width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #333; background: #2b2f33; color: white; box-sizing: border-box; }}
        input:focus {{ border-color: #0066cc; outline: none; }}
        button {{ width: 100%; padding: 12px; background: #0066cc; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 1rem; margin-top: 10px; transition: background 0.2s; }}
        button:hover {{ background: #0052a3; }}
        .divider {{ margin: 20px 0; border-bottom: 1px solid #333; }}
        .sso-btn {{ background: #333; margin-top: 10px; display: flex; align-items: center; justify-content: center; }}
        .sso-btn:hover {{ background: #444; }}
        .sso-disabled {{ background: #222; color: #666; cursor: not-allowed; opacity: 0.6; }}
        .sso-disabled:hover {{ background: #222; }}
        h2 {{ margin-top: 0; color: #e1e1e1; margin-bottom: 10px; }}
        .error {{ color: #ff6666; font-size: 0.9em; margin-bottom: 15px; background: rgba(255,0,0,0.1); padding: 10px; border-radius: 4px; border: 1px solid rgba(255,0,0,0.2); }}
        .warning {{ color: #ffcc00; font-size: 0.85em; margin-top: 15px; background: rgba(255,204,0,0.1); padding: 12px; border-radius: 6px; border: 1px solid rgba(255,204,0,0.3); text-align: left; }}
        .warning strong {{ color: #ffdd44; }}
        .warning code {{ background: #333; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #333; text-align: center; font-size: 0.85em; color: #888; }}
        footer p {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <img src="/assets/switchcraft_logo.png" alt="SwitchCraft" class="logo" onerror="this.style.display='none'">
            <h2>{title}</h2>
            <p class="description">{desc}</p>

            {error_msg}

            <form action="/login" method="post">
                <input type="text" name="username" placeholder="{ph_username}" required autofocus>
                <input type="password" name="password" placeholder="{ph_password}" required>
                {mfa_field}
                <button type="submit">{btn_login}</button>
            </form>

            {sso_section}

            {default_password_warning}
        </div>

        <footer>
            <p>SwitchCraft v{version}</p>
            <p>
                <a href="https://github.com/FaserF/SwitchCraft" target="_blank">GitHub</a> |
                <a href="/admin">{link_admin}</a>
            </p>
            <p style="color: #666;">{footer}</p>
        </footer>
    </div>
</body>
</html>
"""


# --- Routes ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, sso_failed: bool = False):
    conf = auth_manager.load_config()
    if conf.get("auth_disabled"):
        resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        token = serializer.dumps({"username": "admin"})
        secure_flag = auth_manager.load_config().get("session_cookie_secure", False)
        resp.set_cookie("sc_session", token, httponly=True, max_age=86400, secure=secure_flag)
        return resp

    # Auto-redirect to Entra SSO if configured and not returning from a failed SSO attempt
    entra_configured = bool(os.environ.get("SC_ENTRA_CLIENT_ID"))
    if entra_configured and not sso_failed and request.query_params.get("manual") != "1":
        return RedirectResponse("/login/entra", status_code=status.HTTP_302_FOUND)

    mfa_field = ""
    if conf.get("mfa_enabled"):
        mfa_field = '<input type="text" name="totp_token" placeholder="MFA Code (e.g. 123456)" pattern="[0-9]{6}" autocomplete="off">'

    # SSO Buttons - Always show, greyed out if not configured
    github_configured = bool(os.environ.get("SC_GITHUB_CLIENT_ID"))

    sso_html = '<div class="divider"></div>'

    # Entra button
    if entra_configured:
        sso_html += f'<a href="/login/entra"><button class="sso-btn" type="button">🔐 {t("sso_ms", request)}</button></a>'
    else:
        sso_html += f'<button class="sso-btn sso-disabled" type="button" disabled title="Not configured - Set SC_ENTRA_CLIENT_ID">🔐 {t("sso_ms", request)} ({t("not_configured", request)})</button>'

    # GitHub button
    if github_configured:
        sso_html += f'<a href="/login/github"><button class="sso-btn" type="button">🐙 {t("sso_gh", request)}</button></a>'
    else:
        sso_html += f'<button class="sso-btn sso-disabled" type="button" disabled title="Not configured - Set SC_GITHUB_CLIENT_ID">🐙 {t("sso_gh", request)} ({t("not_configured", request)})</button>'

    # Default password warning (show if first_run is True)
    default_pw_warning = ""
    if conf.get("first_run", False):
        default_pw_warning = f'''
        <div class="warning">
            <strong>{t("default_creds_warning", request)}</strong>
        </div>
        '''

    return LOGIN_TEMPLATE.format(
        title=t("title", request),
        desc=t("desc", request),
        ph_username=t("username", request),
        ph_password=t("password", request),
        btn_login=t("login", request),
        link_admin=t("admin_panel", request),
        footer=t("footer_rights", request),
        error_msg="",
        mfa_field=mfa_field,
        sso_section=sso_html,
        default_password_warning=default_pw_warning,
        version=switchcraft.__version__
    )


# --- MFA Setup Routes ---

@app.get("/mfa/setup", response_class=HTMLResponse)
async def mfa_setup_page(request: Request, user: str = Depends(login_required)):
    # Check if already set up
    if user_manager.get_totp_secret(user):
        return HTMLResponse("<h2>Info</h2><p>MFA is already set up for your account.</p><p><a href='/'>Go to App</a></p>")

    # Generate a new secret
    secret = pyotp.random_base32()
    return MFA_SETUP_TEMPLATE.format(secret=secret, error_msg="")

@app.post("/mfa/setup", response_class=HTMLResponse)
async def mfa_setup_verify(secret: str = Form(...), code: str = Form(...), user: str = Depends(login_required)):
    totp = pyotp.TOTP(secret)
    if totp.verify(code):
        # Save secret
        user_manager.set_totp_secret(user, secret)
        logger.info(f"User '{user}' successfully set up MFA")
        return HTMLResponse("<h2>Success!</h2><p>MFA has been enabled for your account.</p><p><a href='/'>Continue to SwitchCraft</a></p>")
    else:
        error_msg = '<div style="color: #ff6666; margin-top: 10px;">Invalid code. Please try again.</div>'
        return MFA_SETUP_TEMPLATE.format(secret=secret, error_msg=error_msg)

# --- SSO Test Endpoints ---

@app.get("/admin/sso/test/{provider}")
async def test_sso_config(provider: str, user: str = Depends(admin_required)):
    if provider == "github":
        client_id = os.environ.get("SC_GITHUB_CLIENT_ID")
        client_secret = os.environ.get("SC_GITHUB_CLIENT_SECRET")
        if not client_id or not client_secret:
            return {"status": "error", "message": "GitHub SSO not configured (env vars missing)"}
        return {"status": "success", "message": "Parameters found. Try logging in to fully test."}
    elif provider == "entra":
        client_id = os.environ.get("SC_ENTRA_CLIENT_ID")
        tenant_id = os.environ.get("SC_ENTRA_TENANT_ID")
        client_secret = os.environ.get("SC_ENTRA_CLIENT_SECRET")
        if not all([client_id, tenant_id, client_secret]):
            return {"status": "error", "message": "Entra SSO not fully configured (env vars missing)"}
        return {"status": "success", "message": "Parameters found. Try logging in to fully test."}
    return {"status": "error", "message": "Unknown provider"}


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), totp_token: str = Form(None)):
    error = None

    # 1. Verify User
    if user_manager.verify_password(username, password):
        # 2. Check MFA (Global or User Specific)
        user_mfa_secret = user_manager.get_totp_secret(username)
        global_mfa = auth_manager.is_mfa_enabled()

        if global_mfa or user_mfa_secret:
            if not totp_token:
                error = "MFA Code Required"
            else:
                # Try global MFA first
                global_valid = auth_manager.verify_totp(totp_token) if global_mfa else False

                # Try user MFA
                user_valid = False
                if user_mfa_secret:
                    totp = pyotp.TOTP(user_mfa_secret)
                    user_valid = totp.verify(totp_token)

                if not (global_valid or user_valid):
                    error = "Invalid MFA Code"

        if not error:
             # Success
            user_info = user_manager.get_user(username)
            if user_info and user_info.get("must_change_password"):
                logger.info(f"User '{username}' must change password. Redirecting to Admin.")
                resp = RedirectResponse(url="/admin?force_pw_change=1", status_code=status.HTTP_303_SEE_OTHER)
                token = serializer.dumps({"username": username})
                secure_flag = auth_manager.load_config().get("session_cookie_secure", False)
                resp.set_cookie("sc_session", token, httponly=True, max_age=86400, secure=secure_flag)
                return resp

            resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            token = serializer.dumps({"username": username})
            secure_flag = auth_manager.load_config().get("session_cookie_secure", False)
            resp.set_cookie("sc_session", token, httponly=True, max_age=86400, secure=secure_flag)
            return resp
    else:
        error = "Invalid Credentials"

    sso_section = "" # Re-populate if needed
    conf = auth_manager.load_config()
    mfa_field = ""
    if conf.get("mfa_enabled"):
        mfa_field = '<input type="text" name="totp_token" placeholder="MFA Code (e.g. 123456)" pattern="[0-9]{6}" autocomplete="off">'

    # Default password warning (show if first_run is True)
    default_pw_warning = ""
    if conf.get("first_run", False):
        default_pw_warning = '''
        <div class="warning">
            <strong>⚠️ Security Notice:</strong><br>
            Default credentials are active:<br>
            Username: <code>admin</code> | Password: <code>admin</code><br><br>
            <strong>Please change the password immediately</strong> after logging in via the <a href="/admin">Admin Panel</a>.
        </div>
        '''

    return LOGIN_TEMPLATE.format(
        title=t("title", request),
        desc=t("desc", request),
        ph_username=t("username", request),
        ph_password=t("password", request),
        btn_login=t("login", request),
        link_admin=t("admin_panel", request),
        footer=t("footer_rights", request),
        error_msg=f'<div class="error">{error}</div>',
        mfa_field=mfa_field,
        sso_section=sso_section,
        default_password_warning=default_pw_warning,
        version=switchcraft.__version__
    )

@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie("sc_session")
    return resp

# --- SSO Handlers ---
@app.get("/login/github")
async def login_github():
    client_id = os.environ.get("SC_GITHUB_CLIENT_ID")
    if not client_id: raise HTTPException(404, "GitHub Auth not configured")
    scope = "read:user user:email"
    return RedirectResponse(f"https://github.com/login/oauth/authorize?client_id={client_id}&scope={scope}")

@app.get("/login/entra")
async def login_entra():
    client_id = os.environ.get("SC_ENTRA_CLIENT_ID")
    tenant_id = os.environ.get("SC_ENTRA_TENANT_ID", "common")
    if not client_id: raise HTTPException(404, "Entra Auth not configured")
    scope = "User.Read"
    return RedirectResponse(f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?client_id={client_id}&response_type=code&scope={scope}&response_mode=query&redirect_uri={os.environ.get('SC_BASE_URL', 'http://localhost:8080')}/oauth_callback/entra")

@app.get("/oauth_callback/entra")
async def entra_callback(code: str, request: Request):
    # Determine base URL for redirect URI match
    base_url = os.environ.get('SC_BASE_URL', f"{request.url.scheme}://{request.url.netloc}")
    redirect_uri = f"{base_url}/oauth_callback/entra"

    token_url = f"https://login.microsoftonline.com/{os.environ.get('SC_ENTRA_TENANT_ID', 'common')}/oauth2/v2.0/token"

    # Actual implementation requires async httpx which might fail if not installed or network blocked
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data={
                "client_id": os.environ.get("SC_ENTRA_CLIENT_ID"),
                "scope": "User.Read",
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "client_secret": os.environ.get("SC_ENTRA_CLIENT_SECRET"),
            })
            tokens = resp.json()
            if "access_token" not in tokens:
                 logger.error(f"Entra Login Failed: {tokens}")
                 return RedirectResponse("/login?sso_failed=1&error=entra_token_failed")

            # Get User Info
            me_resp = await client.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
            me = me_resp.json()

            email = me.get("mail") or me.get("userPrincipalName")
            if not email: return HTMLResponse("Could not identify user email", 400)

            # Auto-Provision Logic
            if not user_manager.get_user(email):
                conf = auth_manager.load_config()
                if not conf.get("allow_sso_registration", True):
                     return HTMLResponse("Registration via SSO is disabled", 403)

                logger.info(f"Auto-provisioning Entra user: {email}")
                user_manager.create_user(email, password=None, role="user", auto_hash=False)

            # Login
            resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            token = serializer.dumps({"username": email, "auth_method": "entra"})
            secure_flag = auth_manager.load_config().get("session_cookie_secure", False)
            resp.set_cookie("sc_session", token, httponly=True, max_age=86400, secure=secure_flag)
            return resp
    except Exception as e:
        logger.error(f"Entra SSO Error: {e}")
        return RedirectResponse("/login?sso_failed=1&error=entra_exception")

@app.get("/oauth_callback/github")
async def github_callback(code: str, request: Request):
    try:
       async with httpx.AsyncClient() as client:
          # Exchange code
          token_resp = await client.post("https://github.com/login/oauth/access_token", headers={"Accept": "application/json"}, data={
              "client_id": os.environ.get("SC_GITHUB_CLIENT_ID"),
              "client_secret": os.environ.get("SC_GITHUB_CLIENT_SECRET"),
              "code": code
          })
          tokens = token_resp.json()
          if "access_token" not in tokens:
              logger.error(f"GitHub Login Failed: {tokens}")
              return RedirectResponse("/login?sso_failed=1&error=github_token_failed")

          # Get User
          user_resp = await client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {tokens['access_token']}"})
          gh_user = user_resp.json()
          login = gh_user.get("login")

          if not user_manager.get_user(login):
               conf = auth_manager.load_config()
               if not conf.get("allow_sso_registration", True):
                    return HTMLResponse("Registration via SSO is disabled", 403)

               user_manager.create_user(login, password=None, role="user", auto_hash=False)

          resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
          token = serializer.dumps({"username": login, "auth_method": "github"})
          secure_flag = auth_manager.load_config().get("session_cookie_secure", False)
          resp.set_cookie("sc_session", token, httponly=True, max_age=86400, secure=secure_flag)
          return resp
    except Exception as e:
        logger.error(f"GitHub SSO Error: {e}")
        return RedirectResponse("/login?sso_failed=1&error=github_exception")

# --- Admin Section ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, user: str = Depends(admin_required)):
    conf = auth_manager.load_config()
    users = user_manager.list_users()

    # Check for updates
    update_info = await check_for_updates()
    logger.info(f"Admin Page Update Info: {update_info}")

    update_banner = ""
    if update_info.get("has_update"):
        update_banner = f"""
        <div style="background: #004488; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>🚀 Update Available: v{update_info['latest_version']}</strong><br>
                <span style="font-size: 0.9em;">Current: v{update_info['current_version']} | <code>{update_info['docker_command']}</code></span>
            </div>
            <a href="{update_info['release_url']}" target="_blank"><button style="background: white; color: #004488; margin: 0;">View Release</button></a>
        </div>
        """
    elif update_info.get("error"):
        logger.warning(f"Update check failed: {update_info['error']}")
    else:
        # Up to date
        update_banner = f"""
        <div style="background: #00aa44; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>✅ SwitchCraft is up to date</strong><br>
                <span style="font-size: 0.9em;">Version: v{switchcraft.__version__} | Channel: {update_info.get('channel', 'stable')}</span>
            </div>
             <button disabled style="background: rgba(255,255,255,0.2); color: white; cursor: default; margin: 0;">Latest Version</button>
        </div>
        """

    # Render Users Table
    users_html = f"<table style='width:100%; text-align:left; border-collapse:collapse;'><tr><th>{t('username', request)}</th><th>{t('role', request)}</th><th>{t('active', request)}</th><th>{t('actions', request)}</th></tr>"
    for u in users:
        active_status = "✅" if u.get('is_active') else "❌"
        users_html += f"<tr><td>{u['username']}</td><td>{u['role']}</td><td>{active_status}</td>"
        # Prevent deleting self or critical admin if only one?
        users_html += f"<td><form method='post' action='/admin/users/delete' onsubmit='return confirm(\"Delete?\");' style='display:inline;'><input type='hidden' name='username' value='{u['username']}'><button style='padding:2px 8px; font-size:12px; background:#cc0000; margin:0;'>Del</button></form></td></tr>"
    users_html += "</table>"

    # Password change warning banner
    password_warning = ""
    if conf.get("first_run", False) or request.query_params.get("force_pw_change") == "1":
        msg = "You are using a temporary or default password!" if request.query_params.get("force_pw_change") == "1" else "You are using the default admin password!"
        password_warning = f'''
        <div style="background: #cc3300; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; border: 2px solid #ffdd44;">
            <strong>⚠️ SECURITY WARNING: {msg}</strong><br>
            Please change it immediately using the form below to unlock all features.
        </div>
        '''

    # SSO Configuration section
    entra_client = os.environ.get("SC_ENTRA_CLIENT_ID", "")
    entra_tenant = os.environ.get("SC_ENTRA_TENANT_ID", "")
    github_client = os.environ.get("SC_GITHUB_CLIENT_ID", "")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{t('admin_title', request)}</title>
        <link rel="icon" type="image/png" href="/assets/favicon.png">
         <style>
            body {{ font-family: 'Segoe UI', sans-serif; padding: 20px; background-color: #111315; color: #eee; }}
            .card {{ background: #1e2124; padding: 30px; border-radius: 12px; max-width: 900px; margin: 0 auto; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
            h2, h3 {{ border-bottom: 1px solid #333; padding-bottom: 10px; }}
            input, select {{ padding: 8px; border-radius: 4px; border: 1px solid #444; background: #222; color: white; margin-right: 5px; }}
            input[type="text"], input[type="password"] {{ min-width: 200px; }}
            td, th {{ padding: 8px; border-bottom: 1px solid #333; }}
            button {{ padding: 8px 16px; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; margin: 5px 0; }}
            button:hover {{ background: #0052a3; }}
            .btn-danger {{ background: #cc0000; }}
            .btn-danger:hover {{ background: #990000; }}
            .btn-success {{ background: #00aa44; }}
            .btn-success:hover {{ background: #008833; }}
            a {{ color: #0099ff; text-decoration: none; }}
            .toggle-label {{ display: flex; align-items: center; justify-content: space-between; padding: 10px; background: #2b2f33; border-radius: 5px; margin-bottom: 10px; }}
            input[type="checkbox"] {{ transform: scale(1.5); margin-left: 10px; }}
            .section {{ margin: 25px 0; padding: 20px; background: #2b2f33; border-radius: 8px; }}
            .section h4 {{ margin-top: 0; color: #aaa; }}
            .inline-form {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
            footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #333; text-align: center; font-size: 0.85em; color: #888; }}
        </style>
        <script>
            async function testSSO(provider) {{
                const btn = event.target;
                const originalText = btn.innerText;
                btn.innerText = 'Testing...';
                btn.disabled = true;

                try {{
                    const resp = await fetch('/admin/sso/test/' + provider);
                    const data = await resp.json();
                    alert(data.status.toUpperCase() + ": " + data.message);
                }} catch (e) {{
                    alert("Error testing " + provider + ": " + e);
                }} finally {{
                    btn.innerText = originalText;
                    btn.disabled = false;
                }}
            }}
        </script>
    </head>
    <body>
        <div class="card">
            <h1>🔧 {t('admin_title', request)}</h1>
            <p>Logged in as: <b>{user}</b> | <a href="/">{t('back_to_app', request)}</a> | <a href="/logout">{t('logout', request)}</a></p>

            {update_banner}
            {password_warning}

            <!-- Password Change Section -->
            <div class="section">
                <h4>🔐 {t('change_password', request)}</h4>
                <form action="/admin/password" method="post" class="inline-form">
                    <input type="password" name="current_password" placeholder="{t('curr_pw', request)}" required>
                    <input type="password" name="new_password" placeholder="{t('new_pw', request)}" required minlength="6">
                    <input type="password" name="confirm_password" placeholder="{t('confirm_pw', request)}" required minlength="6">
                    <button type="submit" class="btn-success">{t('change_password', request)}</button>
                </form>
            </div>

            <h3>👥 {t('user_mgmt', request)}</h3>
            {users_html}

            <h4>{t('add_user', request)}</h4>
            <form action="/admin/users/add" method="post" class="inline-form">
                <input type="text" name="username" placeholder="{t('username', request)}" required>
                <input type="password" name="password" placeholder="{t('password', request)}" required>
                <select name="role"><option value="user">User</option><option value="admin">Admin</option></select>
                <button type="submit">{t('add_user', request)}</button>
            </form>

            <h3>⚙️ {t('global_settings', request)}</h3>
            <form action="/admin/settings" method="post">
                <div class="toggle-label">
                    <label>{t('enable_demo', request)}</label>
                    <input type="checkbox" name="demo_mode" {'checked' if conf.get('demo_mode') else ''}>
                </div>
                <div class="toggle-label">
                    <label>{t('disable_auth', request)}</label>
                    <input type="checkbox" name="auth_disabled" {'checked' if conf.get('auth_disabled') else ''}>
                </div>
                <div class="toggle-label">
                    <label>{t('allow_sso', request)}</label>
                    <input type="checkbox" name="allow_sso_registration" {'checked' if conf.get('allow_sso_registration', True) else ''}>
                </div>
                <div class="toggle-label">
                    <label>{t('enforce_mfa', request)}</label>
                    <input type="checkbox" name="enforce_mfa" {'checked' if conf.get('enforce_mfa') else ''}>
                </div>
                <p style="font-size: 0.8em; color: #888; margin-top: -5px;">When enabled, users without MFA will be required to set it up on next login.</p>
                <br>
                <button type="submit">{t('save_settings', request)}</button>
            </form>

            <!-- SSO Configuration -->
            <div class="section">
                <h4>🔑 {t('sso_config', request)}</h4>
                <p style="color: #888; font-size: 0.9em;">Configure Single Sign-On providers. Set via environment variables.</p>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <h5 style="margin: 0;">Microsoft Entra ID</h5>
                        <p style="font-size: 0.85em; color: #666; margin: 5px 0;">
                            Client ID: <code>{entra_client[:8] if entra_client else 'Not Set'}...</code>
                        </p>
                    </div>
                    <button onclick="testSSO('entra')" style="padding: 5px 12px; font-size: 0.85em;">Test Config</button>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h5 style="margin: 0;">GitHub OAuth</h5>
                        <p style="font-size: 0.85em; color: #666; margin: 5px 0;">
                            Client ID: <code>{github_client[:8] if github_client else 'Not Set'}...</code>
                        </p>
                    </div>
                    <button onclick="testSSO('github')" style="padding: 5px 12px; font-size: 0.85em;">Test Config</button>
                </div>
            </div>

            <!-- Backup & Reset -->
            <div class="section">
                <h4>💾 {t('backup_reset', request)}</h4>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <a href="/admin/backup"><button type="button">📥 {t('exp_backup', request)}</button></a>
                    <form action="/admin/reset" method="post" onsubmit="return confirm('⚠️ This will DELETE ALL DATA and reset to defaults. Are you absolutely sure?');" style="display: inline;">
                        <button type="submit" class="btn-danger">🗑️ {t('fac_reset', request)}</button>
                    </form>
                </div>
            </div>

            <footer>
                <p>SwitchCraft v{switchcraft.__version__}</p>
                <p><a href="https://github.com/FaserF/SwitchCraft" target="_blank">GitHub</a> | {t('footer_rights', request)}</p>
            </footer>
        </div>
    </body>
    </html>
    """

@app.post("/admin/users/add")
async def add_user(username: str = Form(...), password: str = Form(...), role: str = Form("user"), u: str = Depends(admin_required)):
    if user_manager.create_user(username, password, role):
        return RedirectResponse("/admin", status_code=303)
    return HTMLResponse(f"Error: User {username} already exists.", 400)

@app.post("/admin/users/delete")
async def delete_user_route(username: str = Form(...), u: str = Depends(admin_required)):
    if username == "admin": return HTMLResponse("Cannot delete root admin", 400)
    user_manager.delete_user(username)
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/settings")
async def update_settings(demo_mode: bool = Form(False), auth_disabled: bool = Form(False), allow_sso_registration: bool = Form(False), enforce_mfa: bool = Form(False), u: str = Depends(admin_required)):
    auth_manager.set_demo_mode(demo_mode)
    auth_manager.set_auth_disabled(auth_disabled)
    auth_manager.set_sso_registration(allow_sso_registration)
    # Update enforce_mfa
    conf = auth_manager.load_config()
    conf["enforce_mfa"] = enforce_mfa
    auth_manager.save_config(conf)
    switchcraft.IS_DEMO = demo_mode
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/password")
async def change_password(current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), user: str = Depends(admin_required)):
    """Change the admin user's password."""
    # Verify new passwords match
    if new_password != confirm_password:
        return HTMLResponse("<h2>Error</h2><p>New passwords do not match.</p><p><a href='/admin'>Back to Admin</a></p>", 400)

    # Verify current password
    if not user_manager.verify_password(user, current_password):
        return HTMLResponse("<h2>Error</h2><p>Current password is incorrect.</p><p><a href='/admin'>Back to Admin</a></p>", 400)

    # Update password
    if user_manager.update_password(user, new_password):
        # Clear first_run flag since password has been changed
        conf = auth_manager.load_config()
        conf["first_run"] = False
        auth_manager.save_config(conf)
        return RedirectResponse("/admin", status_code=303)

    return HTMLResponse("<h2>Error</h2><p>Failed to update password.</p><p><a href='/admin'>Back to Admin</a></p>", 500)

@app.get("/admin/backup")
async def admin_backup(user: str = Depends(admin_required)):
    """Export all server configuration as a ZIP file."""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add auth config
        auth_config_path = Path(auth_manager.config_file)
        if auth_config_path.exists():
            zf.write(auth_config_path, "auth_config.json")

        # Add users file
        users_path = Path(user_manager.users_file)
        if users_path.exists():
            zf.write(users_path, "users.json")

        # Add any other config files in the config directory
        config_dir = auth_config_path.parent
        for config_file in config_dir.glob("*.json"):
            if config_file.name not in ["auth_config.json", "users.json"]:
                zf.write(config_file, config_file.name)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=switchcraft_backup.zip"}
    )

@app.post("/admin/reset")
async def admin_reset(user: str = Depends(admin_required)):
    """Factory reset - delete all configuration and users."""
    # Delete auth config
    auth_config_path = Path(auth_manager.config_file)
    if auth_config_path.exists():
        auth_config_path.unlink()

    # Delete users file
    users_path = Path(user_manager.users_file)
    if users_path.exists():
        users_path.unlink()

    # Re-initialize with defaults immediately to prevent lockout
    try:
        user_manager._ensure_users_file()
    except Exception as e:
        logger.error(f"Failed to recreate default admin during reset: {e}")

    # Force logout
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("sc_session")
    return resp


@app.get("/api/me")
async def get_me(user: str = Depends(get_current_user)):
    return {"username": user}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/assets/favicon.ico")

# Flet Auth Middleware
async def flet_auth_middleware(request: Request, call_next):
    path = request.url.path
    path_lower = path.lower()

    # 1. Broad whitelist for static/engine assets to prevent "FormatException"
    # This MUST be extremely permissive for anyone to load the engine
    static_exts = [
        ".js", ".mjs", ".json", ".wasm", ".png", ".ico", ".txt",
        ".webmanifest", ".woff", ".woff2", ".ttf", ".svg", ".jpg",
        ".jpeg", ".map", ".otf", ".cur"
    ]

    # If it looks like a static asset, let it through
    if (
        path.startswith("/assets/") or
        any(path_lower.endswith(ext) for ext in static_exts) or
        "main.dart" in path_lower or
        "flutter" in path_lower or
        "canvaskit" in path_lower or
        path_lower.endswith("/manifest.json") or # Specific check for manifest file
        path_lower.endswith("/notices") or
        path_lower.endswith("/version")
    ):
        return await call_next(request)

    # 2. Whitelist explicit UI paths
    whitelist = ["/login", "/logout", "/admin", "/api", "/oauth_callback", "/favicon.ico"]
    if any(path.startswith(p) for p in whitelist):
        return await call_next(request)

    user = get_current_user(request)
    if not user:
        if "websocket" in request.headers.get("upgrade", "").lower():
            # Allow websocket upgrades even for unauthenticated requests
            # (Flet's application logic will handle auth internally)
            return await call_next(request)

        # If it's a request for a potentially missing static file that's not in our extension list
        # we still want to avoid redirecting to /login if it's likely a Flet internal request.
        # But for now, the extension list is quite comprehensive.

        logger.debug(f"Unauthenticated access to {path}, redirecting to /login")
        return RedirectResponse("/login")

    # Enforce password change if flag is set
    u_info = user_manager.get_user(user)
    if u_info and u_info.get("must_change_password"):
        # If not on /admin (where change is handled) or /logout or /api
        if not request.url.path.startswith("/admin") and not request.url.path.startswith("/logout") and not request.url.path.startswith("/api"):
            logger.warning(f"User '{user}' must change password before accessing {request.url.path}")
            return RedirectResponse("/admin?force_pw_change=1")

    return await call_next(request)

app.middleware("http")(flet_auth_middleware)

# --- Upload Handler ---
UPLOAD_DIR = Path(tempfile.gettempdir()) / "switchcraft_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/upload")
async def upload_endpoint(files: list[UploadFile]):
    saved_files = []
    for file in files:
        if not file.filename:
            continue

        # Keep only alphanumeric, dots, dashes, underscores
        clean_name = "".join(x for x in file.filename if x.isalnum() or x in "-_.")

        # Prevent hidden files (leading dots) and ensure it's not empty after cleaning
        clean_name = clean_name.lstrip(".")
        if not clean_name:
            import uuid
            clean_name = f"upload_{uuid.uuid4().hex[:8]}.bin"

        # Append short UUID and ensure uniqueness
        import uuid
        uid = uuid.uuid4().hex[:8]
        parts = clean_name.rsplit(".", 1)

        candidate_name = clean_name
        if len(parts) > 1:
            candidate_name = f"{parts[0]}_{uid}.{parts[1]}"
        else:
            candidate_name = f"{clean_name}_{uid}"

        path = UPLOAD_DIR / candidate_name
        # Final collision safety loop (backup in case of rapid concurrent identical uploads)
        while path.exists():
            uid = uuid.uuid4().hex[:4]
            parts = candidate_name.rsplit("_", 1) # Split by our own suffix
            if len(parts) > 1:
                # Re-try with new suffix
                base = parts[0]
                ext_parts = parts[1].rsplit(".", 1)
                if len(ext_parts) > 1:
                    candidate_name = f"{base}_{uid}.{ext_parts[1]}"
                else:
                    candidate_name = f"{base}_{uid}"
            else:
                candidate_name = f"{candidate_name}_{uid}"
            path = UPLOAD_DIR / candidate_name

        try:
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(str(path))
        finally:
            file.file.close()
    return {"uploaded": saved_files}

# --- Flet App Integration ---
async def before_main(page: ft.Page):
    """
    Called before the main Flet app starts.
    Injects authenticated username and browser language into the page session.
    """
    # Initialize switchcraft_session dict if not present
    if not hasattr(page, 'switchcraft_session'):
        page.switchcraft_session = {}

    # Inject authenticated username from HTTP request cookies
    try:
        # Get the request from page (Flet FastAPI integration)
        request = page.request
        if request:
            cookies = request.cookies
            token = cookies.get("sc_session")
            if token:
                try:
                    data = serializer.loads(token, max_age=86400)
                    username = data.get("username", "User")
                    page.switchcraft_session['username'] = username
                    logger.info(f"Injected username '{username}' into Flet session")
                except Exception as e:
                    logger.warning(f"Failed to decode session token: {e}")
                    page.switchcraft_session['username'] = "User"

            # Detect browser language from Accept-Language header
            accept_lang = request.headers.get("Accept-Language", "")
            logger.info(f"Flet before_main: Accept-Language='{accept_lang}'")
            if accept_lang:
                # Parse Accept-Language: e.g. "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
                lang_parts = accept_lang.split(",")
                if lang_parts:
                    primary_lang = lang_parts[0].split(";")[0].strip().lower()
                    logger.info(f"Flet before_main: Primary detected='{primary_lang}'")
                    # Check if German
                    if primary_lang.startswith("de"):
                        page.switchcraft_session['browser_language'] = "de"
                        logger.info("Flet before_main: Setting language to 'de'")
                        # Set i18n language directly
                        try:
                            from switchcraft.utils.i18n import i18n
                            i18n.set_language("de")
                        except Exception:
                            pass
                        logger.info("Detected browser language: German")
                    else:
                        page.switchcraft_session['browser_language'] = "en"
                        try:
                            from switchcraft.utils.i18n import i18n
                            i18n.set_language("en")
                        except Exception:
                            pass
                        logger.info(f"Detected browser language: English (from {primary_lang})")
    except Exception as e:
        logger.warning(f"before_main error: {e}")
        page.switchcraft_session['username'] = "User"

# Mount Flet with before_main handler
import flet.fastapi as flet_fastapi
flet_app = flet_fastapi.app(
    flet_main,
    before_main,
    upload_endpoint_path="/upload",
    assets_dir=str(ASSETS_DIR),
    web_renderer=ft.WebRenderer.HTML
)
app.mount("/", flet_app)
