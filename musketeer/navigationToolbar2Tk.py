import tkinter as tk
import tkinter.ttk as ttk

from matplotlib.backends.backend_tkagg import (
    NavigationToolbar2Tk as OriginalToolbar
)


# TODO: Fix the tooltips. In the default matplotlib class, the tooltip can
# partially cover the button, causing it to rapidly appear and disappear if the
# mouse is at the overlapping position. This isn't noticeable in the default
# style where there is no difference between the default and hovered state, but
# causes the button to flash when using ttkbootstrap.

# updates the navigation toolbar to use ttk, and the correct ttkbootstrap style
class NavigationToolbar2Tk(OriginalToolbar):
    def _Button(self, text, image_file, toggle, command):
        if tk.TkVersion >= 8.6:
            PhotoImage = tk.PhotoImage
        else:
            from PIL.ImageTk import PhotoImage
        image = (PhotoImage(master=self, file=image_file)
                 if image_file is not None else None)
        if not toggle:
            b = ttk.Button(
                master=self, text=text, image=image, command=command,
                style="Outline.TButton"
            )
        else:
            # There is a bug in tkinter included in some python 3.6 versions
            # that without this variable, produces a "visual" toggling of
            # other near checkbuttons
            # https://bugs.python.org/issue29402
            # https://bugs.python.org/issue25684
            var = tk.IntVar(master=self)
            b = ttk.Checkbutton(
                master=self, text=text, image=image, command=command,
                variable=var, style="Outline.Toolbutton")
            b.var = var
        b._ntimage = image
        b.pack(side=tk.LEFT)
        return b
