import tkinter as tk
import tkinter.ttk as ttk

import matplotlib
from matplotlib import cbook
from matplotlib.backend_bases import NavigationToolbar2, _Mode
from matplotlib.backends._backend_tk import NavigationToolbar2Tk, ToolTip
from tksheet import _tksheet, _tksheet_column_headers, _tksheet_main_table

matplotlib.use("TkAgg")


class NavigationToolbarVertical(NavigationToolbar2Tk):
    def __init__(self, canvas, window=None, *, pack_toolbar=True):
        """
        Parameters
        ----------
        canvas : `FigureCanvas`
            The figure canvas on which to operate.
        window : tk.Window
            The tk.Window which owns this toolbar.
        pack_toolbar : bool, default: True
            If True, add the toolbar to the parent's pack manager's packing
            list during initialization with ``side="bottom"`` and ``fill="x"``.
            If you want to use the toolbar with a different layout manager, use
            ``pack_toolbar=False``.
        """

        if window is None:
            window = canvas.get_tk_widget().master
        tk.Frame.__init__(
            self,
            master=window,
            borderwidth=2,
            width=int(canvas.figure.bbox.width),
            height=50,
        )

        self._buttons = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                # Add a spacer; return value is unused.
                self._Spacer()
            else:
                self._buttons[text] = button = self._Button(
                    text,
                    str(cbook._get_data_path(f"images/{image_file}.png")),
                    toggle=callback in ["zoom", "pan"],
                    command=getattr(self, callback),
                )
                if tooltip_text is not None:
                    ToolTip.createToolTip(button, tooltip_text)

        self.message = tk.StringVar(master=self)
        self.message.set("\N{NO-BREAK SPACE}\n\N{NO-BREAK SPACE}")
        self._message_label = ttk.Label(
            master=self,
            textvariable=self.message,
            width=len("y=-1234.5"),
        )
        self._message_label.bind(
            "<Configure>",
            lambda *args: self._message_label.configure(width=len("y=-1234.5")),
        )
        self._message_label.pack(side=tk.TOP)

        NavigationToolbar2.__init__(self, canvas)

    def set_message(self, s):
        self.message.set(s.replace(" ", "\n"))


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
    if isinstance(self, NavigationToolbarVertical):
        b.pack(side=tk.TOP, pady=2)
    else:
        b.pack(side=tk.LEFT)
    return b


def _Spacer(self):
    if isinstance(self, NavigationToolbarVertical):
        s = ttk.Separator(master=self, orient=tk.HORIZONTAL)
        s.pack(side=tk.TOP, pady="2")
    else:
        s = ttk.Separator(master=self, orient=tk.VERTICAL)
        s.pack(side=tk.LEFT, padx="3p")
    return s


def _update_buttons_checked(self):
    # sync button checkstates to match active mode
    for text, mode in [("Zoom", _Mode.ZOOM), ("Pan", _Mode.PAN)]:
        if text in self._buttons:
            if self.mode == mode:
                self._buttons[text].var.set(1)
            else:
                self._buttons[text].var.set(0)


def nop(self):
    pass


def applyPatch():
    # makes buttons use ttk widgets
    NavigationToolbar2Tk._Button = _Button
    NavigationToolbar2Tk._Spacer = _Spacer
    NavigationToolbar2Tk._update_buttons_checked = _update_buttons_checked

    # remove calls to update() from tksheet
    _tksheet.Sheet.update = nop
    _tksheet_main_table.MainTable.update = nop
    _tksheet_column_headers.ColumnHeaders.update = nop
