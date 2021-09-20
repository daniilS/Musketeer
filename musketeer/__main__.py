import tkinter as tk
import tkinter.ttk as ttk
import os
import ctypes

from ttkbootstrap import Style
import matplotlib.pyplot as plt

from . import titrationReader, patchMatplotlib
from .titrationFrame import TitrationFrame
from .style import padding

patchMatplotlib.applyPatch()

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
    appId = u'daniilS.musketeer'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
except:  # noqa
    pass
try:
    # From Windows 10, version 1607 onwards, it's possible to set the high DPI
    # scaling mode to "System (Enhanced)" using this function. This makes the
    # GUI look less blurry on displays using a scaling factor above 100%.
    #
    # A proper solution would involve disabling system scaling and handling it
    # through the application instead. This would require setting the dpi
    # awareness context to -4, querying the current monitor's scaling factor,
    # using it with "tk scaling" (and updating it whenever a window is moved to
    # another display, and manually changing any elements in tk that aren't
    # automatically updated, such as the padding in widget styles, and widget
    # elements drawn as images. This does not seem worth it for now.
    #
    # Information on the syscall:
    # https://docs.microsoft.com/en-us/windows/win32/hidpi/dpi-awareness-context
    # https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext
    DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED = -5
    setThreadDpiAwarenessContext = \
        ctypes.windll.user32.SetThreadDpiAwarenessContext
    setThreadDpiAwarenessContext.argtypes = (ctypes.c_void_p,)
    setThreadDpiAwarenessContext.restype = ctypes.c_void_p
    setThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED)
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
    titrationFrame = TitrationFrame(notebook, titration, padding=padding)
    notebook.add(titrationFrame, text="Titration", sticky="nesw")


def closePlots():
    plt.close("all")
    root.destroy()


# temporary workaround to prevent embedded matplotlib plots from keeping the
# mainloop running
root.protocol("WM_DELETE_WINDOW", closePlots)
root.mainloop()
