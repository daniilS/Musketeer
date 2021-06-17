import tkinter as tk
import tkinter.ttk as ttk
from decimal import Decimal

import re
import numpy as np

from . import moduleFrame
from . import table
from .scrolledFrame import ScrolledFrame

prefixesDecimal = {
    "": Decimal(1),
    "m": Decimal(1e-3),
    "u": Decimal(1e-6),
    "μ": Decimal(1e-6),
    "n": Decimal(1e-9)
}

prefixes = dict([key, float(value)] for key, value in prefixesDecimal.items())


def getVolumeFromString(string, unit="L"):
    searchResult = re.search(r"([0-9.]+) ?([nuμm]?)[lL]", string)
    if not searchResult:
        return None
    volume, prefix = searchResult.group(1, 2)
    volume = Decimal(volume)
    convertedVolume = float(
        volume * prefixesDecimal[prefix] / prefixesDecimal[unit.strip("L")]
    )
    return f"{convertedVolume:g}"  # strip trailing zeroes


class StockTable(table.Table):
    def __init__(self, master, titration):
        self.headerRows = 3
        self.dataColumns = 2
        super().__init__(master)

        self.label(0, 0, "Stock concentrations:", 4)
        self.label(1, 2, "Unit:")
        _, self.unit = self.dropdown(1, 3, ("nm", "\u03BCM", "mM", "M"), "mM")

        self.label(2, 1, "Species:")
        self.entry(2, 2, "Stock 1")
        self.entry(2, 3, "Stock 2")

        for name in titration.freeNames:
            self.addRow(name)


class VolumesTable(table.Table):
    def __init__(self, master, titration):
        self.headerRows = 4
        self.dataColumns = 2
        super().__init__(master)

        self.label(0, 0, "Addition volumes:", 4)
        self.label(1, 2, "Unit:")
        _, self.unit = self.dropdown(
            1, 3, ("nL", "\u03BCL", "mL", "L"), "\u03BCL"
        )

        self.label(3, 1, "Addition title:")

        for stock in range(self.dataColumns):
            self.button(
                2, stock + 2, "Copy first",
                lambda stock=stock: self.copyFirst(stock)
            )
            self.button(
                3, stock + 2, "Copy from titles",
                lambda stock=stock: self.copyFromTitles(stock)
            )

        for name in titration.additionTitles:
            self.addRow(name)

    def copyFirst(self, dataColumn):
        rows, _ = self.data.shape
        first = self.data[0, dataColumn + 2].get()
        for row in range(rows):
            if self.data[row, dataColumn + 2] is not None:
                self.data[row, dataColumn + 2].set(first)

    def copyFromTitles(self, dataColumn):
        rows, _ = self.data.shape
        for row in range(rows):
            if self.data[row, dataColumn + 2] is not None:
                title = self.data[row, 1].get()
                volume = getVolumeFromString(title, self.unit.get())
                if volume is not None:
                    self.data[row, dataColumn + 2].set(volume)


def saveData(stockTable, volumesTable, titration, popup):
    stockConcs = []
    for row in stockTable.data:
        if row[0] is None:
            continue
        rowData = []
        for stock in range(stockTable.dataColumns):
            rowData.append(row[stock + 2].get())
        stockConcs.append(rowData)
    stockConcs = np.array(stockConcs, dtype=float) * prefixes[
        stockTable.unit.get().strip("M")
    ]

    volumes = []
    for row in volumesTable.data:
        if row[0] is None:
            continue
        rowData = []
        for stock in range(volumesTable.dataColumns):
            rowData.append(row[stock + 2].get())
        volumes.append(rowData)
    volumes = np.array(volumes, dtype=float) * prefixes[
        volumesTable.unit.get().strip("L")
    ]

    moles = volumes @ stockConcs.T
    totalVolumes = np.atleast_2d(np.sum(volumes, 1)).T
    titration.totalConcs = moles / totalVolumes

    popup.destroy()


class GetTotalConcsFromVolumes():
    def __init__(self, titration):
        self.titration = titration
        popup = tk.Toplevel()
        popup.title("Enter volumes")
        popup.grab_set()

        frame = ScrolledFrame(popup, height=900, max_width=1500)
        frame.pack(expand=True, fill="both")
        frame.bind_arrow_keys(popup)
        frame.bind_scroll_wheel(popup)

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        stockTable = StockTable(innerFrame, titration)
        stockTable.pack(expand=True, fill="both")
        volumesTable = VolumesTable(innerFrame, titration)
        volumesTable.pack(expand=True, fill="both")
        buttonFrame = ttk.Frame(innerFrame, borderwidth=5)
        buttonFrame.pack(expand=True, fill="both")
        saveButton = ttk.Button(
            buttonFrame, text="Save", command=lambda: saveData(
                stockTable, volumesTable, titration, popup
            )
        )
        saveButton.pack()

        popup.wait_window(popup)

    def __call__(self, totalConcVars):
        # TODO: implement unknown concentrations
        return self.titration.totalConcs


class GetTotalConcs():
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, totalConcVars):
        # TODO: implement unknown concentrations
        return self.titration.totalConcs


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Total concentrations"
    dropdownLabelText = "Enter concentrations or volumes:"
    dropdownOptions = {
        "Volumes": GetTotalConcsFromVolumes,
        "Concentrations": GetTotalConcs
    }
    attributeName = "getTotalConcs"
    setDefault = False
