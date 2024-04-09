import importlib
import sys
import tkinter as tk
import tkinter.ttk as ttk
from abc import ABC

from . import style
from .style import padding


# all module strategies should be a subclass
class Strategy(ABC):
    Popup = None

    # List of attributes that are set through the popup window, and can be
    # loaded from / saved to a file.
    popupAttributes = ()

    # List of attributes that each base Strategy class should define, for all concrete
    # strategies to set either in __init__ or from the popup. Compliance by the concrete
    # strategies is checked in ModuleFrame.callback().
    requiredAttributes = NotImplemented

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.requiredAttributes is NotImplemented:
            raise NotImplementedError(
                f"Can't define class {cls.__name__} without implementing the abstract"
                " class attribute requiredAttributes"
            )

    def checkAttributes(self):
        for attr in self.requiredAttributes:
            if not hasattr(self, attr):
                raise NotImplementedError(
                    f"Can't set strategy {type(self).__name__} without"
                    f" implementing the required attribute {attr}"
                )

    def __init__(self, titration):
        self.titration = titration

    @property
    def outputCount(self):
        return len(self.outputNames)

    @property
    def variableCount(self):
        return len(self.variableNames)


class Popup(tk.Toplevel):
    def show(self):
        if self._windowingsystem != "aqua":
            # On some versions of macOS, calling grab_set here sets the popup
            # grab before the global grab on the menu is realeased, leaving
            # the popup unresponsive to mouse events.
            # TODO: find better place for callback that avoids this issue
            self.grab_set()
        self.transient(self.master)
        self.saved = False
        self.wait_window()
        return self.saved


class GroupFrame(ttk.LabelFrame):
    def __init__(self, master, group, *args, **kwargs):
        super().__init__(
            master,
            labelanchor="n",
            borderwidth=5,
            *args,
            **kwargs,
        )

        self.labelWidget = ttk.Label(
            self,
            text=group,
            font=style.italicFont,
        )
        self.configure(labelwidget=self.labelWidget)


class ModuleFrame(ttk.Frame):
    group = ""
    dropdownLabelText = ""
    dropdownOptions = {}
    attributeName = ""
    setDefault = True

    def __init__(self, parent, *args, **kwargs):
        try:
            groupFrames = parent.groupFrames
        except AttributeError:
            groupFrames = parent.groupFrames = {}

        try:
            labelFrame = groupFrames[self.group]
        except KeyError:
            labelFrame = groupFrames[self.group] = GroupFrame(parent, self.group)
            labelFrame.grid(sticky="nesw", pady=padding)

        super().__init__(labelFrame, *args, **kwargs)

        self.stringVar = tk.StringVar()

        self.dropdownLabel = ttk.Label(
            self, text=self.dropdownLabelText, justify="left"
        )
        self.dropdownLabel.pack(fill="x")

        strategies = list(self.dropdownOptions.keys())
        self.lastValue = ""
        optionMenu = ttk.OptionMenu(
            self,
            self.stringVar,
            self.lastValue,
            command=self.callback,
            *strategies,
            style="primary.Outline.TMenubutton",
        )
        optionMenu.configure(width=30)

        optionMenu.pack(fill="x", pady=(2, padding))

    def update(self, titration, setDefault=False):
        self.titration = titration
        if setDefault and self.setDefault:
            defaultValue = list(self.dropdownOptions.keys())[0]
            self.stringVar.set(defaultValue)
            self.callback(defaultValue)
            return
        elif setDefault:
            setattr(self.titration, self.attributeName, None)

        if getattr(self.titration, self.attributeName) is None:
            self.stringVar.set("")
            return
        self.lastValue = list(self.dropdownOptions.keys())[
            [x.__name__ for x in self.dropdownOptions.values()].index(
                type(getattr(self.titration, self.attributeName)).__name__
            )
        ]
        self.stringVar.set(self.lastValue)

    def callback(self, value):
        importlib.reload(sys.modules[self.__module__])
        self.dropdownOptions = sys.modules[self.__module__].ModuleFrame.dropdownOptions
        print(f"reloaded {self.__module__}")
        SelectedStrategy = self.dropdownOptions[value]
        selectedStrategy = SelectedStrategy(self.titration)
        if selectedStrategy.Popup is not None:
            root = self.winfo_toplevel()
            popup = selectedStrategy.Popup(self.titration, master=root)
            popup.geometry(f"+{root.winfo_x()+100}+{root.winfo_y()+100}")
            if not popup.show():
                # Returns False if the new options shouldn't be saved, so restore the
                # previous value.
                self.stringVar.set(self.lastValue)
                return

            for attr in selectedStrategy.popupAttributes:
                setattr(selectedStrategy, attr, getattr(popup, attr))

        selectedStrategy.checkAttributes()

        setattr(self.titration, self.attributeName, selectedStrategy)
        self.lastValue = value
