import flet as ft
from switchcraft.utils.config import SwitchCraftConfig


def ModernSettingsView(page: ft.Page):
    """Settings View."""

    # Storage for text fields to save later
    text_fields = []

    def create_switch(key, label, default):
        val = SwitchCraftConfig.get_value(key, default)

        def on_change(e):
            SwitchCraftConfig.set_value(key, e.control.value)
            page.show_snack_bar(ft.SnackBar(ft.Text(f"Saved {label}")))

        return ft.Switch(label=label, value=bool(val), on_change=on_change)

    def create_input(key, label, password=False):
        if password:
            val = SwitchCraftConfig.get_secure_value(key) or ""
        else:
            val = SwitchCraftConfig.get_value(key) or ""

        field = ft.TextField(label=label, value=str(val), password=password, can_reveal_password=password)
        text_fields.append((key, field, password))
        return field

    def save_all(e):
        count = 0
        for key, field, is_secure in text_fields:
            value = field.value
            if is_secure:
                SwitchCraftConfig.set_secure_value(key, value)
            else:
                SwitchCraftConfig.set_value(key, value)
            count += 1

        page.show_snack_bar(ft.SnackBar(ft.Text("Settings Saved Successfully!"), bgcolor=ft.colors.GREEN))

    return ft.Container(
        content=ft.Column([
            ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),

            ft.Text("General", size=20, weight=ft.FontWeight.W_500, color=ft.colors.BLUE_400),
            create_switch("EnableWinget", "Enable Winget Integration", True),
            create_switch("CheckForUpdates", "Check for Updates on Startup", True),

            ft.Divider(),
            ft.Text("Intune / Microsoft Graph", size=20, weight=ft.FontWeight.W_500, color=ft.colors.BLUE_400),
            create_input("GraphTenantId", "Tenant ID"),
            create_input("GraphClientId", "Client ID"),
            create_input("GraphClientSecret", "Client Secret", password=True),

            ft.Divider(),
            ft.Text("Paths", size=20, weight=ft.FontWeight.W_500, color=ft.colors.BLUE_400),
            create_input("GitRepoPath", "Git Repository Path (for Intune Scripts)"),
            create_input("CustomTemplatePath", "Custom PowerShell Template Path"),

            ft.Divider(),
            ft.ElevatedButton("Save Settings", bgcolor=ft.colors.BLUE, color=ft.colors.WHITE, on_click=save_all)

        ], scroll=ft.ScrollMode.AUTO, expand=True),
        padding=20,
        expand=True
    )
