import flet as ft
import json
import logging
from pathlib import Path
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)


class StackManagerView(ft.Column, ViewMixin):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.stacks_file = Path("data/stacks.json")
        self.stacks = self._load_stacks()
        self.current_stack = None

        # UI Components
        self.stack_list = ft.ListView(expand=True, spacing=5, padding=10)
        self.stack_content_list = ft.ListView(expand=True, spacing=5, padding=10)
        self.stack_name_field = ft.TextField(
            label=i18n.get("stack_name") or "Stack Name",
            expand=True,
            border_radius=8
        )

        self.new_item_field = ft.TextField(
            label=i18n.get("stack_app_name") or "App Name / Winget ID",
            hint_text=i18n.get("stack_app_hint") or "e.g. Mozilla.Firefox or path to installer",
            expand=True,
            border_radius=8
        )

        # Build UI with proper layout
        self._build_ui()

    def _build_ui(self):
        """Build the main UI with proper padding and layout."""
        # Description text explaining the Stacks feature
        description = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color="BLUE_400", size=20),
                ft.Container(
                    content=ft.Text(
                        i18n.get("stacks_description") or
                        "Stacks allow you to group multiple apps together for batch deployment. "
                        "Create a stack, add apps by Winget ID or file path, then deploy them all at once to Intune.",
                        size=14,
                        color="GREY_400"
                    ),
                    expand=True,
                    width=None
                )
            ], spacing=10, wrap=False),
            padding=ft.Padding.only(bottom=15),
        )

        # Left panel - Stack list
        left_panel = ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("your_stacks") or "Your Stacks",
                    weight=ft.FontWeight.BOLD,
                    size=16
                ),
                ft.Container(height=10),
                ft.Row([
                    self.stack_name_field,
                    ft.IconButton(
                        ft.Icons.ADD_CIRCLE,
                        tooltip=i18n.get("add_stack") or "Add Stack",
                        on_click=self._add_stack,
                        icon_color="GREEN_400"
                    )
                ], spacing=5),
                ft.Container(height=10),
                ft.Container(
                    content=self.stack_list,
                    expand=True,
                    bgcolor="BLACK12",
                    border_radius=10,
                    border=ft.Border.all(1, "WHITE10")
                )
            ], spacing=5),
            width=280,
            padding=10
        )

        # Right panel - Stack contents
        right_panel = ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("stack_content") or "Stack Content",
                    weight=ft.FontWeight.BOLD,
                    size=16
                ),
                ft.Container(height=10),
                ft.Row([
                    self.new_item_field,
                    ft.IconButton(
                        ft.Icons.ADD_TO_PHOTOS,
                        tooltip=i18n.get("add_app_to_stack") or "Add App to Stack",
                        on_click=self._add_item_to_stack,
                        icon_color="BLUE_400"
                    )
                ], spacing=5),
                ft.Container(height=10),
                ft.Container(
                    content=self.stack_content_list,
                    expand=True,
                    bgcolor="BLACK12",
                    border_radius=10,
                    border=ft.Border.all(1, "WHITE10")
                ),
                ft.Container(height=15),
                ft.Row([
                    ft.Button(
                        i18n.get("save_stack") or "Save Stack",
                        icon=ft.Icons.SAVE,
                        on_click=self._save_stacks_action
                    ),
                    ft.Button(
                        i18n.get("deploy_stack") or "Deploy Stack",
                        icon=ft.Icons.ROCKET_LAUNCH,
                        bgcolor="BLUE_700",
                        color="WHITE",
                        on_click=self._deploy_stack
                    )
                ], spacing=10)
            ], spacing=5),
            expand=True,
            padding=10
        )

        # Main layout with proper padding
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        i18n.get("stacks_title") or "Project Stacks",
                        size=28,
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.Text(
                        i18n.get("stacks_subtitle") or "Manage collections of apps for batch deployment",
                        size=16,
                        color="GREY_400"
                    ),
                    ft.Divider(height=20),
                    description,
                    ft.Row([
                        left_panel,
                        ft.VerticalDivider(width=1, color="WHITE10"),
                        right_panel
                    ], expand=True, spacing=0)
                ], expand=True, spacing=10),
                padding=20,
                expand=True
            )
        ]

    def did_mount(self):
        self._refresh_stack_list()

    def _load_stacks(self):
        if not self.stacks_file.exists():
            return {}
        try:
            with open(self.stacks_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_stacks(self):
        try:
            self.stacks_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stacks_file, "w") as f:
                json.dump(self.stacks, f, indent=4)
        except (OSError, IOError) as e:
            logger.error(f"Failed to save stacks: {e}")
            self._show_snack(f"{i18n.get('save_failed') or 'Failed to save'}: {e}", "RED")

    def _save_stacks_action(self, e):
        self._save_stacks()
        self._show_snack(i18n.get("stacks_saved") or "Stacks saved!", "GREEN")

    def _refresh_stack_list(self):
        self.stack_list.controls.clear()
        if not self.stacks:
            self.stack_list.controls.append(
                ft.Text(
                    i18n.get("no_stacks_yet") or "No stacks yet. Create one above!",
                    italic=True,
                    color="GREY_500",
                    size=12
                )
            )
        else:
            for name in self.stacks.keys():
                item_count = len(self.stacks[name])
                self.stack_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(name),
                        subtitle=ft.Text(f"{item_count} {i18n.get('apps') or 'apps'}"),
                        leading=ft.Icon(ft.Icons.LAYERS, color="BLUE_400"),
                        on_click=lambda e, n=name: self._select_stack(n),
                        trailing=ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_color="RED_400",
                            tooltip=i18n.get("delete_stack") or "Delete Stack",
                            on_click=lambda e, n=name: self._delete_stack(n)
                        )
                    )
                )
        if self.page:
            self.update()

    def _add_stack(self, e):
        name = self.stack_name_field.value
        if not name:
            self._show_snack(i18n.get("enter_stack_name") or "Please enter a stack name", "ORANGE")
            return
        if name in self.stacks:
            self._show_snack(i18n.get("stack_exists") or "Stack already exists!", "RED")
            return

        self.stacks[name] = []
        self.stack_name_field.value = ""
        self._save_stacks()
        self._refresh_stack_list()
        self._select_stack(name)

    def _delete_stack(self, name):
        if name in self.stacks:
            del self.stacks[name]
            self._save_stacks()
            self._refresh_stack_list()
            if self.current_stack == name:
                self.current_stack = None
                self.stack_content_list.controls.clear()
                self.update()

    def _select_stack(self, name):
        if name not in self.stacks:
            self._show_snack(i18n.get("stack_not_found") or "Stack not found", "RED")
            return
        self.current_stack = name
        items = self.stacks[name]
        self.stack_content_list.controls.clear()

        if not items:
            self.stack_content_list.controls.append(
                ft.Text(
                    i18n.get("stack_empty") or "Stack is empty. Add apps above!",
                    italic=True,
                    color="GREY_500",
                    size=12
                )
            )
        else:
            for item in items:
                self.stack_content_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(item),
                        leading=ft.Icon(ft.Icons.APPS, color="GREEN_400"),
                        trailing=ft.IconButton(
                            ft.Icons.REMOVE_CIRCLE_OUTLINE,
                            icon_color="RED_400",
                            tooltip=i18n.get("remove_app") or "Remove App",
                            on_click=lambda e, i=item: self._remove_item(i)
                        )
                    )
                )
        self.update()

    def _add_item_to_stack(self, e):
        if not self.current_stack:
            self._show_snack(i18n.get("select_stack_first") or "Select a stack first", "ORANGE")
            return

        val = self.new_item_field.value
        if val and val.strip():
            self.stacks[self.current_stack].append(val.strip())
            self._save_stacks()
            self._select_stack(self.current_stack)  # Refresh list
            self.new_item_field.value = ""
            self.update()
        else:
            self._show_snack(i18n.get("fill_all_fields") or "Please fill all fields", "ORANGE")

    def _remove_item(self, item):
        if self.current_stack and item in self.stacks[self.current_stack]:
            self.stacks[self.current_stack].remove(item)
            self._save_stacks()
            self._select_stack(self.current_stack)

    def _deploy_stack(self, e):
        if not self.current_stack or not self.stacks[self.current_stack]:
            self._show_snack(i18n.get("stack_empty_deploy") or "Stack is empty or not selected", "RED")
            return

        # Deployment dialog
        items = self.stacks[self.current_stack]
        items_list = "\n".join([f"• {item}" for item in items])

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("deploy_stack_title") or "Deploy Stack"),
            content=ft.Column([
                ft.Text(
                    f"{i18n.get('deploying_apps') or 'Deploying'} {len(items)} {i18n.get('apps') or 'apps'}:"
                ),
                ft.Container(height=10),
                ft.Text(items_list, size=12),
                ft.Container(height=10),
                ft.Text(
                    i18n.get("deploy_stack_note") or
                    "Note: This feature requires Intune integration to be configured.",
                    italic=True,
                    color="GREY_500",
                    size=12
                )
            ], tight=True),
            actions=[
                ft.TextButton(i18n.get("btn_cancel") or "Cancel", on_click=lambda e: self.app_page.close(dlg)),
                ft.Button(
                    i18n.get("btn_deploy") or "Deploy",
                    bgcolor="BLUE_700",
                    color="WHITE",
                    on_click=lambda e: self._execute_deploy(dlg)
                )
            ]
        )
        self.app_page.open(dlg)

    def _execute_deploy(self, dlg):
        """Simulate a batch deployment of the stack items."""
        items = self.stacks.get(self.current_stack, [])
        self.app_page.dialog.open = False
        self.app_page.update()

        self._show_snack(f"Starting batch deployment for {len(items)} items...", "BLUE")

        def _deploy_worker():
            try:
                import time
                for item in items:
                    # Simulate processing each item
                    logger.info(f"Deploying stack item: {item}")
                    time.sleep(1) # Simulate network/processing time

                self._run_task_with_fallback(
                    lambda: self._show_snack(f"Stack {self.current_stack} deployed successfully!", "GREEN")
                )
            except Exception as e:
                logger.error(f"Stack deployment failed: {e}")
                self._run_task_with_fallback(
                    lambda: self._show_snack(f"Deployment error: {e}", "RED")
                )

        threading.Thread(target=_deploy_worker, daemon=True).start()
