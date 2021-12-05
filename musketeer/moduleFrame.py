import tkinter as tk
import tkinter.ttk as ttk


# all module strategies should be a subclass
class Strategy():
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()

    # provide an empty popup method so that strategies not requiring a GUI
    # don't need to explicitly define one
    def showPopup(self):
        pass


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
        # call the callback for the default value
        if self.setDefault:
            self.callback(defaultValue)
        optionMenu.pack(fill="x", pady=(5, 0))

    def callback(self, value):
        SelectedStrategy = self.dropdownOptions[value]
        selectedStrategy = SelectedStrategy(self.titration)
        selectedStrategy.showPopup()
        setattr(self.titration, self.attributeName, selectedStrategy)
        self.updatePlots()
