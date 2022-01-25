import tkinter as tk
import tkinter.ttk as ttk
import ctypes

import ttkbootstrap
from ttkbootstrap.widgets import InteractiveNotebook
import importlib.resources as res
import tkinter.messagebox as mb

from . import titrationReader, patchMatplotlib, windowsHighDpiPatch
from .titrationFrame import TitrationFrame
from .style import padding

patchMatplotlib.applyPatch()
try:
    appId = u"daniilS.musketeer"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
except Exception:
    pass


DEBUG = True
olderror = mb.showerror


def newshowerror(title, message, *args, **kwargs):
    import traceback

    if DEBUG and isinstance(message, Exception):
        message = traceback.format_exc()
    return olderror(title, message, *args, **kwargs)


mb.showerror = newshowerror


# need to keep a reference to the Style object so that image-based widgets
# appear correctly
ttkStyle = ttkbootstrap.Style(theme="lumen")
root = ttkStyle.master

windowsHighDpiPatch.setEnhancedDpiScaling(root)

try:
    # Windows and OS X
    root.state("zoomed")
except tk.TclError:
    # X11
    root.attributes("-zoomed", True)
root.title("Musketeer")

try:
    iconData = res.read_binary(__package__, "logo small.png")
    icon = tk.PhotoImage(data=iconData)
    root.iconphoto(True, icon)
except Exception:
    # Should currently never happen, but if anything changes about the API in
    # the future, we can survive without an icon.
    pass
frame = ttk.Frame(root, padding=padding)
frame.pack(expand=True, fill="both")


class TitrationsNotebook(InteractiveNotebook):
    def __init__(self, master, *args, **kwargs):
        super().__init__(
            master,
            padding=padding,
            newtab=self.readFile,
            style="Flat.Interactive.TNotebook",
            *args,
            **kwargs
        )

    def readFile(self):
        fileReader = titrationReader.getFileReader()
        if fileReader is None:
            return
        filePath = titrationReader.getFilePath()
        if filePath == "":
            return
        try:
            titrations = fileReader(filePath)
        except Exception as e:
            mb.showerror(title="Failed to read file", message=e, parent=self)
            return

        # create a tab for each titration, and let the titration object handle
        # its own I/O
        for titration in titrations:
            titrationFrame = TitrationFrame(self, titration, padding=padding)
            self.add(titrationFrame, text=titration.title, sticky="nesw")
            self.select(str(titrationFrame))


notebook = TitrationsNotebook(frame)
notebook.pack(expand=True, fill="both")
notebook.readFile()

root.mainloop()
