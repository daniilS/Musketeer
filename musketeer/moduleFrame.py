import tkinter as tk
import tkinter.ttk as ttk


# all module strategies should be a subclass
class Strategy():
    popup = None

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
        super().__init__(
            parent, text=self.frameLabel, borderwidth=5,
            *args, **kwargs

        )
        self.titration = titration
        self.updatePlots = updatePlots

        self.stringVar = tk.StringVar()

        self.dropdownLabel = ttk.Label(self, text=self.dropdownLabelText)
        self.dropdownLabel.pack()

        strategies = list(self.dropdownOptions.keys())
        defaultValue = strategies[0] if self.setDefault else None
        optionMenu = ttk.OptionMenu(
            self, self.stringVar, defaultValue, command=self.callback,
            *strategies, style="primary.Outline.TMenubutton"
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
            # if grab_set is called immediately, on some versions of macOS
            # this leaves the Toplevel window unresponsive to mouse clicks
            if not popup.winfo_viewable():
                popup.wait_visibility()
            popup.grab_set()
            popup.wait_window()
        setattr(self.titration, self.attributeName, selectedStrategy)
        self.updatePlots()
