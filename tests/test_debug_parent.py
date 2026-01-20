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
        self.assertIsInstance(page, ft.Page, "Mock page should be an instance of ft.Page")

        # Helper to set parent structure
        # Note: This differs from conftest.py's set_structure_recursive which uses weakref.ref(parent).
        # This test requires direct parent assignment (not weakref) to validate the parent chain.
        def set_structure_recursive(ctrl, parent):
            import weakref
            try:
                # Parent property expects a weakref logic internally usually,
                # but if we set _parent directly, it MUST be a weakref (callable)
                # because the property getter calls it: return self._parent()
                ctrl._parent = weakref.ref(parent)
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

        # Assert button exists
        self.assertIsNotNone(btn, "Button should exist")
        self.assertIsInstance(btn, ft.Button, "Button should be a Button instance")

        # Assert parent chain exists and has correct types
        self.assertIsNotNone(btn.parent, "Button should have a parent")
        self.assertIsInstance(btn.parent, ft.Column, "Button parent should be a Column")

        self.assertIsNotNone(btn.parent.parent, "Button parent.parent should exist")
        self.assertIsInstance(btn.parent.parent, ft.ListView, "Button parent.parent should be a ListView")

        self.assertIsNotNone(btn.parent.parent.parent, "Button parent.parent.parent should exist")
        self.assertIsInstance(btn.parent.parent.parent, ft.Container, "Button parent.parent.parent should be a Container")

        self.assertIsNotNone(btn.parent.parent.parent.parent, "Button parent.parent.parent.parent should exist")
        self.assertIsInstance(btn.parent.parent.parent.parent, ft.Column, "Button parent.parent.parent.parent should be a Column (view)")

        self.assertIsNotNone(btn.parent.parent.parent.parent.parent, "Button parent.parent.parent.parent.parent should exist")
        self.assertEqual(btn.parent.parent.parent.parent.parent, page, "Button parent.parent.parent.parent.parent should be the page")

        # Assert page resolution (let exceptions raise if there's an error)
        p = btn.page
        self.assertIsNotNone(p, "Button should have a page attribute")
        self.assertEqual(p, page, "Button page should be the expected Page object")

if __name__ == '__main__':
    unittest.main()
