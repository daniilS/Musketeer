import ctypes
import importlib.resources as res
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from tkinter import font

import ttkbootstrap

from . import __version__
from . import windowsHighDpiPatch
from .style import padding

try:
    appId = "daniilS.musketeer"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
except Exception:
    pass


fullErrorMessages = True
olderror = mb.showerror


# TODO: convert to simple error message, with an option to expand to the full one
def newshowerror(title, message, *args, **kwargs):
    import traceback

    if fullErrorMessages and isinstance(message, Exception):
        if root._windowingsystem == "aqua":
            # MacOS alert windows don't have a title, and "-icon warning" maps to a
            # higher priority alert than "-icon error".
            return mb.showwarning(
                title,
                f"{title}:\n\n{traceback.format_exception(message)[-1]}",
                detail="".join(traceback.format_exception(message, limit=-8)[:-1]),
                *args,
                **kwargs,
            )
        else:
            return olderror(
                title,
                traceback.format_exception(message)[-1],
                detail="".join(traceback.format_exception(message, limit=-8)[:-1]),
                *args,
                **kwargs,
            )
    else:
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
root.title(f"Musketeer {__version__}")


# notes on preferred icon size on Windows:
# title bar: prefers 16px, actual size 16px (or 24px at 1.5x scaling)
# if the icon set without calling update() first, the title bar also prefers 32, but
# will be blurry
# task bar: prefers 32px, actual size 24px (or 36px at 1.5x scaling)
# if the preferred size is not provided, the first file provided will be used
# the least common multiple of 16, 24, and 36 is 144, but using that causes the title
# bar icon to be blurry
# 48px seems to give the best quality at all scaling factors

# on Linux, tk documentation recommends providing no more than 2 icons, placing the
# largest one first
# on MacOS, only the first icon is used, and it is recommended to provide as large an
# icon as possible

try:
    try:
        iconData48 = (res.files(__package__) / "logo 48px.png").read_bytes()
        iconData512 = (res.files(__package__) / "logo 512px.png").read_bytes()
    except AttributeError:
        # Python 3.8 compatibility
        iconData48 = res.read_binary(__package__, "logo 48px.png")
        iconData512 = res.read_binary(__package__, "logo 512px.png")
    icon48 = tk.PhotoImage(data=iconData48)
    icon512 = tk.PhotoImage(data=iconData512)

    if root._windowingsystem == "win32":
        # Call before update to make sure the icon appears straight away (otherwise the
        # default Tk icon may appear for a few seconds first). Call after update is
        # necessary to make the title bar icon not blurry.
        root.iconphoto(True, icon48, icon512)
        root.update()
        root.iconphoto(True, icon48, icon512)
    else:
        root.iconphoto(True, icon512, icon48)
except Exception:
    # Should currently never happen, but if anything changes about the API in
    # the future, we can survive without an icon.
    pass
frame = ttk.Frame(root, padding=padding)
frame.pack(expand=True, fill="both")


# Especially on the first startup, when matplotlib needs to build the font cache,
# importing everything may take a while. So we defer all other imports until now.
root.tk.eval("tk busy .")
root.update()

from pathlib import PurePath

import numpy as np
from ttkbootstrap.widgets import InteractiveNotebook

from . import patchMatplotlib
from .style import defaultFigureParams, figureParams
from .table import ButtonFrame
from .titration import Titration
from .titrationFrame import TitrationFrame

patchMatplotlib.applyPatch()


class DpiPopup(tk.Toplevel):
    def __init__(self, master, saveCallback, *args, **kwargs):
        super().__init__(
            master,
            padx=padding,
            pady=padding,
            *args,
            **kwargs,
        )
        self.title("Change figure DPI")
        self.resizable(False, False)
        self.saveCallback = saveCallback

        scaleLabel = ttk.Label(self, text="Scale:", justify="left", state="normal")
        scaleLabel.grid(row=0, column=0, sticky="ew")

        self.scaleDropdown = ttk.Combobox(
            self,
            values=[f"{i}%" for i in [60, 80, 100, 125, 150, 200]],
            justify="right",
            width=5,
        )
        self.scaleDropdown.grid(row=0, column=2, sticky="ew")

        resLabel = ttk.Label(self, text="Resolution:", justify="left")
        resLabel.grid(row=1, column=0, sticky="ew")

        self.resDropdown = ttk.Combobox(
            self,
            values=[
                f"{int(y*4/3)} x {y}" for y in [240, 360, 480, 600, 960, 1200, 1440]
            ],
            justify="right",
            width=10,
            state="readonly",
        )
        self.resDropdown.grid(row=1, column=2, sticky="ew")

        self.rowconfigure(0, pad=10)
        self.rowconfigure(1, pad=10)

        self.columnconfigure(0, pad=10)
        self.columnconfigure(1, weight=1)

        self.initValues()

        buttonFrame = ButtonFrame(self, self.reset, self.save, self.destroy)
        buttonFrame.saveButton.configure(text="Save")

        buttonFrame.applyButton = ttk.Button(
            buttonFrame, text="Apply", command=self.apply, style="success.TButton"
        )
        buttonFrame.applyButton.pack(
            side="right", after=buttonFrame.saveButton, padx=padding
        )

        buttonFrame.grid(row=2, column=0, columnspan=3, sticky="esw")

    def reset(self):
        self.scaleDropdown.set(f"{defaultFigureParams['scale']}%")
        self.resDropdown.set(f"{defaultFigureParams['x']} x {defaultFigureParams['y']}")

    def initValues(self):
        self.scaleDropdown.set(f"{figureParams['scale']}%")
        self.resDropdown.set(f"{figureParams['x']} x {figureParams['y']}")

    def save(self):
        if self.apply():  # returns False if failed to apply
            self.destroy()

    def apply(self):
        try:
            scale = int(self.scaleDropdown.get().strip("%"))
            x, y = [int(i) for i in self.resDropdown.get().split(" x ")]
            figureParams.update(scale=scale, x=x, y=y)
            self.saveCallback()
            return True
        except Exception as e:
            mb.showerror(title="Could not apply settings", message=e, parent=self)
            return False


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

        editMenu = tk.Menu(self.menuBar, tearoff=False)
        self.menuBar.add_cascade(label="Edit", menu=editMenu, underline=0)
        editMenu.add_command(
            label="Change figure DPI", command=self.editDpi, underline=0
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
        titration = Titration("Fit 1")
        titration.rawData = np.empty((0, 0))

        titrationFrame = TitrationFrame(self, padding=padding)
        self.add(titrationFrame, text="New Titration", sticky="nesw")
        self.select(str(titrationFrame))
        titrationFrame.loadTitration(titration)

    def saveFile(self, *args):
        self.nametowidget(self.select()).saveFile()

    def saveFileAs(self, *args):
        self.nametowidget(self.select()).saveFile(saveAs=True)

    def openFile(self, *args):
        filePath = fd.askopenfilename(
            title="Open file",
            filetypes=[("Musketeer files", "*.fit"), ("All files", "*.*")],
        )
        if filePath == "":
            return

        try:
            titration = np.load(filePath, allow_pickle=False)
        except Exception as e:
            mb.showerror(title="Failed to read file", message=e, parent=self)
            return

        self.tk.eval("tk busy .")
        self.update()

        titrationFrame = TitrationFrame(self, filePath, padding=padding)
        self.add(titrationFrame, text=PurePath(filePath).name, sticky="nesw")
        self.select(str(titrationFrame))
        titrationFrame.loadTitration(titration)

        self.tk.eval("tk busy forget .")

    def editDpi(self, *args):
        popup = DpiPopup(self, self.updateDpi)
        popup.withdraw()
        self.update()
        root = self.winfo_toplevel()
        x = root.winfo_x() + root.winfo_width() / 2 - popup.winfo_width() / 2
        y = root.winfo_y() + root.winfo_height() / 2 - popup.winfo_height() / 2
        popup.geometry(f"+{int(x)}+{int(y)}")
        popup.transient(self)
        popup.grab_set()
        popup.deiconify()
        popup.wait_window()

    def updateDpi(self):
        for tab in self.tabs():
            try:
                self.nametowidget(tab).updateDpi()
            except AttributeError:
                pass

        self.update()


notebook = TitrationsNotebook(frame)
notebook.pack(expand=True, fill="both")

root.tk.eval("tk busy forget .")
root.mainloop()
