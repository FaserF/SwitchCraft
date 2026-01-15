
import flet as ft
import logging

logger = logging.getLogger(__name__)

def create_tabs(tabs, **kwargs):
    """
    Create a Tabs control compatible with different Flet versions/environments.

    Tries standard ft.Tabs(tabs=...).
    Falls back to ft.Tabs(content=ft.TabBar(tabs=...), length=...) if needed.
    """
    try:
        # Standard Flet
        return ft.Tabs(tabs=tabs, **kwargs)
    except TypeError:
        # Fallback for environments where Tabs requires content/length (e.g. tests)
        try:
            # Check if TabBar exists
            if hasattr(ft, "TabBar"):
                # Move on_change to TabBar if present in kwargs, logic might be complex
                # But typically Tabs wraps TabBar properties.
                # However, if Tabs expects content, we give it TabBar.

                # Careful: kwargs might contain Tabs properties that TabBar also takes (selected_index, etc.)
                # But Tabs wrapper might expect them.

                return ft.Tabs(content=ft.TabBar(tabs=tabs), length=len(tabs), **kwargs)
            else:
                 # No TabBar, maybe properties assignment?
                 t = ft.Tabs(**kwargs)
                 t.tabs = tabs
                 return t
        except Exception as e:
            logger.error(f"Failed to create compat Tabs: {e}")
            raise
