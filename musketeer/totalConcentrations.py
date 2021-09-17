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


class StockTable(table.Table):
    def __init__(self, master, titration):
        super().__init__(master, 3, 2, False)

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
        super().__init__(master, 4, 2, True)

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
        rows, _ = self.cells.shape
        cells = self.cells[:, dataColumn + 2]
        first = next(cell for cell in cells if cell is not None).get()
        for row in range(rows):
            if self.cells[row, dataColumn + 2] is not None:
                self.cells[row, dataColumn + 2].set(first)

    def copyFromTitles(self, dataColumn):
        rows, _ = self.cells.shape
        for row in range(rows):
            if self.cells[row, dataColumn + 2] is not None:
                title = self.cells[row, 1].get()
                volume = self.getVolumeFromString(title, self.unit.get())
                if volume is not None:
                    self.cells[row, dataColumn + 2].set(volume)

    def getVolumeFromString(self, string, unit="L"):
        searchResult = re.search(r"([0-9.]+) ?([nuμm]?)[lL]", string)
        if not searchResult:
            return None
        volume, prefix = searchResult.group(1, 2)
        volume = Decimal(volume)
        convertedVolume = float(
            volume * prefixesDecimal[prefix] / prefixesDecimal[unit.strip("L")]
        )
        return f"{convertedVolume:g}"  # strip trailing zeroes


class VolumesPopup(tk.Toplevel):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter volumes")
        self.grab_set()

        frame = ScrolledFrame(self, height=900, max_width=1500)
        frame.pack(expand=True, fill="both")
        frame.bind_arrow_keys(self)
        frame.bind_scroll_wheel(self)

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        stockTable = StockTable(innerFrame, titration)
        stockTable.pack(expand=True, fill="both")
        volumesTable = VolumesTable(innerFrame, titration)
        volumesTable.pack(expand=True, fill="both")
        buttonFrame = ttk.Frame(innerFrame, borderwidth=5)
        buttonFrame.pack(expand=True, fill="both")
        saveButton = ttk.Button(
            buttonFrame, text="Save", command=lambda: self.saveData(
                stockTable, volumesTable, titration
            )
        )
        saveButton.pack()

    def saveData(self, stockTable, volumesTable, titration):
        titration.stockConcs = stockTable.data * prefixes[
            stockTable.unit.get().strip("M")
        ]

        titration.volumes = volumesTable.data * prefixes[
            volumesTable.unit.get().strip("L")
        ]
        titration.rowFilter = np.in1d(
            titration.additionTitles, volumesTable.rowTitles
        )

        moles = titration.volumes @ titration.stockConcs.T
        totalVolumes = np.atleast_2d(np.sum(titration.volumes, 1)).T
        titration.totalConcs = moles / totalVolumes

        self.destroy()


class GetTotalConcsFromVolumes(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, totalConcVars):
        # TODO: implement unknown concentrations
        return self.titration.totalConcs

    def showPopup(self):
        popup = VolumesPopup(self.titration)
        popup.wait_window(popup)


class GetTotalConcs(moduleFrame.Strategy):
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
