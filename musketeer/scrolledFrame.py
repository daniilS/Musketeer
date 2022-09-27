# Based on https://github.com/bmjcode/tkScrolledFrame by
import sys
import time
import tkinter as tk
import tkinter.ttk as ttk
from packaging.version import parse as v_parse

# TODO: replace with custom implementation to solve flickering issues
from ttkwidgets.autohidescrollbar import AutoHideScrollbar


class ScrolledFrame(ttk.Frame):
    fps = 60
    interval = 1 / fps
    steps = int(fps / 10)

    mousewheel_bindings = None

    def bind_mousewheel(self):
        if self.mousewheel_bindings is not None:
            return False
        else:
            events = (
                ("<MouseWheel",)
                if self.use_TIP474
                else ("<MouseWheel>", "<Button-4>", "<Button-5>")
            )
            ScrolledFrame.mousewheel_bindings = [
                self.bind_all(event, self.deliver_event, add=True) for event in events
            ]

    def deliver_event(self, event):
        widget = event.widget

        event_name = f"<{event.type._name_}>"
        if any(
            [
                event_name in widget._bind(("bind", tag), None, None, None)
                for tag in widget.bindtags()
                if tag not in ("all", widget.winfo_toplevel()._w)
            ]
        ):
            return  # Widget has its own mouse wheel binding
        # Can't check for whether the widget is the toplevel in the loop condition, as
        # wm_manage could turn a ScrolledFrame into a toplevel window.
        while True:
            if isinstance(widget, ScrolledFrame):
                break
            if widget == widget.winfo_toplevel():
                return  # event occurred outside of any ScrolledFrames
            widget = widget.nametowidget(widget.winfo_parent())
        widget.process_event(event)

    def process_event(self, event):
        orient = "horizontal" if bool(event.state & 1) else "vertical"
        # only scroll if the inner frame doesn't fit fully
        if (
            orient == "horizontal"
            and self._interior.winfo_reqwidth() < self._canvas.winfo_width()
        ) or (
            orient == "vertical"
            and self._interior.winfo_reqheight() < self._canvas.winfo_height()
        ):
            return

        if sys.platform.startswith("darwin") and not self.use_TIP474:
            # macOS, pre Tk 8.7
            self.scroll_canvas(orient, "scroll", -1 * event.delta, "units")

        elif event.num == 4:
            # Unix - scroll up
            self.scroll_canvas(orient, "scroll", -1, "units")

        elif event.num == 5:
            # Unix - scroll down
            self.scroll_canvas(orient, "scroll", 1, "units")

        else:
            # Windows
            self.scroll_canvas(
                orient, "scroll", str(-1 * (event.delta // 120)), "units"
            )

    def scroll_canvas_x(self, *args):
        return self.scroll_canvas("horizontal", *args)

    def scroll_canvas_y(self, *args):
        return self.scroll_canvas("vertical", *args)

    def scroll_canvas(self, orient, *args):
        view = "yview" if orient == "vertical" else "xview"
        if args[0] == "moveto":
            currentTime = time.perf_counter()
            if currentTime - self.lastTime >= self.interval:
                setview = (
                    self._canvas.yview if orient == "vertical" else self._canvas.xview
                )
                setview(*args)
                self.lastTime = currentTime
            else:
                nextTime = self.lastTime + self.interval
                delay = nextTime - currentTime
                if delay <= 2 * self.interval:
                    self.lastTime = nextTime
                    # avoid the overhead of creating a new Python function and calling it
                    # from Tk
                    self.tk.eval(
                        f"after {int(1000 * delay)} [list"
                        f" {self._canvas._w} {view} {' '.join(args)}]"
                    )
        elif args[0] == "scroll" and args[2] == "units":
            for i in range(self.steps):
                totalSize = (
                    self._canvas.winfo_height()
                    if orient == "vertical"
                    else self._canvas.winfo_width()
                )
                distance = int(args[1]) * totalSize / 20 / self.steps
                self.tk.eval(
                    f"after {int(i * 1000 * self.interval)} [list"
                    f" {self._canvas._w} {view} scroll {int(distance * (1 + i))} units]"
                )

    def __init__(self, master=None, autohide=True, max_width=None, **kw):
        """Return a new scrollable frame widget."""
        self.lastTime = 0

        super().__init__(master)

        # Check if we should use the MouseWheel behaviour from TIP 474 introduced in
        # Tk 8.7
        self.use_TIP474 = v_parse(self.tk.getvar("tk_version")) >= v_parse("8.7")

        # Hold these names for the interior widget
        self._interior = None
        self._interior_id = None

        # Which scrollbars to provide
        if "scrollbars" in kw:
            scrollbars = kw["scrollbars"]
            del kw["scrollbars"]

            if not scrollbars:
                scrollbars = self._DEFAULT_SCROLLBARS
            elif scrollbars not in self._VALID_SCROLLBARS:
                raise ValueError(
                    "scrollbars parameter must be one of "
                    "'vertical', 'horizontal', 'both', or "
                    "'neither'"
                )
        else:
            scrollbars = self._DEFAULT_SCROLLBARS

        if autohide:
            Scrollbar = AutoHideScrollbar
        else:
            Scrollbar = ttk.Scrollbar

        self._max_width = max_width

        # Default to a 1px sunken border
        if "borderwidth" not in kw:
            kw["borderwidth"] = 0
        if "relief" not in kw:
            kw["relief"] = "flat"

        # Set up the grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Canvas to hold the interior widget
        c = self._canvas = tk.Canvas(
            self, borderwidth=0, highlightthickness=0, takefocus=0
        )

        self.bind_mousewheel()

        # Call _resize_interior() when the canvas widget is updated
        c.bind("<Configure>", self._resize_interior)

        # Scrollbars
        xs = self._x_scrollbar = Scrollbar(
            self, orient="horizontal", command=self.scroll_canvas_x
        )
        ys = self._y_scrollbar = Scrollbar(
            self, orient="vertical", command=self.scroll_canvas_y
        )
        c.configure(
            xscrollcommand=xs.set,
            yscrollcommand=ys.set,
            xscrollincrement=1,
            yscrollincrement=1,
        )

        # Lay out our widgets
        c.grid(row=0, column=0, sticky="nsew")
        if scrollbars == "vertical" or scrollbars == "both":
            ys.grid(row=0, column=1, sticky="ns")
        if scrollbars == "horizontal" or scrollbars == "both":
            xs.grid(row=1, column=0, sticky="we")

        # Forward these to the canvas widget
        self.bind = c.bind
        self.focus_set = c.focus_set
        self.unbind = c.unbind
        self.xview = c.xview
        self.xview_moveto = c.xview_moveto
        self.yview = c.yview
        self.yview_moveto = c.yview_moveto

        # Process our remaining configuration options
        self.configure(**kw)

    def __setitem__(self, key, value):
        """Configure resources of a widget."""

        if key in self._CANVAS_KEYS:
            # Forward these to the canvas widget
            self._canvas.configure(**{key: value})

        else:
            # Handle everything else normally
            tk.Frame.configure(self, **{key: value})

    # ------------------------------------------------------------------------

    def cget(self, key):
        """Return the resource value for a KEY given as string."""

        if key in self._CANVAS_KEYS:
            return self._canvas.cget(key)

        else:
            return tk.Frame.cget(self, key)

    # Also override this alias for cget()
    __getitem__ = cget

    def configure(self, cnf=None, **kw):
        """Configure resources of a widget."""

        # This is overridden so we can use our custom __setitem__()
        # to pass certain options directly to the canvas.
        if cnf:
            for key in cnf:
                self[key] = cnf[key]

        for key in kw:
            self[key] = kw[key]

    # Also override this alias for configure()
    config = configure

    def display_widget(self, widget_class, stretch=True, **kw):
        self._stretch = stretch
        """Create and display a new widget.

        If stretch == True, the interior widget will be stretched as
        needed to fit the width of the frame.

        Keyword arguments are passed to the widget_class constructor.

        Returns the new widget.
        """

        # Blank the canvas
        self.erase()

        # Set the new interior widget
        self._interior = widget_class(self._canvas, **kw)

        # Add the interior widget to the canvas, and save its widget ID
        # for use in _resize_interior()
        self._interior_id = self._canvas.create_window(
            0, 0, anchor="nw", window=self._interior
        )

        # Call _update_scroll_region() when the interior widget is resized
        self._interior.bind("<Configure>", self._update_scroll_region)

        # Fit the interior widget to the canvas if requested
        # We don't need to check fit_width here since _resize_interior()
        # already does.
        self._resize_interior()

        # Scroll to the top-left corner of the canvas
        self.scroll_to_top()

        return self._interior

    def erase(self):
        """Erase the displayed widget."""

        # Clear the canvas
        self._canvas.delete("all")

        # Delete the interior widget
        del self._interior
        del self._interior_id

        # Save these names
        self._interior = None
        self._interior_id = None

        # Reset width fitting
        self._fit_width = False

    def scroll_to_top(self):
        """Scroll to the top-left corner of the canvas."""

        self._canvas.xview_moveto(0)
        self._canvas.yview_moveto(0)

    # ------------------------------------------------------------------------

    def _resize_interior(self, event=None):
        """Resize the canvas to fit the interior widget."""
        if self._stretch:
            # The current width of the canvas
            canvas_width = self._canvas.winfo_width()

            # The interior widget's requested width
            requested_width = self._interior.winfo_reqwidth()

            if requested_width != canvas_width:
                # Resize the interior widget
                if self._max_width is not None:
                    requested_width = min(self._max_width, requested_width)
                self._canvas.config(width=requested_width)

            canvas_height = self._canvas.winfo_height()
            requested_height = self._interior.winfo_reqheight()
            if requested_height < canvas_height:
                self._canvas.config(height=requested_height)

    def _update_scroll_region(self, event):
        """Update the scroll region when the interior widget is resized."""

        # The interior widget's requested width and height
        req_width = self._interior.winfo_reqwidth()
        req_height = self._interior.winfo_reqheight()

        # Set the scroll region to fit the interior widget
        self._canvas.configure(scrollregion=(0, 0, req_width, req_height))

    # ------------------------------------------------------------------------

    # Keys for configure() to forward to the canvas widget
    _CANVAS_KEYS = "width", "height", "takefocus"

    # Scrollbar-related configuration
    _DEFAULT_SCROLLBARS = "both"
    _VALID_SCROLLBARS = "vertical", "horizontal", "both", "neither"
