import tkinter as tk
import tkinter.ttk as ttk
import os
import ctypes

import ttkbootstrap
from ttkbootstrap.widgets import InteractiveNotebook
import matplotlib.pyplot as plt
import tkinter.messagebox as mb

from . import titrationReader, patchMatplotlib, windowsHighDpiPatch
from .titrationFrame import TitrationFrame
from .style import padding

patchMatplotlib.applyPatch()
try:
    appId = u'daniilS.musketeer'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
except:  # noqa
    pass


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

# should get the correct location no matter how the script is run
# TODO: consider using importlib_resources
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
iconPath = os.path.join(__location__, "logo small.png")
icon = tk.PhotoImage(file=iconPath)
root.iconphoto(True, icon)
frame = ttk.Frame(root, padding=padding)
frame.pack(expand=True, fill="both")


class TitrationsNotebook(InteractiveNotebook):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, padding=padding, newtab=self.readFile,
                         style="Flat.Interactive.TNotebook", *args, **kwargs)

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
            mb.showerror(title="Failed to read file", message=e,
                         parent=self)
            return

        # create a tab for each titration, and let the titration object handle
        # its own I/O
        for titration in titrations:
            titrationFrame = TitrationFrame(self, titration, padding=padding)
            self.add(titrationFrame, text=titration.title, sticky="nesw")


notebook = TitrationsNotebook(frame)
notebook.pack(expand=True, fill="both")
notebook.readFile()


def closePlots():
    plt.close("all")
    root.destroy()


# temporary workaround to prevent embedded matplotlib plots from keeping the
# mainloop running
root.protocol("WM_DELETE_WINDOW", closePlots)
root.mainloop()
