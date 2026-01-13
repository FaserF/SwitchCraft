import flet as ft
import time
import threading

class SkeletonContainer(ft.Container):
    """
    A container that displays a pulsing skeleton loading effect.
    """
    def __init__(self, width=None, height=None, border_radius=5, expand=False):
        super().__init__(
            width=width,
            height=height,
            border_radius=border_radius,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            expand=expand,
            animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.aborted = False

    def did_mount(self):
        self._animate()

    def will_unmount(self):
        self.aborted = True

    def _animate(self):
        if self.aborted:
            return

        # Simple pulsing opacity animation
        self.opacity = 0.5 if self.opacity == 1.0 else 1.0
        self.update()

        # Schedule next frame
        if not self.aborted:
            # We can't use time.sleep in main thread or it blocks.
            # But creating threads for every skeleton might be heavy.
            # Flet animations handle the transition, we just need to toggle states.
            # We can use a delayed timer if available, or a background thread loop for the signal.
            # Since Flet doesn't have a built-in "setInterval" exposed easily to controls without page,
            # we rely on the animation completion.
            # However, Flet doesn't have an "on_animation_end" event for individual controls easily accessible here.
            # A simple background thread loop for the life of the component is one way,
            # but let's try a safer recursive threading approach to avoid blocking.

            def _loop():
                time.sleep(0.8)
                if not self.aborted:
                    self._animate()

            threading.Thread(target=_loop, daemon=True).start()
