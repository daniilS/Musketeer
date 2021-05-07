import tkinter as tk
import tkinter.ttk as ttk

import tkscrolledframe
from ttkwidgets.autohidescrollbar import AutoHideScrollbar


# add an option to stretch the frame to fit the content, and a max width
class ScrolledFrame(tkscrolledframe.ScrolledFrame):
    def __init__(self, master=None, autohide=True, max_width=None, **kw):
        """Return a new scrollable frame widget."""

        ttk.Frame.__init__(self, master)

        # Hold these names for the interior widget
        self._interior = None
        self._interior_id = None

        # Whether to fit the interior widget's width to the canvas
        self._fit_width = False

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

        # Enable scrolling when the canvas has the focus
        # TODO: only enable scrolling when full frame isn't shown
        self.bind_arrow_keys(c)
        self.bind_scroll_wheel(c)

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

        if False:
            super().__init__(master, **kw)

            Scrollbar = AutoHideScrollbar
            c = self._canvas
            scrollbars = "both"

            self._x_scrollbar.destroy()
            self._y_scrollbar.destroy()

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

    def display_widget(self, widget_class, stretch=True, **kw):
        self._stretch = stretch
        return super().display_widget(widget_class, **kw)

    def _resize_interior(self, event=None):
        """Resize the canvas to fit the interior widget."""
        super()._resize_interior()

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
        super()._scroll_canvas(event)
