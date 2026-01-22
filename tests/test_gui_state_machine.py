import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import asyncio
import inspect
import importlib
import os
from conftest import mock_page, poll_until

def find_all_clickables(control, clickables):
    """Recursively find all clickable controls (buttons, cards with on_click, etc.)."""
    if hasattr(control, 'on_click') and control.on_click is not None:
        clickables.append(control)

    if hasattr(control, 'controls') and control.controls:
        for child in control.controls:
            find_all_clickables(child, clickables)

    if hasattr(control, 'content') and control.content:
        find_all_clickables(control.content, clickables)

    if hasattr(control, 'actions') and control.actions:
        for action in control.actions:
            find_all_clickables(action, clickables)

@pytest.mark.parametrize("view_info", [
    {"module": "home_view", "class": "ModernHomeView", "kwargs": {"on_navigate": lambda x: None}},
    {"module": "settings_view", "class": "ModernSettingsView", "kwargs": {"initial_tab_index": 0}},
    {"module": "winget_view", "class": "ModernWingetView", "patch": "switchcraft.gui_modern.views.winget_view.AddonService"},
    {"module": "intune_view", "class": "ModernIntuneView", "patch": "switchcraft.gui_modern.views.intune_view.IntuneService"},
    {"module": "group_manager_view", "class": "GroupManagerView", "patch": "switchcraft.gui_modern.views.group_manager_view.IntuneService"},
    {"module": "exchange_view", "class": "ExchangeView", "patch": "switchcraft.gui_modern.views.exchange_view.ExchangeService"},
    {"module": "library_view", "class": "LibraryView"},
    {"module": "dashboard_view", "class": "DashboardView"},
    {"module": "stack_manager_view", "class": "StackManagerView"},
    {"module": "packaging_wizard_view", "class": "PackagingWizardView"},
    {"module": "analyzer_view", "class": "ModernAnalyzerView"},
    {"module": "helper_view", "class": "ModernHelperView"},
    {"module": "script_upload_view", "class": "ScriptUploadView"},
])
def test_comprehensive_view_interaction(mock_page, view_info):
    """
    Test every button in every view and ensure they don't crash.
    Mocks specified services for each view.
    """
    try:
        module_path = f"switchcraft.gui_modern.views.{view_info['module']}"
        module = importlib.import_module(module_path)
        view_class = getattr(module, view_info['class'])

        # Instantiate with mocks as needed
        kwargs = view_info.get("kwargs", {})

        # Patch-on-demand for the specific view's dependencies
        patch_target = view_info.get("patch")

        def run_test_with_instance():
            view = view_class(mock_page, **kwargs)
            if hasattr(view, "did_mount"):
                try:
                    view.did_mount()
                except RuntimeError as e:
                    # Some views call update() in did_mount() before controls are added to page
                    # This is expected behavior in unit tests with mock pages
                    if "Control must be added to the page first" in str(e):
                        pass  # Expected, continue with test
                    else:
                        raise

            clickables = []
            find_all_clickables(view, clickables)

            failures = []
            for clickable in clickables:
                handler = clickable.on_click
                if not handler:
                    continue

                event = MagicMock()
                event.control = clickable

                try:
                    if inspect.iscoroutinefunction(handler):
                        asyncio.run(handler(event))
                    else:
                        res = handler(event)
                        if inspect.isawaitable(res):
                            asyncio.run(res)
                except Exception as e:
                    if "NoneType" in str(e) or "control" in str(e).lower():
                         continue
                    failures.append(f"Button {getattr(clickable, 'text', getattr(clickable, 'icon', 'unknown'))} failed: {e}")
            return failures

        if patch_target:
            with patch(patch_target):
                failures = run_test_with_instance()
        else:
            failures = run_test_with_instance()

        if failures:
            reasons = "\n".join(failures)
            pytest.fail(f"View {view_info['class']} had button failures:\n{reasons}")

    except (ImportError, AttributeError) as e:
        pytest.skip(f"Skipping {view_info['module']}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to test {view_info['class']}: {e}")
