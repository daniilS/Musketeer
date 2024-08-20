import tkinter as tk
import tkinter.filedialog as fd
import tkinter.ttk as ttk
import warnings
from collections import namedtuple

import numpy as np
from numpy import ma
from tksheet import Sheet

from . import moduleFrame
from . import titrationReader
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
        self.title("Enter/edit spectroscopic data")

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

        self.additionTitlesCheckbutton.pack(pady=2.5, fill="x")
        self.signalTitlesCheckbutton.pack(pady=2.5, fill="x")
        self.additionsRowsRadiobutton.pack(pady=2.5, fill="x")
        self.additionsColumnsRadiobutton.pack(pady=2.5, fill="x")

        paramsFrameRight = ttk.Frame(paramsFrame)
        paramsFrameRight.grid(row=0, column=1, sticky="nw", padx=5, pady=5)
        paramsFrame.grid_columnconfigure(1, weight=1)

        optionMenuLabel = ttk.Label(paramsFrameRight, text="Autofill quantities/units:")
        optionMenuLabel.grid(row=0, column=0, sticky="w")

        self.optionMenuVar = tk.StringVar(self)
        optionMenu = ttk.OptionMenu(
            paramsFrameRight,
            self.optionMenuVar,
            None,
            *predefinedParams.keys(),
            style="Outline.TMenubutton",
            command=self.setParams,
        )
        optionMenu.configure(width=max([len(s) for s in predefinedParams]) + 1)
        optionMenu.grid(row=0, column=1, pady=2.5)

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

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.sheet = Sheet(
                frame,
                data=[[]],
                expand_sheet_if_paste_too_big=True,
            )

        self.sheet.pack(side="top", expand=True, fill="both")
        self.sheet.enable_bindings()

        buttonFrame = ButtonFrame(self, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

        loadButton = ttk.Button(
            buttonFrame, text="Import from file", command=self.loadCSV
        )
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
            data = np.r_[[titration.signalTitlesStrings], data]

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
        if not titration.hasSignalTitles:
            titration.continuous = False
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

        rawData = rawData.astype(object)  # to allow setting values to "nan"
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
        fileReaders = titrationReader.fileReaders
        filePath = fd.askopenfilename(
            title="Import spectroscopic data from file",
            filetypes=fileReaders[:, :-1].tolist(),
            typevariable=fileType,
        )
        if filePath == "":
            return

        fileReader = fileReaders[fileReaders[:, 0] == fileType.get(), -1].item()
        data, additionTitles, signalTitles, defaultParams = fileReader(filePath, self)

        if (additionTitles is not None) and (signalTitles is not None):
            data = np.c_[additionTitles, data]
            data = np.r_[[np.insert(signalTitles, 0, "")], data]
            self.hasAdditionTitles.set(True)
            self.hasSignalTitles.set(True)
        elif additionTitles is not None:
            data = np.c_[additionTitles, data]
            self.hasAdditionTitles.set(True)
            self.hasSignalTitles.set(False)
        elif signalTitles is not None:
            data = np.r_[[signalTitles], data]
            self.hasAdditionTitles.set(False)
            self.hasSignalTitles.set(True)
        else:
            self.hasAdditionTitles.set(False)
            self.hasSignalTitles.set(False)

        if defaultParams is not None:
            self.optionMenuVar.set(defaultParams)
            self.setParams(defaultParams)

        self.additionsRowsRadiobutton.invoke()

        self.sheet.set_sheet_data(data.tolist())
