import logging
import tkinter as tk
from tkinter import ttk
import warnings

from .style import padding


class CustomHandler(logging.Handler):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__callback = callback

    def emit(self, record):
        return self.__callback(record)


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
        self.minWidth = 250
        self.minsize(self.minWidth, 0)

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

        self.button = ttk.Button(
            self, text="Abort", command=self.cancel, style="danger.Outline.TButton"
        )
        self.button.pack(padx=padding, pady=padding)

        self.warningsList = []
        self.warningsLabel = ttk.Label(self, text="", font="TkFixedFont")

    def cancel(self):
        self.cancelled = True

    # To be called by long functions inside the context
    def callback(self, *args, **kwargs):
        if not self.determinate:
            self.progressbar.step()
        self.update()
        if self.cancelled:
            raise self.CancelError

    def setLabelText(self, text):
        self.label.configure(text=text)
        self.update()
        self.centerWindow()

    def centerWindow(self):
        parentWindow = self.master.winfo_toplevel()
        width = max(self.winfo_reqwidth(), self.minWidth)
        height = self.winfo_reqheight()
        x = int(parentWindow.winfo_x() + parentWindow.winfo_width() / 2 - width / 2)
        y = int(parentWindow.winfo_y() + parentWindow.winfo_height() / 2 - height / 2)
        self.geometry(f"+{x}+{y}")

    def enter(self):
        parentWindow = self.master.winfo_toplevel()
        self.update()
        self.centerWindow()
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

    def updateWarningsLabel(self, message):
        self.warningsList.append(message)
        self.warningsLabel.configure(text="\n\n".join(self.warningsList))
        self.warningsLabel.pack(padx=padding, pady=padding, fill="both")

    def showwarning(
        self, message, category, filename, lineno, file=None, line=None, **kwargs
    ):
        if file is not None:
            return self.originalShowwarning(
                message, category, filename, lineno, file=file, line=None, **kwargs
            )
        else:
            self.updateWarningsLabel(
                f"{category.__name__ if category else 'Warning'}: {message}"
            )

    def handlerCallback(self, record):
        self.updateWarningsLabel(f"{record.levelname}: {record.getMessage()}")

    def __enter__(self):
        self.warningsContextManager = warnings.catch_warnings(record=True)
        self.warningsContext = self.warningsContextManager.__enter__()
        self.originalShowwarning = warnings.showwarning
        warnings.showwarning = self.showwarning

        try:
            self.logger = logging.getLogger()
            self.handler = CustomHandler(self.handlerCallback, level=logging.WARNING)
            self.logger.addHandler(self.handler)

            return self.enter()
        except Exception as e:
            if not self.warningsContextManager.__exit__(type(e), e, e.__traceback__):
                raise

    def teardown(self):
        self.logger.removeHandler(self.handler)

        parentWindow = self.master.winfo_toplevel()

        if self._windowingsystem == "aqua":
            parentWindow.configure(cursor=self.oldParentCursor)
        elif self.tk.eval(f"tk busy status {parentWindow._w}") == "1":
            self.tk.eval(f"tk busy forget {parentWindow._w}")

        if self.oldGrab is not None and self.oldGrab.winfo_exists():
            self.oldGrab.grab_set()

        self.destroy()

    def exit(self, exc_type, exc_value, tb):
        self.teardown()

        if exc_type is self.CancelError:
            if self.abortCallback is not None:
                self.abortCallback()
            return True

    def __exit__(self, exc_type, exc_value, tb):
        try:
            handled = self.exit(exc_type, exc_value, tb)
        except Exception as e:
            # New exception e was raised while handling the original exception
            if not self.warningsContextManager.__exit__(type(e), e, e.__traceback__):
                raise
            # The new exception was handled by the outer context, but the original one
            # wasn't, so caller should re-raise it.
            return False
        else:
            if handled:
                # Inner context already handled the exception
                self.warningsContextManager.__exit__()
                return handled
            else:
                # Let the outer context attempt to handle it
                return self.warningsContextManager.__exit__(exc_type, exc_value, tb)
