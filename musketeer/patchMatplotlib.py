import tkinter as tk
import tkinter.ttk as ttk

import matplotlib
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backend_bases import _Mode

matplotlib.use("TkAgg")


# updates the navigation toolbar to use ttk, and the correct ttkbootstrap style
def _Button(self, text, image_file, toggle, command):
    if tk.TkVersion >= 8.6:
        PhotoImage = tk.PhotoImage
    else:
        from PIL.ImageTk import PhotoImage
    image = PhotoImage(master=self, file=image_file) if image_file is not None else None
    if not toggle:
        b = ttk.Button(
            master=self,
            text=text,
            image=image,
            command=command,
            style="Outline.TButton",
        )
    else:
        var = tk.IntVar(master=self)
        b = ttk.Checkbutton(
            master=self,
            text=text,
            image=image,
            command=command,
            variable=var,
            style="Outline.Toolbutton",
        )
        b.var = var
    b._ntimage = image
    b.pack(side=tk.LEFT)
    return b


def _update_buttons_checked(self):
    # sync button checkstates to match active mode
    for text, mode in [("Zoom", _Mode.ZOOM), ("Pan", _Mode.PAN)]:
        if text in self._buttons:
            if self.mode == mode:
                self._buttons[text].var.set(1)
            else:
                self._buttons[text].var.set(0)


def applyPatch():
    # makes buttons use ttk widgets
    NavigationToolbar2Tk._Button = _Button
    NavigationToolbar2Tk._update_buttons_checked = _update_buttons_checked
