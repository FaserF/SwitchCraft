import flet as ft
import logging

logger = logging.getLogger(__name__)

class ViewMixin:
    """Mixin for common view functionality."""

    def _show_snack(self, msg, color="GREEN"):
        """Show a snackbar message on the page."""
        try:
            # Check if self has app_page or page
            page = getattr(self, "app_page", getattr(self, "page", None))
            if not page:
                logger.debug("Cannot show snackbar: No page reference found")
                return

            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            if hasattr(page, "open"):
                page.open(page.snack_bar)
            else:
                page.snack_bar.open = True
                page.update()
        except Exception as e:
            logger.debug(f"Failed to show snackbar: {e}")
