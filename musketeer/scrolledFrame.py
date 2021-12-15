# Based on https://github.com/bmjcode/tkScrolledFrame by
import sys
import tkinter as tk
import tkinter.ttk as ttk

# TODO: replace with custom implementation to solve flickering issues
from ttkwidgets.autohidescrollbar import AutoHideScrollbar


class ScrolledFrame(ttk.Frame):
    def __init__(self, master=None, autohide=True, max_width=None, **kw):
        """Return a new scrollable frame widget."""

        super().__init__(master)

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
                raise ValueError("scrollbars parameter must be one of "
                                 "'vertical', 'horizontal', 'both', or "
                                 "'neither'")
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
        c = self._canvas = tk.Canvas(self,
                                     borderwidth=0,
                                     highlightthickness=0,
                                     takefocus=0)

        self.bind_mousewheel()

        # Call _resize_interior() when the canvas widget is updated
        c.bind("<Configure>", self._resize_interior)

        # Scrollbars
        xs = self._x_scrollbar = Scrollbar(self,
                                           orient="horizontal",
                                           command=c.xview)
        ys = self._y_scrollbar = Scrollbar(self,
                                           orient="vertical",
                                           command=c.yview)
        c.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)

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

    def bind_mousewheel(self):
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.winfo_toplevel().bind(event, self.scroll_binding, add=True)

    def scroll_binding(self, event):
        widget = event.widget
        if not str(widget).startswith(str(self)):
            return  # Cursor outside of the frame
        if (
            "<MouseWheel>" in widget.tk.call("bind", widget.winfo_class())
            or "<MouseWheel>" in widget.bind()
        ):
            return  # Widget has its own mouse wheel binding
        self._scroll_canvas(event)

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
        self._interior_id = self._canvas.create_window(0, 0,
                                                       anchor="nw",
                                                       window=self._interior)

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

    def _scroll_canvas(self, event):
        """Scroll the canvas."""

        c = self._canvas
        horizontal_scroll = bool(event.state & 1)
        # only scroll if the inner frame doesn't fit fully
        if (
            (horizontal_scroll and self._interior.winfo_reqwidth() < self._canvas.winfo_width())
            or ((not horizontal_scroll) and self._interior.winfo_reqheight() < self._canvas.winfo_height())
        ):
            return

        scroll = c.xview_scroll if horizontal_scroll else c.yview_scroll

        if sys.platform.startswith("darwin"):
            # macOS
            scroll(-1 * event.delta, "units")

        elif event.num == 4:
            # Unix - scroll up
            scroll(-1, "units")

        elif event.num == 5:
            # Unix - scroll down
            scroll(1, "units")

        else:
            # Windows
            scroll(-1 * (event.delta // 120), "units")

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
