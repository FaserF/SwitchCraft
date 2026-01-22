"""
E2E Test for Packaging Wizard Flow
Simulates the user journey:
1. Upload PowerShell Script/Installer
2. Configure Packaging Options
3. Genereate Script
4. Build Package
5. Verify Output/Success
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from conftest import poll_until, _create_mock_page

# Mock Dependencies
@pytest.fixture
def mock_packaging_deps():
    with patch("switchcraft.gui_modern.views.packaging_wizard_view.IntuneService") as mock_intune, \
         patch("switchcraft.gui_modern.views.packaging_wizard_view.FilePickerHelper") as mock_picker, \
         patch("switchcraft.gui_modern.views.packaging_wizard_view.SwitchCraftConfig") as mock_config:

        # Setup Intune Service Mock
        intune_instance = MagicMock()
        mock_intune.return_value = intune_instance
        intune_instance.create_intunewin.return_value = "Package created at C:\\Output\\app.intunewin"

        yield {
            "intune": intune_instance,
            "picker": mock_picker,
            "config": mock_config
        }

def test_packaging_e2e_flow(mock_packaging_deps):
    """
    Test the complete packaging flow from upload to build.
    """
    from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView

    # Init mock page
    mock_page = _create_mock_page()
    mock_page.switchcraft_session = {}

    # Patch PackagingWizardView.page property for the ENTIRE test execution
    with patch("switchcraft.gui_modern.views.packaging_wizard_view.PackagingWizardView.page", new_callable=PropertyMock) as mock_page_prop:
        mock_page_prop.return_value = mock_page

        # 1. Initialize View
        view = PackagingWizardView(mock_page)
        view.update = MagicMock()

        # 2. Simulate File Selection (Upload)
        dummy_file_path = "C:\\Scripts\\install_app.ps1"
        view.installer_path = dummy_file_path

        # 3. Configure/Edit Script
        view.current_step = 2

        # 3a. Generate Script
        view.analysis_result = MagicMock()
        view.analysis_result.info.install_switches = ["/S"]

        # Initialize UI for step 2
        view._step_script_ui()
        view.script_field.value = "# Modified Script\nStart-Process..."

        # Mock file I/O for saving AND checking existence
        # We need Path.exists to remain mocked during both _save_script AND _run_packaging (thread)
        with patch("builtins.open", new_callable=MagicMock), \
             patch("switchcraft.gui_modern.views.packaging_wizard_view.Path.exists", return_value=True), \
             patch("switchcraft.gui_modern.views.packaging_wizard_view.Path.parent", new_callable=MagicMock) as mock_parent:

             mock_parent.return_value.__truediv__.return_value = "C:\\Scripts\\install.ps1"

             # Mock subprocess for signing
             with patch("subprocess.run") as mock_run:
                 result_mock = MagicMock()
                 result_mock.returncode = 0
                 mock_run.return_value = result_mock

                 view._save_script()

                 # Ensure path is set
                 if not view.generated_script_path:
                      view.generated_script_path = "C:\\Scripts\\install.ps1"

                 view.current_step = 3
                 view._step_package_ui()

                 # 4. Trigger Build
                 build_btn = view.pkg_btn
                 assert build_btn is not None
                 assert not build_btn.disabled

                 mock_event = MagicMock()
                 # This triggers the thread which calls Path.exists.
                 # Since we are inside the 'with patch(...Path.exists...)' block, the thread should see the mock.
                 build_btn.on_click(mock_event)

                 # 5. Verify Build Trigger
                 def service_called():
                     return mock_packaging_deps["intune"].create_intunewin.called

                 assert poll_until(service_called, timeout=3.0), "IntuneService.create_intunewin should be called"

                 # 6. Verify Output
                 def status_updated():
                     # Check value for Success message
                     val = view.pkg_status.value or ""
                     return "Success" in val

                 assert poll_until(status_updated, timeout=3.0), f"Package status should verify success. Current: {view.pkg_status.value}"

if __name__ == "__main__":
    pytest.main([__file__])
