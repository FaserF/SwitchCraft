import flet as ft
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StackManagerView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.stacks_file = Path("data/stacks.json")
        self.stacks = self._load_stacks()
        self.current_stack = None

        # UI Components
        self.stack_list = ft.ListView(expand=True, spacing=5)
        self.stack_content_list = ft.ListView(expand=True, spacing=5)
        self.stack_name_field = ft.TextField(label="Stack Name")

        self.new_item_field = ft.TextField(label="App Name / Path", expand=True)

        # Build UI
        self._refresh_stack_list()

        self.controls = [
            ft.Text("Project Stacks", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Manage collections of apps for batch deployment.", size=16, color="GREY"),
            ft.Divider(),
            ft.Row([
                # Left: Stack List
                ft.Container(
                    width=250,
                    content=ft.Column([
                        ft.Text("Your Stacks", weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.stack_name_field,
                            ft.IconButton(ft.Icons.ADD, on_click=self._add_stack)
                        ]),
                        ft.Container(content=self.stack_list, expand=True, bgcolor="BLACK26", border_radius=5)
                    ]),
                ),
                ft.VerticalDivider(width=1),
                # Right: Stack Details
                ft.Container(
                    expand=True,
                    content=ft.Column([
                        ft.Text("Stack Content", weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.new_item_field,
                            ft.IconButton(ft.Icons.ADD_TO_PHOTOS, tooltip="Add App", on_click=self._add_item_to_stack)
                        ]),
                        ft.Container(
                            content=self.stack_content_list, expand=True, bgcolor="BLACK26", border_radius=5
                        ),
                        ft.Row([
                            ft.ElevatedButton("Save Stack", icon=ft.Icons.SAVE, on_click=self._save_stacks_action),
                            ft.ElevatedButton(
                                "Deploy Stack (Simulated)", icon=ft.Icons.ROCKET_LAUNCH,
                                bgcolor="RED_700", color="WHITE", on_click=self._deploy_stack
                            )
                        ])
                    ])
                )
            ], expand=True)
        ]

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
            self._show_snack(f"Failed to save: {e}", "RED")

    def _save_stacks_action(self, e):
        self._save_stacks()
        self._show_snack("Stacks saved!", "GREEN")

    def _refresh_stack_list(self):
        self.stack_list.controls.clear()
        for name in self.stacks.keys():
            self.stack_list.controls.append(
                ft.ListTile(
                    title=ft.Text(name),
                    leading=ft.Icon(ft.Icons.LAYERS),
                    on_click=lambda e, n=name: self._select_stack(n),
                    trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda e, n=name: self._delete_stack(n))
                )
            )
        self.update()

    def _add_stack(self, e):
        name = self.stack_name_field.value
        if not name:
            return
        if name in self.stacks:
            self._show_snack("Stack exists!", "RED")
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
            self._show_snack("Selected stack not found", "RED")
            return
        self.current_stack = name
        items = self.stacks[name]
        self.stack_content_list.controls.clear()
        for item in items:
            self.stack_content_list.controls.append(
                ft.ListTile(
                    title=ft.Text(item),
                    leading=ft.Icon(ft.Icons.APPS),
                    trailing=ft.IconButton(
                        ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e, i=item: self._remove_item(i)
                    )
                )
            )
        self.update()

    def _add_item_to_stack(self, e):
        if not self.current_stack:
            self._show_snack("Select a stack first", "RED")
            return

        val = self.new_item_field.value
        if val:
            self.stacks[self.current_stack].append(val)
            self._save_stacks()
            self._select_stack(self.current_stack)  # Refresh list
            self.new_item_field.value = ""
            self.update()

    def _remove_item(self, item):
        if self.current_stack and item in self.stacks[self.current_stack]:
            self.stacks[self.current_stack].remove(item)
            self._save_stacks()
            self._select_stack(self.current_stack)

    def _deploy_stack(self, e):
        if not self.current_stack or not self.stacks[self.current_stack]:
            self._show_snack("Stack empty or not selected", "RED")
            return

        # Simulation
        items = ", ".join(self.stacks[self.current_stack])
        dlg = ft.AlertDialog(
            title=ft.Text("Deploying Stack"),
            content=ft.Text(
                f"Deploying {len(self.stacks[self.current_stack])} apps:\n{items}\n\n(This is a simulation placeholder)"
            ),
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
            pass
