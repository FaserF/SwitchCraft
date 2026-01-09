
import tkinter
from tkinter import filedialog
import os

class FilePickerHelper:
    """
    A helper class to replace Flet's FilePicker with Tkinter's native dialogs.
    This avoids issues with Flet versions where FilePicker is not recognized or buggy.
    """

    @staticmethod
    def pick_file(allowed_extensions: list[str] = None, allow_multiple: bool = False):
        """
        Open a file selection dialog.
        :param allowed_extensions: List of extensions e.g. ['exe', 'msi']
        :param allow_multiple: Whether to allow multiple files (returns list)
        :return: Path string (or list of strings), or None if cancelled.
        """
        root = tkinter.Tk()
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
            root.destroy()

    @staticmethod
    def pick_directory():
        """
        Open a directory selection dialog.
        :return: Directory path or None.
        """
        root = tkinter.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        try:
            result = filedialog.askdirectory()
            return result if result else None
        finally:
            root.destroy()

    @staticmethod
    def save_file(dialog_title: str = "Save File", file_name: str = "untitled", allowed_extensions: list[str] = None, initial_directory: str = None):
        """
        Open a save file dialog.
        :return: Path or None.
        """
        root = tkinter.Tk()
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
            root.destroy()
