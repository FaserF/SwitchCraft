import unittest
from unittest.mock import MagicMock
import flet as ft
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

class TestParentChain(unittest.TestCase):
    def test_parent_chain(self):
        page = MagicMock(spec=ft.Page)
        # Verify instance check
        print(f"Is instance Page: {isinstance(page, ft.Page)}")

        # Helper to set parent (copying from conftest)
        def set_structure_recursive(ctrl, parent):
            try:
                ctrl.parent = parent
            except AttributeError:
                try:
                    ctrl._parent = parent
                except AttributeError:
                    pass

            try:
                ctrl._page = page
            except AttributeError:
                pass

            if hasattr(ctrl, 'controls') and ctrl.controls:
                for child in ctrl.controls:
                    set_structure_recursive(child, ctrl)
            if hasattr(ctrl, 'content') and ctrl.content:
                set_structure_recursive(ctrl.content, ctrl)

        # Create structure
        view = ft.Column()
        container = ft.Container(content=ft.ListView(controls=[ft.Column(controls=[ft.Button("Test")])]))
        view.controls.append(container)

        # Apply recursion
        set_structure_recursive(view, page)

        # Test traversal
        btn = container.content.controls[0].controls[0]
        print(f"Button: {btn}")
        print(f"Button Parent: {btn.parent}")
        print(f"Column Parent: {btn.parent.parent}")
        print(f"ListView Parent: {btn.parent.parent.parent}")
        print(f"Container Parent: {btn.parent.parent.parent.parent}")
        print(f"View Parent: {btn.parent.parent.parent.parent.parent}")

        try:
            p = btn.page
            print(f"Button Page: {p}")
        except Exception as e:
            print(f"Button Page Error: {e}")

if __name__ == '__main__':
    unittest.main()
