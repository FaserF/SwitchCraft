"""Regression tests for Analyzer upload, Winget manifest generation, and NotificationService."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from switchcraft.services.notification_service import NotificationService


def test_analyzer_manifest_helpers_and_upload_guard(tmp_path: Path) -> None:
    """Verify SHA256 calculation, InstallerType normalization, and identifier sanitization."""
    # Mock flet if not installed in minimal test env
    if "flet" not in sys.modules:
        ft_mock = MagicMock()
        ft_mock.Column = object
        sys.modules["flet"] = ft_mock

    from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView

    sample = tmp_path / "installer.exe"
    sample.write_bytes(b"switchcraft-test-binary")
    expected_sha = hashlib.sha256(b"switchcraft-test-binary").hexdigest().upper()

    assert ModernAnalyzerView._compute_file_sha256(str(sample)) == expected_sha
    assert ModernAnalyzerView._compute_file_sha256(str(tmp_path / "missing.exe")) == "0" * 64
    assert ModernAnalyzerView._normalize_winget_installer_type("Inno Setup") == "inno"
    assert ModernAnalyzerView._normalize_winget_installer_type("NSIS") == "nullsoft"
    assert ModernAnalyzerView._normalize_winget_installer_type("MSI") == "msi"
    assert (
        ModernAnalyzerView._sanitize_winget_identifier("Contoso Ltd. / My App!")
        == "ContosoLtd.MyApp"
    )

    # Verify _on_file_upload preserves server-returned path when present
    view = ModernAnalyzerView.__new__(ModernAnalyzerView)
    started: list[tuple[str, str | None]] = []
    view.start_analysis = lambda path, cleanup_path=None: started.append((path, cleanup_path))  # type: ignore[method-assign]
    view._show_snack = MagicMock()  # type: ignore[method-assign]

    ev = SimpleNamespace(
        error=None,
        data=json.dumps({"uploaded": [str(sample)]}),
        file_name="installer.exe",
    )
    view._on_file_upload(ev)
    assert started == [(str(sample), str(sample))]


def test_notification_service_notifies_listeners(tmp_path: Path, monkeypatch) -> None:
    """NotificationService records notifications and triggers registered UI listeners."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    NotificationService._instance = None
    NotificationService._listeners = []

    svc = NotificationService()
    events: list[int] = []
    svc.add_listener(lambda: events.append(len(svc.get_notifications())))

    notif = svc.add_notification("Build Done", "Signed artifact ready", type="success")
    assert notif["title"] == "Build Done"
    assert events == [1]
    assert svc.get_unread_count() == 1
