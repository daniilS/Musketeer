import tkinter as tk
import tkinter.ttk as ttk
import os

from ttkbootstrap import Style
import matplotlib.pyplot as plt

from . import titrationReader
from .style import padding


# need to keep a reference to the Style object so that image-based widgets
# appear correctly
ttkStyle = Style(theme="lumen")
root = ttkStyle.master

try:
    # Windows and OS X
    root.state("zoomed")
except tk.TclError:
    # X11
    root.attributes("-zoomed", True)
root.title("Musketeer")

try:
    import ctypes
    myappid = u'daniilS.musketeer'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:  # noqa
    pass

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
    titration.frame = ttk.Frame(notebook, padding=padding)
    notebook.add(titration.frame, text="Titration", sticky="nesw")
    titration.populateFrame()


def closePlots():
    plt.close("all")
    root.destroy()


# temporary workaround to prevent embedded matplotlib plots from keeping the
# mainloop running
root.protocol("WM_DELETE_WINDOW", closePlots)
root.mainloop()
