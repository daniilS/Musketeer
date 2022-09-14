import tkinter as tk
import tkinter.ttk as ttk


# all module strategies should be a subclass
class Strategy:
    Popup = None
    # List of titration attributes that are set through the popup window, and
    # can be loaded from / saved to a file.
    popupAttributes = ()

    def __init__(self, titration):
        self.titration = titration

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()


class Popup(tk.Toplevel):
    def show(self):
        if self._windowingsystem != "aqua":
            # On some versions of macOS, calling grab_set here sets the popup
            # grab before the global grab on the menu is realeased, leaving
            # the popup unresponsive to mouse events.
            # TODO: find better place for callback that avoids this issue
            self.grab_set()
        self.saved = False
        self.wait_window()
        return self.saved


class ModuleFrame(ttk.LabelFrame):
    frameLabel = ""
    dropdownLabelText = ""
    dropdownOptions = {}
    attributeName = ""
    setDefault = True

    def __init__(self, parent, titration, updatePlots, *args, **kwargs):
        super().__init__(parent, text=self.frameLabel, borderwidth=5, *args, **kwargs)
        self.titration = titration
        self.updatePlots = updatePlots

        self.stringVar = tk.StringVar()

        self.dropdownLabel = ttk.Label(self, text=self.dropdownLabelText)
        self.dropdownLabel.pack()

        strategies = list(self.dropdownOptions.keys())
        self.lastValue = strategies[0] if self.setDefault else ""
        optionMenu = ttk.OptionMenu(
            self,
            self.stringVar,
            self.lastValue,
            command=self.callback,
            *strategies,
            style="primary.Outline.TMenubutton"
        )
        optionMenu.configure(width=30)
        # call the callback for the default value
        if self.setDefault:
            self.callback(self.lastValue)
        optionMenu.pack(fill="x", pady=(5, 0))

    def callback(self, value):
        SelectedStrategy = self.dropdownOptions[value]
        selectedStrategy = SelectedStrategy(self.titration)
        if selectedStrategy.Popup is not None:
            popup = selectedStrategy.Popup(self.titration)
            if not popup.show():
                # Returns False if the new options shouldn't be saved, so restore the
                # previous value.
                self.stringVar.set(self.lastValue)
                return
        setattr(self.titration, self.attributeName, selectedStrategy)
        self.updatePlots()
        self.lastValue = value
