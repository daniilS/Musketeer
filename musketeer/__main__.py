import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from tkinter import font
import ctypes

import ttkbootstrap
from ttkbootstrap.widgets import InteractiveNotebook
import importlib.resources as res
import numpy as np

from . import titrationReader, patchMatplotlib, windowsHighDpiPatch
from .titration import Titration
from .titrationFrame import TitrationFrame
from .style import padding

patchMatplotlib.applyPatch()
try:
    appId = "daniilS.musketeer"
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
root.geometry("1000x600")

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
            newtab=self.newFile,
            style="Flat.Interactive.TNotebook",
            *args,
            **kwargs,
        )
        self.createMenuBar()
        self.createQuickStartMenu()
        self.select(str(self._newtab_frame))

    def forget(self, index, *args, **kwargs):
        # Manually change to a different tab before a tab is closed, to prevent the
        # quickstart menu from appearing briefly right after a tab is closed but before
        # the next tab has been selected
        next_tab = index + 1
        if (
            self._has_newtab_button and next_tab == self._last_tab
        ) or index == self._last_tab:
            next_tab = index - 1
        if 0 <= next_tab <= self._last_tab:
            self.select(next_tab)
        return super().forget(index, *args, **kwargs)

    def createQuickStartMenu(self):
        self.quickStartFrame = ttk.Frame(self)
        self.quickStartFrame.pack(expand=True, fill="none")

        self.quickStartFont = font.nametofont("TkTextFont").copy()
        self.quickStartFont["size"] = round(self.quickStartFont["size"] * 1.33)
        ttkStyle.configure("large.success.TButton", font=self.quickStartFont)
        ttkStyle.configure("large.TButton", font=self.quickStartFont)

        self.newFileButton = ttk.Button(
            self.quickStartFrame,
            text="Create a new fit file",
            command=self.newFile,
            style="large.success.TButton",
        )
        self.newFileButton.pack(fill="x")
        self.orLabel = ttk.Label(
            self.quickStartFrame, text="or", font=self.quickStartFont
        )
        self.orLabel.pack(pady=5)
        self.OpenFileButton = ttk.Button(
            self.quickStartFrame,
            text="Open an existing file",
            command=self.openFile,
            style="large.TButton",
        )
        self.OpenFileButton.pack(fill="x")

    def createMenuBar(self):
        self.menuBar = tk.Menu(self, tearoff=False)

        fileMenu = tk.Menu(self.menuBar, tearoff=False)
        self.menuBar.add_cascade(label="File", menu=fileMenu, underline=0)

        self.addMenuCommand(fileMenu, "New", self.newFile)
        self.addMenuCommand(fileMenu, "Open", self.openFile)
        self.addMenuCommand(fileMenu, "Save", self.saveFile)
        self.addMenuCommand(
            fileMenu, "Save As", self.saveFileAs, keys=("Shift", "s"), underline=5
        )

        self.winfo_toplevel().config(menu=self.menuBar)

    def addMenuCommand(self, fileMenu, label, command, keys=None, underline=0):
        if self._windowingsystem == "aqua":
            accelerator = "Command"
            key = accelerator
        else:
            accelerator = "Ctrl"
            key = "Control"

        if keys is None:
            keys = (label[0].lower(),)

        fileMenu.add_command(
            label=label,
            command=command,
            accelerator=f"{accelerator}+{'+'.join(keys).title()}",
            underline=underline,
        )
        self.winfo_toplevel().bind(f"<{key}-{'-'.join(keys)}>", command)

    def newFile(self, *args):
        titration = Titration("New Titration")
        titration.rawData = np.empty((0, 0))
        titration.continuous = False

        titrationFrame = TitrationFrame(self, titration, padding=padding)
        self.add(titrationFrame, text=titration.title, sticky="nesw")
        self.select(str(titrationFrame))

    def saveFile(self, *args):
        self.nametowidget(self.select()).saveFile()

    def saveFileAs(self, *args):
        self.nametowidget(self.select()).saveFile(saveAs=True)

    def openFile(self, *args):
        fileType = tk.StringVar(self)
        fileReaders = titrationReader.fileReaders
        filePath = fd.askopenfilename(
            title="Open file",
            filetypes=fileReaders[:, :-1].tolist(),
            typevariable=fileType,
        )
        if filePath == "":
            return
        fileReader = fileReaders[fileReaders[:, 0] == fileType.get(), -1].item()
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

root.mainloop()
