import functools
import tkinter as tk
import tkinter.ttk as ttk

import matplotlib
from matplotlib import cbook, offsetbox
from matplotlib.axes import Axes
from matplotlib.axes._base import _AxesBase
from matplotlib.backend_bases import NavigationToolbar2, _Mode, cursors
from matplotlib.backends._backend_tk import (
    FigureCanvasTk,
    NavigationToolbar2Tk,
    add_tooltip,
)

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
            if callback == "configure_subplots":
                # configure subplots doesn't work with constrained layout
                continue
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
                    add_tooltip(button, tooltip_text)

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


class VerticalToolbarAxes(Axes):
    def format_coord(self, x, y):
        return (
            f"x={'???' if x is None else self.format_xdata(x)}\n"
            f"y={'???' if y is None else self.format_ydata(y)}"
        )


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


def __init__(self, ref_artist, use_blit=False):
    self.ref_artist = ref_artist
    if not ref_artist.pickable():
        ref_artist.set_picker(True)
    self.got_artist = False
    self._hover = False
    self._use_blit = use_blit and self.canvas.supports_blit
    callbacks = ref_artist.figure._canvas_callbacks
    self._disconnectors = [
        functools.partial(
            callbacks.disconnect, callbacks._connect_picklable(name, func)
        )
        for name, func in [
            ("pick_event", self.on_pick),
            ("button_release_event", self.on_release),
            ("motion_notify_event", self.on_motion),
        ]
    ]


def on_motion(self, evt):
    # Only check if the widget lock is available, setting it would prevent
    # picking.
    if not (self._check_still_parented() and self.canvas.widgetlock.available(self)):
        return

    picker = self.ref_artist.get_picker()
    if callable(picker):
        inside, _ = picker(self, evt)
    else:
        inside, _ = self.ref_artist.contains(evt)

    # If the mouse is moving quickly while dragging, it may leave the artist,
    # but should still use the move cursor.
    if inside or self.got_artist:
        # Ideally, this should use an open hand cursor on hover, and a closed
        # hand when dragging, but those cursors are not natively provided by
        # all platforms.
        self._hover = True
        self.canvas.set_cursor(cursors.MOVE)
    elif self._hover:
        # Only change the cursor back if this is the widget that set it, to
        # avoid multiple draggable widgets fighting over the cursor.
        self._hover = False
        self.canvas.set_cursor(cursors.POINTER)

    if self._check_still_parented() and self.got_artist:
        dx = evt.x - self.mouse_x
        dy = evt.y - self.mouse_y
        self.update_offset(dx, dy)
        if self._use_blit:
            self.canvas.restore_region(self.background)
            self.ref_artist.draw(self.ref_artist.figure._get_renderer())
            self.canvas.blit()
        else:
            self.canvas.draw()


def on_pick(self, evt):
    if self._check_still_parented() and evt.artist == self.ref_artist:
        self.mouse_x = evt.mouseevent.x
        self.mouse_y = evt.mouseevent.y
        self.got_artist = True
        if self._use_blit:
            self.ref_artist.set_animated(True)
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.ref_artist.figure.bbox)
            self.ref_artist.draw(self.ref_artist.figure._get_renderer())
            self.canvas.blit()
        self.save_offset()


def on_release(self, event):
    if self._check_still_parented() and self.got_artist:
        self.finalize_offset()
        self.got_artist = False

        if self._use_blit:
            self.ref_artist.set_animated(False)


def disconnect(self):
    """Disconnect the callbacks."""
    for disconnector in self._disconnectors:
        disconnector()
    if self._hover:
        self.canvas.set_cursor(cursors.POINTER)


original_scroll_event_windows = FigureCanvasTk.scroll_event_windows


def scroll_event_windows(self, event):
    # gives an error when scrolling over "tk busy" otherwise
    if not isinstance(event.widget, str):
        original_scroll_event_windows(self, event)


original_clear = _AxesBase.clear


def clear(self, *args, **kwargs):
    if hasattr(self, "legend_") and self.legend_ is not None:
        self.legend_.axes = self.legend_.figure = None
    original_clear(self, *args, **kwargs)


def applyPatch():
    # makes buttons use ttk widgets
    NavigationToolbar2Tk._Button = _Button
    NavigationToolbar2Tk._Spacer = _Spacer
    NavigationToolbar2Tk._update_buttons_checked = _update_buttons_checked

    # implements PR #25412
    offsetbox.DraggableBase.__init__ = __init__
    offsetbox.DraggableBase.on_motion = on_motion
    offsetbox.DraggableBase.on_pick = on_pick
    offsetbox.DraggableBase.on_release = on_release
    offsetbox.DraggableBase.disconnect = disconnect
    _AxesBase.clear = clear

    FigureCanvasTk.scroll_event_windows = scroll_event_windows
