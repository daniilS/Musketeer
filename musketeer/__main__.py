import ctypes
import importlib.resources as res
import sys
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from tkinter import font, scrolledtext
import traceback

import ttkbootstrap

from . import __version__
from . import windowsHighDpiPatch
from .progressDialog import ProgressDialog
from .style import padding
from .table import WrappedLabel

try:
    appId = "daniilS.musketeer"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
except Exception:
    pass


class ErrorDialog(tk.Toplevel):
    def __init__(self, root, excType, excValue, tb, *args, **kwargs):
        super().__init__(root, *args, **kwargs)
        self.withdraw()

        self.title("An error has occured")

        arrowRight = "⮞" if self._windowingsystem == "win32" else "▶"
        arrowDown = "⮟" if self._windowingsystem == "win32" else "▼"
        self.closedLabel = f"Show details {arrowRight}"
        self.openLabel = f"Show details {arrowDown}"

        if self._windowingsystem == "aqua":
            try:
                self.tk.call(
                    "::tk::unsupported::MacWindowStyle", "style", self, "moveableModal"
                )
            except Exception:
                pass
        elif self._windowingsystem == "x11":
            self.attributes("-type", "dialog")

        self.button = ttk.Button(
            self, text="OK", command=self.close, style="Outline.TButton"
        )
        self.button.pack(side="bottom", padx=padding, pady=padding)

        image = "::tk::icons::warning"
        if image not in self.image_names():
            image = None
        self.wrappedLabel = WrappedLabel(
            self,
            text=traceback.format_exception_only(excType, excValue)[-1],
            image=image,
            compound="left",
            anchor="center",
        )
        self.wrappedLabel.pack(padx=padding, pady=padding, fill="both", expand=False)

        self.detailsToggle = ttk.Checkbutton(
            self,
            text=self.closedLabel,
            style="textOnly.TCheckbutton",
            command=self.toggleDetails,
        )
        self.detailsToggle.expanded = False
        self.detailsToggle.state(["!alternate", "!selected"])

        self.detailsFrame = ttk.LabelFrame(
            self, labelwidget=self.detailsToggle, labelanchor="n"
        )
        self.detailsFrame.pack(padx=padding, pady=padding, fill="both", expand=True)

        tracebackText = "".join(traceback.format_exception(excType, excValue, tb))
        self.detailsText = scrolledtext.ScrolledText(
            self.detailsFrame,
            font="TkFixedFont",
            width=40,
            height=20,
        )
        self.detailsText.insert("end", tracebackText)
        self.detailsText.configure(state="disabled")
        self.detailsText.pack(fill="both", expand=True)

        self.update_idletasks()

        # A WrappedLabel only automatically updates its height when it receives a
        # <Configure> event, so force it to request a height based on the detailFrame's
        # width.
        self.wrappedLabel.setHeightFromWidth(self.detailsFrame.winfo_reqwidth())
        self.update_idletasks()

        self.collapsedFrameHeight = (
            self.detailsFrame.winfo_reqheight() - self.detailsText.winfo_reqheight()
        )
        self.minWidth, self.minHeight = (
            self.winfo_reqwidth(),
            self.winfo_reqheight() - self.detailsText.winfo_reqheight(),
        )
        x = int(root.winfo_x() + root.winfo_width() / 2 - self.minWidth / 2)
        y = int((root.winfo_y() + root.winfo_height()) * (1 / 3) - self.minHeight / 2)
        self.detailsText.forget()
        self.minsize(0, self.minHeight)
        self.geometry(f"{self.minWidth}x{self.minHeight}+{x}+{y}")

        self.deiconify()
        self.bell()
        self.wait_visibility()

        self.oldGrab = root.grab_current()
        self.grab_set()
        self.wm_protocol("WM_DELETE_WINDOW", self.close)

        self.transient(root)
        self.tkraise()  # otherwise window may only appear after the parent window receives a click
        self.button.focus_set()

    def close(self):
        if self.oldGrab is not None and self.oldGrab.winfo_exists():
            self.oldGrab.grab_set()
        self.destroy()

    def toggleDetails(self):
        self.detailsToggle.expanded = not self.detailsToggle.expanded

        if self.detailsToggle.expanded:
            self.detailsToggle.configure(text=self.openLabel)
            self.detailsText.pack(padx=padding, pady=padding, fill="both", expand=True)
            if self.detailsFrame.winfo_reqheight() > self.detailsFrame.winfo_height():
                self.geometry(
                    f"{self.winfo_width()}x{self.winfo_height() + self.detailsFrame.winfo_reqheight()-self.detailsFrame.winfo_height()}"
                )
        else:
            newHeight = self.winfo_height() - (
                self.detailsFrame.winfo_height() - self.collapsedFrameHeight
            )
            self.detailsToggle.configure(text=self.closedLabel)
            self.detailsText.forget()
            self.geometry(f"{self.winfo_width()}x{newHeight}")


class App(tk.Tk):
    def report_callback_exception(self, excType, excValue, tb):
        try:
            dialog = ErrorDialog(self, excType, excValue, tb)
            self.wait_window(dialog)
        except Exception as e:
            title = "Fatal error"
            message = "While attempting to display an error message, another error occured. To resolve this issue, please report it on the Musketeer GitHub page."
            if self._windowingsystem == "aqua":
                # MacOS alert windows don't have a title, and "-icon warning" maps to a
                # higher priority alert than "-icon error".
                mb.showwarning(title, f"{title}:\n\n{message}", detail=str(e))
            else:
                mb.showerror(title, message, detail=str(e))


# need to keep a reference to the Style object so that image-based widgets
# appear correctly
root = App()
root.ttkStyle = ttkbootstrap.Style(master=root, theme="lumen")
root.geometry("1000x600")

root.ttkStyle.layout(
    "textOnly.TCheckbutton",
    [
        (
            "Checkbutton.padding",
            {
                "children": [
                    (
                        "Checkbutton.focus",
                        {
                            "children": [("Checkbutton.label", {"sticky": "nswe"})],
                            "side": "left",
                            "sticky": "",
                        },
                    )
                ],
                "sticky": "nswe",
            },
        )
    ],
)

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
with ProgressDialog(
    root,
    title="Starting Musketeer",
    labelText="Loading modules",
    abortCallback=sys.exit,
) as progressDialog:
    from pathlib import PurePath

    progressDialog.callback()

    import numpy as np

    progressDialog.callback()
    from ttkbootstrap.widgets import InteractiveNotebook

    progressDialog.callback()

    from . import patchMatplotlib

    progressDialog.callback()
    from .style import defaultFigureParams, figureParams

    progressDialog.callback()
    from .table import ButtonFrame

    progressDialog.callback()
    from .titration import Titration

    progressDialog.callback()
    from .titrationFrame import TitrationFrame

    progressDialog.callback()

    patchMatplotlib.applyPatch()
    progressDialog.callback()

    progressDialog.setLabelText("Loading interface")

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
            self.resDropdown.set(
                f"{defaultFigureParams['x']} x {defaultFigureParams['y']}"
            )

        def initValues(self):
            self.scaleDropdown.set(f"{figureParams['scale']}%")
            self.resDropdown.set(f"{figureParams['x']} x {figureParams['y']}")

        def save(self):
            if self.apply():  # returns False if failed to apply
                self.destroy()

        def apply(self):
            scale = int(self.scaleDropdown.get().strip("%"))
            x, y = [int(i) for i in self.resDropdown.get().split(" x ")]
            figureParams.update(scale=scale, x=x, y=y)
            self.saveCallback()
            return True

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
            root.ttkStyle.configure("large.success.TButton", font=self.quickStartFont)
            root.ttkStyle.configure("large.TButton", font=self.quickStartFont)

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
            with ProgressDialog(
                self,
                title="Loading titration",
                labelText="Waiting for filename",
            ) as progressDialog:
                filePath = fd.askopenfilename(
                    title="Open file",
                    filetypes=[("Musketeer files", "*.fit"), ("All files", "*.*")],
                )
                if filePath == "":
                    return

                progressDialog.setLabelText(f"Loading {PurePath(filePath).name}")

                titration = np.load(filePath, allow_pickle=False)

                titrationFrame = TitrationFrame(self, filePath, padding=padding)
                self.add(titrationFrame, text=PurePath(filePath).name, sticky="nesw")
                self.select(str(titrationFrame))
                titrationFrame.loadTitration(titration, progressDialog.callback)

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
                if isinstance(titrationFrame := self.nametowidget(tab), TitrationFrame):
                    titrationFrame.updateDpi()
            self.update()

    notebook = TitrationsNotebook(frame)
    progressDialog.callback()
    notebook.pack(expand=True, fill="both")

root.mainloop()
