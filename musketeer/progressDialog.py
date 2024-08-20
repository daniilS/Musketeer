import tkinter as tk
from tkinter import ttk

from .style import padding


class ProgressDialog(tk.Toplevel):
    def __init__(
        self,
        master,
        title="Please wait...",
        labelText=" ",
        progressbarSteps=None,
        *args,
        abortCallback=None,
        **kwargs,
    ):
        super().__init__(master, *args, **kwargs)
        self.withdraw()

        self.determinate = progressbarSteps is not None
        self.abortCallback = abortCallback

        class CancelError(Exception):
            pass

        self.CancelError = CancelError
        self.cancelled = False

        self.title(title)
        self.protocol("WM_DELETE_WINDOW", self.bell)

        self.label = ttk.Label(self, text=labelText)
        self.label.pack(padx=padding, pady=padding)

        self.progressbar = ttk.Progressbar(
            self,
            max=(progressbarSteps or 30),
            mode="determinate" if self.determinate else "indeterminate",
        )
        self.progressbar.pack(padx=padding, pady=padding, fill="x")

        self.button = ttk.Button(self, text="Abort", command=self.cancel)
        self.button.pack(padx=padding, pady=padding)

    def cancel(self):
        self.cancelled = True

    # To be called by long functions inside the context
    def callback(self, *args, **kwargs):
        if not self.determinate:
            self.progressbar.step()
        self.update()
        if self.cancelled:
            raise self.CancelError

    def __enter__(self):
        parentWindow = self.master.winfo_toplevel()
        self.update()
        width = max(self.winfo_reqwidth(), 250)
        height = self.winfo_reqheight()
        x = int(parentWindow.winfo_x() + parentWindow.winfo_width() / 2 - width / 2)
        y = int(parentWindow.winfo_y() + parentWindow.winfo_height() / 2 - height / 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        self.transient(self.master)

        if self._windowingsystem == "aqua":
            self.oldParentCursor = parentWindow.cget("cursor")
            parentWindow.configure(cursor="wait")
        else:
            self.tk.eval(f"tk busy {parentWindow._w}")

        self.oldGrab = parentWindow.grab_current()

        self.update()
        return self

    def teardown(self):
        parentWindow = self.master.winfo_toplevel()

        if self._windowingsystem == "aqua":
            parentWindow.configure(cursor=self.oldParentCursor)
        elif self.tk.eval(f"tk busy status {parentWindow._w}") == "1":
            self.tk.eval(f"tk busy forget {parentWindow._w}")

        if self.oldGrab is not None and self.oldGrab.winfo_exists():
            self.oldGrab.grab_set()

        self.destroy()

    def __exit__(self, exc_type, exc_value, traceback):
        self.teardown()

        if exc_type is self.CancelError:
            if self.abortCallback is not None:
                self.abortCallback()
            return True
