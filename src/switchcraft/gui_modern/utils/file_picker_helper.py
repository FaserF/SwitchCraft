import sys

class FilePickerHelper:
    """
    A helper class to replace Flet's FilePicker with Tkinter's native dialogs.
    This avoids issues with Flet versions where FilePicker is not recognized or buggy.
    NOTE: NOT compatible with Web implementations (Docker/Browser).
    """

    @staticmethod
    def _get_tkinter():
        # Skip tkinter entirely on non-Windows to avoid shared library errors in Docker
        if sys.platform != 'win32':
            return None, None
        try:
            import tkinter
            from tkinter import filedialog
            return tkinter, filedialog
        except ImportError:
            return None, None
        except Exception as e:
            # e.g. TclError: no display name and no $DISPLAY environment variable
            print(f"Tkinter unavailable: {e}")
            return None, None

    @staticmethod
    def pick_file(allowed_extensions: list[str] = None, allow_multiple: bool = False):
        """
        Open a file selection dialog.
        :param allowed_extensions: List of extensions e.g. ['exe', 'msi']
        :param allow_multiple: Whether to allow multiple files (returns list)
        :return: Path string (or list of strings), or None if cancelled.
        """
        tk, filedialog = FilePickerHelper._get_tkinter()
        if not tk or not filedialog:
            print("FilePickerHelper: Tkinter not available (Web/Headless mode?)")
            return None

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        filetypes = []
        if allowed_extensions:
            # Tkinter expects ("Name", "*.ext")
            exts = [f"*.{e}" for e in allowed_extensions]
            filetypes.append(("Allowed Files", " ".join(exts)))
            filetypes.append(("All Files", "*.*"))

        try:
            if allow_multiple:
                result = filedialog.askopenfilenames(filetypes=filetypes)
                return list(result) if result else None
            else:
                result = filedialog.askopenfilename(filetypes=filetypes)
                return result if result else None
        finally:
            try:
                root.destroy()
            except:
                pass

    @staticmethod
    def pick_directory():
        """
        Open a directory selection dialog.
        :return: Directory path or None.
        """
        tk, filedialog = FilePickerHelper._get_tkinter()
        if not tk or not filedialog:
             print("FilePickerHelper: Tkinter not available")
             return None

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        try:
            result = filedialog.askdirectory()
            return result if result else None
        finally:
            try:
                root.destroy()
            except:
                pass

    @staticmethod
    def save_file(dialog_title: str = "Save File", file_name: str = "untitled", allowed_extensions: list[str] = None, initial_directory: str = None):
        """
        Open a save file dialog.
        :return: Path or None.
        """
        tk, filedialog = FilePickerHelper._get_tkinter()
        if not tk or not filedialog:
             print("FilePickerHelper: Tkinter not available")
             return None

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Prepare defaultextension
        defaultext = ""
        filetypes = []
        if allowed_extensions:
            defaultext = f".{allowed_extensions[0]}"
            exts = [f"*.{e}" for e in allowed_extensions]
            filetypes.append(("Allowed Files", " ".join(exts)))
            filetypes.append(("All Files", "*.*"))

        try:
            result = filedialog.asksaveasfilename(
                title=dialog_title,
                initialfile=file_name,
                initialdir=initial_directory,
                defaultext=defaultext,
                filetypes=filetypes
            )
            return result if result else None
        finally:
             try:
                root.destroy()
             except:
                pass
