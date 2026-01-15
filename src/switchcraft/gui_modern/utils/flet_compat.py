
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
    except TypeError as te:
        # Fallback for environments where Tabs requires content/length (e.g. tests)
        logger.debug(f"Standard Tabs failed (likely compat mode needed): {te}")
        try:
            # Check if TabBar exists
            if hasattr(ft, "TabBar"):
                # Flet 0.80+ style: Tabs is just a wrapper, or we manually build Column
                # If Tabs() requires 'tabs' and fails, it means we probably need to separate TabBar and View.
                # However, returning a simple ft.Column simulating Tabs is safer if Tabs is broken/changed.

                # Extract children (content) from Tabs if possible, usually Tabs.tabs[i].content
                # But here we are creating it.
                tab_contents = []
                for t in (tabs or []):
                    if hasattr(t, "content"):
                        tab_contents.append(t.content)
                    else:
                        tab_contents.append(ft.Container()) # Empty placeholder

                # Create a Column with TabBar and the content view (TabBarView not strict req if we manage visibility?)
                # Actually, standard pattern is Column([TabBar, Expanded(TabBarView)])
                # But we can just return a Column that acts as the container.

                # We need to ensure logic works. Tabs usually handles switching.
                # If we return a Column, existing code might expect .tabs property.
                # But standard Flet Tabs has .tabs.

                # Let's try to construct a valid ft.Tabs via kwargs, matching 0.80.1 requirement:
                # ft.Tabs(selected_index=..., animation_duration=..., tabs=[...], expand=...)
                # If that failed above (TypeError), it implies signature mismatch.

                # Re-try assuming it's the `content` argument issue or similar.
                # If we really need a fallback:

                length = len(tabs) if tabs else 0
                return ft.Tabs(content=ft.TabBar(tabs=tabs), length=length, **kwargs)
            else:
                # No TabBar, maybe properties assignment?
                t = ft.Tabs(**kwargs)
                if tabs is not None:
                    t.tabs = tabs
                return t
        except Exception as e:
            logger.error(f"Failed to create compat Tabs: {e}")
            raise
