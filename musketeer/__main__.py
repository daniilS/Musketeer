import tkinter as tk
import tkinter.ttk as ttk
import os
import ctypes

from ttkbootstrap import Style
import matplotlib.pyplot as plt

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
ttkStyle = Style(theme="lumen")
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

fileReader = titrationReader.getFileReader()
filePath = titrationReader.getFilePath()
titrations = fileReader(filePath)

notebook = ttk.Notebook(frame, padding=padding)
notebook.pack(expand=True, fill="both")

# create a tab for each titration, and let the titration object handle its
# own I/O
for titration in titrations:
    titrationFrame = TitrationFrame(notebook, titration, padding=padding)
    notebook.add(titrationFrame, text="Titration", sticky="nesw")


def closePlots():
    plt.close("all")
    root.destroy()


# temporary workaround to prevent embedded matplotlib plots from keeping the
# mainloop running
root.protocol("WM_DELETE_WINDOW", closePlots)
root.mainloop()
