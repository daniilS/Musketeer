import tkinter as tk
import tkinter.ttk as ttk


# all module strategies should be a subclass
class Strategy:
    popup = None
    # List of titration attributes that are set through the popup window, and
    # can be loaded from / saved to a file.
    popupAttributes = ()

    def __init__(self, titration):
        self.titration = titration

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()


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
        defaultValue = strategies[0] if self.setDefault else None
        optionMenu = ttk.OptionMenu(
            self,
            self.stringVar,
            defaultValue,
            command=self.callback,
            *strategies,
            style="primary.Outline.TMenubutton"
        )
        optionMenu.configure(width=30)
        # call the callback for the default value
        if self.setDefault:
            self.callback(defaultValue)
        optionMenu.pack(fill="x", pady=(5, 0))

    def callback(self, value):
        SelectedStrategy = self.dropdownOptions[value]
        selectedStrategy = SelectedStrategy(self.titration)
        if selectedStrategy.popup is not None:
            popup = selectedStrategy.popup(self.titration)
            # On some versions of macOS, calling grab_set here sets the popup
            # grab before the global grab on the menu is realeased, leaving
            # the popup unresponsive to mouse events.
            # TODO: find better place for callback that avoids this issue
            if self._windowingsystem != "aqua":
                popup.grab_set()
            popup.wait_window()
        setattr(self.titration, self.attributeName, selectedStrategy)
        self.updatePlots()
