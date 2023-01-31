import csv
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from collections import namedtuple

import numpy as np
from numpy import ma
from tksheet import Sheet

from . import moduleFrame
from .style import padding
from .table import ButtonFrame

Params = namedtuple(
    "Params",
    ("yQuantity", "yUnit", "xQuantity", "xUnit"),
    defaults=[""] * 4,
)

predefinedParams = {
    "UV-Vis": Params("Abs", "AU", "λ", "nm"),
    "NMR": Params("δ", "ppm"),
}


class EditDataPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter data")

        frame = ttk.Frame(self, padding=15)
        frame.pack(expand=True, fill="both")

        paramsFrame = ttk.Frame(frame)
        paramsFrame.pack(expand=False, fill="both")

        paramsFrameLeft = ttk.Frame(paramsFrame)
        paramsFrameLeft.grid(row=0, column=0, sticky="ne", padx=5, pady=5)
        paramsFrame.grid_columnconfigure(0, weight=1)

        self.hasAdditionTitles = tk.BooleanVar()
        self.additionTitlesCheckbutton = ttk.Checkbutton(
            paramsFrameLeft, text="Addition titles", variable=self.hasAdditionTitles
        )
        self.hasSignalTitles = tk.BooleanVar()
        self.signalTitlesCheckbutton = ttk.Checkbutton(
            paramsFrameLeft, text="Signal titles", variable=self.hasSignalTitles
        )

        self.additionsRowsRadiobutton = ttk.Radiobutton(
            paramsFrameLeft, value=0, text="Rows are additions, columns are signals"
        )
        self.additionsColumnsRadiobutton = ttk.Radiobutton(
            paramsFrameLeft, value=1, text="Rows are signals, columns are additions"
        )

        self.additionTitlesCheckbutton.pack(pady=2.5)
        self.signalTitlesCheckbutton.pack(pady=2.5)
        self.additionsRowsRadiobutton.pack(pady=2.5)
        self.additionsColumnsRadiobutton.pack(pady=2.5)

        paramsFrameRight = ttk.Frame(paramsFrame)
        paramsFrameRight.grid(row=0, column=1, sticky="nw", padx=5, pady=5)
        paramsFrame.grid_columnconfigure(1, weight=1)

        self.optionMenuVar = tk.StringVar(self)
        optionMenu = ttk.OptionMenu(
            paramsFrameRight,
            self.optionMenuVar,
            None,
            *predefinedParams.keys(),
            style="Outline.TMenubutton",
            command=self.setParams
        )
        optionMenu.configure(width=max([len(s) for s in predefinedParams]) + 1)
        optionMenu.grid(row=0, columnspan=2, pady=2.5)

        self.yQuantityLabel = ttk.Label(paramsFrameRight, text="Measured quantity:")
        self.yQuantityLabel.grid(row=1, column=0, sticky="w")
        self.yUnitLabel = ttk.Label(paramsFrameRight, text="Unit:")
        self.yUnitLabel.grid(row=1, column=1, sticky="w")
        self.yQuantity = tk.StringVar(self)
        self.yUnit = tk.StringVar(self)
        self.yQuantityWidget = ttk.Entry(paramsFrameRight, textvariable=self.yQuantity)
        self.yQuantityWidget.grid(row=2, column=0, sticky="w")
        self.yUnitWidget = ttk.Entry(
            paramsFrameRight, width=10, textvariable=self.yUnit
        )
        self.yUnitWidget.grid(row=2, column=1, sticky="w")

        self.xQuantityLabel = ttk.Label(
            paramsFrameRight, text="Continuous signals x-axis quantity:"
        )
        self.xQuantityLabel.grid(row=3, column=0, sticky="w")
        self.xUnitLabel = ttk.Label(paramsFrameRight, text="Unit:")
        self.xUnitLabel.grid(row=3, column=1, sticky="w")
        self.xQuantity = tk.StringVar(self)
        self.xUnit = tk.StringVar(self)
        self.xQuantityWidget = ttk.Entry(paramsFrameRight, textvariable=self.xQuantity)
        self.xQuantityWidget.grid(row=4, column=0, sticky="w")
        self.xUnitWidget = ttk.Entry(
            paramsFrameRight, width=10, textvariable=self.xUnit
        )
        self.xUnitWidget.grid(row=4, column=1, sticky="w")

        self.sheet = Sheet(
            frame,
            data=[[]],
            expand_sheet_if_paste_too_big=True,
        )

        self.sheet.pack(side="top", expand=True, fill="both")
        self.sheet.enable_bindings()

        buttonFrame = ButtonFrame(self, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

        loadButton = ttk.Button(buttonFrame, text="Load from CSV", command=self.loadCSV)
        loadButton.pack(side="left", padx=padding)

        self.populateDefault()

    def populateDefault(self):
        titration = self.titration
        self.hasAdditionTitles.set(titration.hasAdditionTitles)
        self.hasSignalTitles.set(titration.hasSignalTitles)

        if not self.titration.transposeData:
            self.additionsRowsRadiobutton.invoke()
        else:
            self.additionsColumnsRadiobutton.invoke()

        self.optionMenuVar.set("")

        for param in Params._fields:
            if hasattr(titration, param):
                getattr(self, param).set(getattr(titration, param))
            else:
                getattr(self, param).set("")

        data = titration.rawData.copy()
        if data.shape == (0, 0):
            data = np.full((16, 5), "")
        else:
            formattedData = data.astype(str)
            formattedData[np.isnan(data)] = ""
            data = formattedData
        if titration.hasAdditionTitles and titration.hasSignalTitles:
            data = np.c_[titration.additionTitles, data]
            data = np.r_[[np.insert(titration.signalTitlesStrings, 0, "")], data]
        elif titration.hasAdditionTitles:
            data = np.c_[titration.additionTitles, data]
        elif titration.hasSignalTitles:
            data = np.r_[titration.signalTitlesStrings, data]

        if titration.transposeData:
            data = data.T
        self.sheet.set_sheet_data(data.tolist())

    def setParams(self, selection):
        params = predefinedParams[selection]
        for k, v in params._asdict().items():
            if v is not None:
                getattr(self, k).set(v)

    def reset(self):
        self.populateDefault()

    def processData(self):
        titration = self.titration
        data = np.array(self.sheet.get_sheet_data())
        data = data[~np.all(data == "", 1), :][:, ~np.all(data == "", 0)]

        titration.hasSignalTitles = self.signalTitlesCheckbutton.instate(["selected"])
        titration.hasAdditionTitles = self.additionTitlesCheckbutton.instate(
            ["selected"]
        )
        titration.transposeData = self.additionsColumnsRadiobutton.instate(["selected"])

        if titration.transposeData:
            data = data.T

        if titration.hasAdditionTitles and titration.hasSignalTitles:
            titration.additionTitles = data[1:, 0]
            titration.signalTitles = data[0, 1:]
            rawData = data[1:, 1:]
        elif titration.hasAdditionTitles:
            titration.additionTitles = data[:, 0]
            rawData = data[:, 1:]
        elif titration.hasSignalTitles:
            titration.signalTitles = data[0, :]
            rawData = data[1:, :]
        else:
            rawData = data

        rawData[rawData == ""] = "nan"
        return ma.masked_invalid(rawData.astype(float))

    def saveData(self):
        self.titration.rawData = self.processData()
        for param in Params._fields:
            setattr(self.titration, param, getattr(self, param).get())

        self.saved = True
        self.destroy()

    def loadCSV(self):
        fileType = tk.StringVar(self)
        filePath = fd.askopenfilename(
            master=self,
            title="Load from CSV",
            filetypes=[("All files", "*.*"), ("CSV files", "*.csv")],
            typevariable=fileType,
        )
        if filePath == "":
            return
        with open(filePath) as file:
            d = csv.Sniffer().sniff(file.readline() + file.readline())
            file.seek(0)
            data = list(csv.reader(file, dialect=d))
        self.sheet.set_sheet_data(data)
