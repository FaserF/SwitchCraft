import flet as ft
import time
import threading
from switchcraft import IS_WEB

class SkeletonContainer(ft.Container):
    """
    A container that displays a pulsing skeleton loading effect.
    """
    def __init__(self, width=None, height=None, border_radius=5, expand=False):
        super().__init__(
            width=width,
            height=height,
            border_radius=border_radius,
            bgcolor="SURFACE_CONTAINER_HIGHEST",
            expand=expand,
            animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
        )
        self.aborted = False

    def did_mount(self):
        self._animate()

    def will_unmount(self):
        self.aborted = True

    def _animate(self):
        if hasattr(self, "_loop_started") and self._loop_started:
             return

        self._loop_started = True

        def _loop():
            while not self.aborted:
                # Simple pulsing opacity animation
                # Note: modifying properties from thread is generally safe in Flet if .update() handles it,
                # but idiomatic way is often page.run_task or similar.
                # Here we just toggle and update.
                if self.aborted:
                    break

                # Check control status before update if possible, or try/except
                try:
                    self.opacity = 0.5 if self.opacity == 1.0 else 1.0
                    self.update()
                except Exception:
                    # Control might be detached or page closed
                    break

                # Sleep in chunks to allow faster exit
                for _ in range(8): # 0.8s
                    if self.aborted:
                        break
                    time.sleep(0.1)

        if not IS_WEB:
            threading.Thread(target=_loop, daemon=True).start()
