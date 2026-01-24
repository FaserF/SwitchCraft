import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import os
import secrets
import shutil
from pathlib import Path

# Needed for FletApp mount to work without GUI
os.environ["FLET_PLATFORM"] = "web"

from switchcraft.server.app import app, auth_manager, user_manager

# Setup Test Client
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_env():
    """Setup a temporary config directory for the duration of tests."""
    test_dir = Path("./temp_test_data")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)

    # Override managers to use test dir
    auth_manager.config_dir = test_dir / "server"
    auth_manager.config_file = auth_manager.config_dir / "auth_config.json"
    auth_manager._ensure_dir()

    user_manager.data_dir = test_dir / "server"
    user_manager.users_file = user_manager.data_dir / "users.json"
    user_manager._ensure_users_file()

    yield

    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)

def test_login_flow():
    """Test basic login and logout."""
    # 1. Initial State: Unauthenticated
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 307
    assert "/login" in resp.headers["location"]

    # 2. Login with wrong password
    resp = client.post("/login", data={"username": "admin", "password": "wrongpassword"})
    assert "Invalid Credentials" in resp.text

    # 3. Login with correct password (default: admin)
    # Note: UserManager initializes 'admin' with 'admin' in _ensure_users_file IF it doesn't exist.
    # But since we mocked the dir, it should be fresh.
    resp = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    assert resp.status_code == 303
    assert "sc_session" in resp.cookies

    token = resp.cookies["sc_session"]

    # 4. Access Protected Route
    resp = client.get("/api/me", cookies={"sc_session": token})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"

    # 5. Access Admin Route
    resp = client.get("/admin", cookies={"sc_session": token})
    assert resp.status_code == 200
    assert "Server Administration" in resp.text

    # 6. Logout
    resp = client.get("/logout", cookies={"sc_session": token}, follow_redirects=False)
    assert resp.status_code == 303

    # 7. Check Token Invalidated (Cookie deleted)
    assert 'sc_session=""' in resp.headers.get("set-cookie", "")

def test_user_management_by_admin():
    """Test creating and deleting users via Admin API."""
    # Login as Admin
    resp = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    token = resp.cookies["sc_session"]

    # 1. Create User
    resp = client.post("/admin/users/add",
                       data={"username": "testuser", "password": "password123", "role": "user"},
                       cookies={"sc_session": token},
                       follow_redirects=False)
    assert resp.status_code == 303

    # Verify creation
    u = user_manager.get_user("testuser")
    assert u is not None
    assert u["role"] == "user"
    assert user_manager.verify_password("testuser", "password123")

    # 2. Delete User
    resp = client.post("/admin/users/delete",
                       data={"username": "testuser"},
                       cookies={"sc_session": token},
                       follow_redirects=False)
    assert resp.status_code == 303

    # Verify deletion
    u = user_manager.get_user("testuser")
    assert u is None

def test_sso_registration_toggle():
    """Test the allow_sso_registration logic."""
    # Mock AuthConfig to ensure clean state
    auth_manager.set_sso_registration(True)

    # Login as Admin
    resp = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    token = resp.cookies["sc_session"]

    # 1. Mock SSO Callback (Entra) - Success Case (Auto Provisioning ON)
    with patch("httpx.AsyncClient", autospec=True) as MockClientClass:
        mock_client_instance = MockClientClass.return_value
        mock_client_instance.__aenter__.return_value = mock_client_instance

        # Mock Response Objects
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "fake_token"}
        mock_client_instance.post.return_value = mock_token_resp # post is async method

        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {"mail": "newuser@example.com"}
        mock_client_instance.get.return_value = mock_user_resp

        resp = client.get("/oauth_callback/entra?code=fake_code", follow_redirects=False)
        assert resp.status_code == 303 # Redirects to / on success

        # Verify user created
        assert user_manager.get_user("newuser@example.com") is not None

    # 2. Disable SSO Registration
    # In FastAPI Form, boolean is False if missing/False.
    client.post("/admin/settings",
                data={"demo_mode": False, "auth_disabled": False}, # Missing allow_sso_registration -> False
                cookies={"sc_session": token})

    conf = auth_manager.load_config()
    assert conf["allow_sso_registration"] == False

    # 3. Mock SSO Callback - Failure Case (Auto Provisioning OFF)
    with patch("httpx.AsyncClient", autospec=True) as MockClientClass:
        mock_client_instance = MockClientClass.return_value
        mock_client_instance.__aenter__.return_value = mock_client_instance

        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "fake_token_2"}
        mock_client_instance.post.return_value = mock_token_resp

        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {"mail": "rejected@example.com"}
        mock_client_instance.get.return_value = mock_user_resp

        resp = client.get("/oauth_callback/entra?code=fake_code_2", follow_redirects=False)
        assert resp.status_code == 403
        assert "Registration via SSO is disabled" in resp.text

        # Verify user NOT created
        assert user_manager.get_user("rejected@example.com") is None

def test_feature_flags():
    """Test Demo Mode and Auth Disabled behavior."""
    # 1. Enable Demo Mode
    resp = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    token = resp.cookies["sc_session"]

    client.post("/admin/settings", data={"demo_mode": True, "auth_disabled": False}, cookies={"sc_session": token})

    conf = auth_manager.load_config()
    assert conf["demo_mode"] == True

    # 2. Enable Auth Disabled (No-Auth Mode)
    client.post("/admin/settings", data={"demo_mode": False, "auth_disabled": True}, cookies={"sc_session": token})

    conf = auth_manager.load_config()
    assert conf["auth_disabled"] == True

    # 3. Verify Login Bypass
    # Clear cookies to simulate new user
    client.cookies.clear()

    # Accessing login should redirect to home with auto-login token
    resp = client.get("/login", follow_redirects=False) # follow_redirects=False to see 303
    assert resp.status_code == 303
    assert "sc_session" in resp.cookies
    assert "admin" in resp.cookies["sc_session"] or len(resp.cookies["sc_session"]) > 0

    # Access protected route directly without cookie (should auto-login inside get_current_user?)
    # Our implementation checks cookie first. If missing, checks auth_disabled flag.
    # In app.py: get_current_user returns "admin (no-auth)" if auth_disabled and no token.
    resp = client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
