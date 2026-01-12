
import pytest
from unittest.mock import MagicMock, patch
from switchcraft.utils.updater import UpdateChecker

@pytest.fixture
def mock_requests():
    with patch("switchcraft.utils.updater.requests") as mock:
        yield mock

def test_stable_channel_stable_update(mock_requests):
    """Test standard stable update."""
    checker = UpdateChecker(channel="stable")
    checker.current_version = "1.0.0"

    # Mock Stable Response
    mock_requests.get.return_value.status_code = 200
    mock_requests.get.return_value.json.return_value = {
        "tag_name": "v1.1.0",
        "html_url": "url",
        "body": "notes",
        "published_at": "2025-01-01T00:00:00Z",
        "prerelease": False
    }

    has_update, ver, data = checker.check_for_updates()
    assert has_update is True
    assert ver == "1.1.0"
    assert data["tag_name"] == "v1.1.0"

def test_dev_channel_finds_stable_if_newer(mock_requests):
    """User on Dev, but a minimal Stable release is available (no dev update)."""
    checker = UpdateChecker(channel="dev")
    checker.current_version = "dev-old"

    # Mock Stable: New Version
    stable_resp = MagicMock()
    stable_resp.status_code = 200
    stable_resp.json.return_value = {
        "tag_name": "v2.0.0",
        "published_at": "2025-02-01T00:00:00Z",
        "prerelease": False
    }

    # Mock Beta: None
    beta_resp = MagicMock()
    beta_resp.status_code = 200
    beta_resp.json.return_value = []

    # Mock Dev: Same as current
    dev_resp = MagicMock()
    dev_resp.status_code = 200
    dev_resp.json.return_value = {
        "sha": "old",
        "commit": {
             "message": "old commit",
             "committer": {"date": "2025-01-01T00:00:00Z"}
        }
    }

    mock_requests.get.side_effect = [stable_resp, beta_resp, dev_resp]

    has_update, ver, data = checker.check_for_updates()
    assert has_update is True
    assert ver == "2.0.0" # Should pick Stable 2.0.0 over dev-old

def test_dev_channel_prefers_dev_if_newer(mock_requests):
    """User on Dev, new Dev commit available."""
    checker = UpdateChecker(channel="dev")
    checker.current_version = "dev-old"

    # Stable: Old
    stable_resp = MagicMock()
    stable_resp.status_code = 200
    stable_resp.json.return_value = {"tag_name": "v1.0.0", "prerelease": False} # older

    # Beta: None
    beta_resp = MagicMock()
    beta_resp.status_code = 200
    beta_resp.json.return_value = []

    # Dev: New SHA
    dev_resp = MagicMock()
    dev_resp.status_code = 200
    dev_resp.json.return_value = {
        "sha": "newhash",
        "commit": {
             "message": "new commit",
             "committer": {"date": "2025-03-01T00:00:00Z"}
        }
    }

    mock_requests.get.side_effect = [stable_resp, beta_resp, dev_resp]

    has_update, ver, data = checker.check_for_updates()
    assert has_update is True
    assert ver == "dev-newhash"

def test_no_update_found(mock_requests):
    checker = UpdateChecker(channel="stable")
    checker.current_version = "1.0.0"

    mock_requests.get.return_value.status_code = 200
    mock_requests.get.return_value.json.return_value = {
        "tag_name": "v1.0.0", # Same version
        "prerelease": False
    }

    has_update, ver, _ = checker.check_for_updates()
    assert has_update is False
    assert ver == "1.0.0"
