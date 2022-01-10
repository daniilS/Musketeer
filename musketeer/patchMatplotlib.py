import tkinter as tk
import tkinter.ttk as ttk

import matplotlib
from matplotlib.backends._backend_tk import NavigationToolbar2Tk, ToolTip
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


# make the tooltips appear further to the right to prevent them from
# overlapping the buttons
def showtip(self, text):
    """Display text in tooltip window."""
    self.text = text
    if self.tipwindow or not self.text:
        return
    x, y, _, _ = self.widget.bbox("insert")
    x = x + self.widget.winfo_rootx() + self.widget.winfo_width()
    y = y + self.widget.winfo_rooty()
    self.tipwindow = tw = tk.Toplevel(self.widget)
    tw.wm_overrideredirect(1)
    tw.wm_geometry("+%d+%d" % (x, y))
    try:
        # For Mac OS
        tw.tk.call(
            "::tk::unsupported::MacWindowStyle", "style", tw._w, "help", "noActivates"
        )
    except tk.TclError:
        pass
    label = tk.Label(
        tw, text=self.text, justify=tk.LEFT, relief=tk.SOLID, borderwidth=1
    )
    label.pack(ipadx=1)


def applyPatch():
    NavigationToolbar2Tk._Button = _Button
    NavigationToolbar2Tk._update_buttons_checked = _update_buttons_checked

    ToolTip.showtip = showtip
