import tkinter as tk
import tkinter.ttk as ttk


class ModuleFrame(ttk.LabelFrame):
    frameLabel = ""
    dropdownLabelText = ""
    dropdownOptions = {}
    attributeName = ""
    setDefault = True

    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(
            parent, text=self.frameLabel, borderwidth=5,
            *args, **kwargs

        )
        self.titration = titration

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
        Strategy = self.dropdownOptions[value]
        setattr(self.titration, self.attributeName, Strategy(self.titration))
