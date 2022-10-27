import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as mb
from decimal import Decimal

import re
import numpy as np

from . import moduleFrame
from .table import Table, ButtonFrame
from .scrolledFrame import ScrolledFrame

prefixesDecimal = {
    "": Decimal(1),
    "m": Decimal(1e-3),
    "u": Decimal(1e-6),
    "μ": Decimal(1e-6),
    "n": Decimal(1e-9),
}

prefixes = dict([key, float(value)] for key, value in prefixesDecimal.items())


def convertConc(conc, fromUnit, toUnit):
    if np.isnan(conc):
        return ""
    conc = Decimal(conc)
    convertedConc = float(
        conc * prefixesDecimal[fromUnit.strip("M")] / prefixesDecimal[toUnit.strip("M")]
    )
    return f"{convertedConc:g}"  # strip trailing zeroes


class StockTable(Table):
    def __init__(self, master, titration):
        if hasattr(titration, "stockTitles"):
            stockTitles = titration.stockTitles
        else:
            stockTitles = ("Stock 1", "Stock 2")
        super().__init__(
            master,
            2,
            0,
            stockTitles,
            allowBlanks=True,
            rowOptions=("readonlyTitles", "delete"),
            columnOptions=("titles", "new", "delete"),
        )

        self.titration = titration

        self.label(0 - self.headerGridRows, 0, "Stock concentrations:", 4)
        self.label(1 - self.headerGridRows, 2, "Unit:")
        _, self.unit = self.dropdown(
            1 - self.headerGridRows, 3, ("nM", "μM", "mM", "M"), "mM"
        )
        if hasattr(titration, "concsUnit"):
            self.unit.set(titration.concsUnit)

        if hasattr(titration, "stockConcs"):
            self.populate(titration.stockConcs)
        else:
            self.populateDefault()

    def deleteRowButton(self, *args, **kwargs):
        button = super().deleteRowButton(*args, **kwargs)
        button.state(["disabled"])
        return button

    def populate(self, stockConcs):
        for name, row in zip(self.titration.freeNames, stockConcs):
            self.addRow(name, [convertConc(conc, "M", self.unit.get()) for conc in row])

    def populateDefault(self):
        for name in self.titration.freeNames:
            self.addRow(name)


class VolumesTable(Table):
    def __init__(self, master, titration):
        if hasattr(titration, "stockTitles"):
            stockTitles = titration.stockTitles
        else:
            stockTitles = ("Stock 1", "Stock 2")
        super().__init__(
            master,
            2,
            2,
            stockTitles,
            allowBlanks=False,
            rowOptions=("delete", "readonlyTitles"),
            columnOptions=(),
        )

        self.titration = titration

        self.label(0 - self.headerGridRows, 0, "Cumulative addition volumes:", 4)
        self.label(1 - self.headerGridRows, 2, "Unit:")
        _, self.unit = self.dropdown(
            1 - self.headerGridRows, 3, ("nL", "μL", "mL", "L"), "μL"
        )
        if hasattr(titration, "volumesUnit"):
            self.unit.set(titration.volumesUnit)

        self.label(1, 1, "Addition title:")

        if hasattr(titration, "volumes"):
            self.populate(titration.volumes)
        else:
            self.populateDefault()

    def populate(self, volumes):
        for name, row in zip(self.titration.processedAdditionTitles, volumes):
            self.addRow(
                name,
                [self.convertVolume(volume, "L", self.unit.get()) for volume in row],
            )

    def populateDefault(self):
        for name in self.titration.additionTitles:
            self.addRow(name)

    def addColumn(self, firstEntry="", data=None):
        super().addColumn(firstEntry, data)
        column = self.cells.shape[1] - 1
        copyFirstButton = self.button(0, column, "Copy first")
        copyFirstButton.configure(
            command=lambda button=copyFirstButton: self.copyFirst(
                button.grid_info()["column"]
            )
        )
        self.cells[0, column] = copyFirstButton

        copyTitlesButton = self.button(1, column, "Copy from titles")
        copyTitlesButton.configure(
            command=lambda button=copyTitlesButton: self.copyFromTitles(
                button.grid_info()["column"]
            )
        )
        self.cells[1, column] = copyTitlesButton

    def copyFirst(self, column):
        cells = self.cells[self.headerCells :, column]
        first = cells[0].get()
        for cell in cells:
            cell.set(first)

    def copyFromTitles(self, column):
        cells = self.cells[self.headerCells :]
        for row in cells:
            title = row[1].get()
            volume = self.getVolumeFromString(title, self.unit.get())
            if volume is not None:
                row[column].set(volume)

    def getVolumeFromString(self, string, toUnit="L"):
        searchResult = re.search(r"([0-9.]+) ?([nuμm]?)[lL]", string)
        if not searchResult:
            return None
        volume, prefix = searchResult.group(1, 2)
        return self.convertVolume(volume, prefix, toUnit)

    def convertVolume(self, volume, fromUnit, toUnit):
        volume = Decimal(volume)
        convertedVolume = float(
            volume
            * prefixesDecimal[fromUnit.strip("L")]
            / prefixesDecimal[toUnit.strip("L")]
        )
        return f"{convertedVolume:g}"  # strip trailing zeroes


class VolumesPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter volumes")

        height = int(self.master.winfo_height() * 0.8)
        frame = ScrolledFrame(self, height=height, max_width=1500)
        frame.pack(expand=True, fill="both")

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        unknownConcsFrame = ttk.Frame(innerFrame, borderwidth=5)
        unknownConcsFrame.pack(expand=True, fill="both")
        unknownConcsLabel = ttk.Label(
            unknownConcsFrame, text="Leave cells blank for unknown concentrations."
        )
        unknownConcsLabel.pack()
        self.unknownTotalConcsLinkedVar = tk.BooleanVar()
        if hasattr(titration, "unknownTotalConcsLinked"):
            self.unknownTotalConcsLinkedVar.set(self.titration.unknownTotalConcsLinked)
        else:
            self.unknownTotalConcsLinkedVar.set(True)
        unknownTotalConcsCheckbutton = ttk.Checkbutton(
            unknownConcsFrame,
            variable=self.unknownTotalConcsLinkedVar,
            text="Link unknown concentrations for the same species in different stocks",
        )
        unknownTotalConcsCheckbutton.pack()

        self.stockTable = StockTable(innerFrame, titration)
        self.stockTable.pack(expand=True, fill="both")
        self.volumesTable = VolumesTable(innerFrame, titration)
        self.volumesTable.pack(expand=True, fill="both")

        self.stockTable.newColumnButton.configure(command=self.addColumns)
        self.stockTable._deleteColumn = self.stockTable.deleteColumn
        self.stockTable.deleteColumn = self.deleteColumns

        buttonFrame = ButtonFrame(innerFrame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both")

    def addColumns(self):
        self.stockTable.addColumn()
        self.volumesTable.addColumn()

    def deleteColumns(self, column):
        self.stockTable._deleteColumn(column)
        self.volumesTable.deleteColumn(column)

    def reset(self):
        for table in (self.stockTable, self.volumesTable):
            table.resetData()
            table.columnTitles = ("Stock 1", "Stock 2")
            table.populateDefault()

    def saveData(self):
        try:
            stockTitles = self.stockTable.columnTitles
            stockConcs = self.stockTable.data
            volumes = self.volumesTable.data
        except Exception as e:
            mb.showerror(title="Could not save data", message=e, parent=self)
            return

        self.titration.stockTitles = stockTitles
        self.titration.unknownTotalConcsLinked = self.unknownTotalConcsLinkedVar.get()

        concsUnit = self.stockTable.unit.get()
        self.titration.concsUnit = concsUnit
        self.titration.stockConcs = stockConcs * prefixes[concsUnit.strip("M")]

        volumesUnit = self.volumesTable.unit.get()
        self.titration.volumesUnit = volumesUnit
        self.titration.volumes = volumes * prefixes[volumesUnit.strip("L")]

        self.titration.rowFilter = np.in1d(
            self.titration.additionTitles, self.volumesTable.rowTitles
        )

        # Calculate and save total concentrations if no stock concentrations
        # are unknown, to transfer them to the ConcsPopup.
        if np.count_nonzero(np.isnan(self.titration.stockConcs)) == 0:
            moles = self.titration.volumes @ self.titration.stockConcs.T
            totalVolumes = np.atleast_2d(np.sum(self.titration.volumes, 1)).T
            self.titration.totalConcs = moles / totalVolumes
        elif hasattr(self.titration, "totalConcs"):
            # TODO: Find a way to store totalConcs in the options file, only if they're
            # present
            del self.titration.totalConcs

        self.saved = True
        self.destroy()


class ConcsTable(Table):
    # TODO: merge with VolumesTable
    def __init__(self, master, titration):
        self.titration = titration

        super().__init__(
            master,
            2,
            2,
            titration.freeNames,
            allowBlanks=False,
            rowOptions=("delete", "readonlyTitles"),
            columnOptions=("readonlyTitles",),
        )

        self.label(0 - self.headerGridRows, 0, "Concentrations:", 4)
        self.label(1 - self.headerGridRows, 2, "Unit:")
        _, self.unit = self.dropdown(
            1 - self.headerGridRows, 3, ("nM", "μM", "mM", "M"), "mM"
        )
        if hasattr(titration, "concsUnit"):
            self.unit.set(titration.concsUnit)

        self.label(self.headerCells - 1, 1, "Addition title:")

        if hasattr(titration, "totalConcs"):
            self.populate(titration.totalConcs)
        else:
            self.populateDefault()

    def populate(self, concs):
        for name, row in zip(self.titration.processedAdditionTitles, concs):
            self.addRow(name, [convertConc(conc, "M", self.unit.get()) for conc in row])

    def populateDefault(self):
        for name in self.titration.additionTitles:
            self.addRow(name)

    def addColumn(self, firstEntry="", data=None):
        super().addColumn(firstEntry, data)
        column = self.cells.shape[1] - 1
        copyFirstButton = self.button(0, column, "Copy first")
        copyFirstButton.configure(
            command=lambda button=copyFirstButton: self.copyFirst(
                button.grid_info()["column"]
            )
        )
        self.cells[0, column] = copyFirstButton

        copyTitlesButton = self.button(1, column, "Copy from titles")
        copyTitlesButton.configure(
            command=lambda button=copyTitlesButton: self.copyFromTitles(
                button.grid_info()["column"]
            )
        )
        self.cells[1, column] = copyTitlesButton

    def copyFirst(self, column):
        cells = self.cells[self.headerCells :, column]
        first = cells[0].get()
        for cell in cells:
            cell.set(first)

    def copyFromTitles(self, column):
        cells = self.cells[self.headerCells :]
        for row in cells:
            title = row[1].get()
            conc = self.getConcFromString(title, self.unit.get())
            if conc is not None:
                row[column].set(conc)

    def getConcFromString(self, string, toUnit="M"):
        searchResult = re.search(r"([0-9.]+) ?([nuμm]?)M", string)
        if not searchResult:
            return None
        conc, prefix = searchResult.group(1, 2)
        return convertConc(conc, prefix, toUnit)


class ConcsPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter concentrations")

        height = int(self.master.winfo_height() * 0.8)
        frame = ScrolledFrame(self, height=height, max_width=1500)
        frame.pack(expand=True, fill="both")

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        self.concsTable = ConcsTable(innerFrame, titration)
        self.concsTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(innerFrame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both")

    def reset(self):
        self.concsTable.resetData()
        self.concsTable.populateDefault()

    def saveData(self):
        try:
            totalConcs = self.concsTable.data
        except Exception as e:
            mb.showerror(title="Could not save data", message=e, parent=self)
            return

        concsUnit = self.concsTable.unit.get()
        self.titration.concsUnit = concsUnit
        self.titration.totalConcs = totalConcs * prefixes[concsUnit.strip("M")]

        self.titration.rowFilter = np.in1d(
            self.titration.additionTitles, self.concsTable.rowTitles
        )

        self.saved = True
        self.destroy()


class GetTotalConcsFromVolumes(moduleFrame.Strategy):
    Popup = VolumesPopup
    popupAttributes = (
        "stockTitles",
        "unknownTotalConcsLinked",
        "concsUnit",
        "stockConcs",
        "volumesUnit",
        "volumes",
    )

    def __init__(self, titration):
        self.titration = titration
        titration.getConcVarsCount = self.getConcVarsCount
        titration.getConcVarsNames = self.getConcVarsNames

    def __call__(self, totalConcVars):
        titration = self.titration
        stockConcs = np.copy(titration.stockConcs)
        if titration.unknownTotalConcsLinked:
            # For each row (= species), all blank cells are assigned to a
            # single unknown variable.
            for rowIndex, totalConcVar in zip(
                np.where(self.rowsWithBlanks)[0], totalConcVars
            ):
                stockConcs[rowIndex, np.isnan(stockConcs[rowIndex])] = totalConcVar
        else:
            stockConcs[np.isnan(stockConcs)] = totalConcVars

        moles = titration.volumes @ stockConcs.T
        totalVolumes = np.atleast_2d(np.sum(titration.volumes, 1)).T
        totalConcs = moles / totalVolumes

        return totalConcs

    @property
    def rowsWithBlanks(self):
        return np.isnan(np.sum(self.titration.stockConcs, 1))

    def getConcVarsNames(self):
        if self.titration.unknownTotalConcsLinked:
            # return the number of rows (= species) with blank cells
            concVarsNames = self.titration.freeNames[self.rowsWithBlanks]
            return np.array([f"[{name}]" for name in concVarsNames])
        else:
            concVarsNames = []
            for freeName, concs in zip(
                self.titration.freeNames, self.titration.stockConcs
            ):
                concVarsNames.extend(
                    [
                        f"[{freeName}] in {stock}"
                        for stock in self.titration.stockTitles[np.isnan(concs)]
                    ]
                )
            return np.array(concVarsNames)

    def getConcVarsCount(self):
        if self.titration.unknownTotalConcsLinked:
            # return the number of rows (= species) with blank cells
            return np.count_nonzero(self.rowsWithBlanks)
        else:
            return np.count_nonzero(np.isnan(self.titration.stockConcs))


class GetTotalConcs(moduleFrame.Strategy):
    Popup = ConcsPopup
    popupAttributes = (
        "concsUnit",
        "totalConcs",
    )

    def __init__(self, titration):
        self.titration = titration
        titration.getConcVarsCount = self.getConcVarsCount

    def __call__(self, totalConcVars):
        return self.titration.totalConcs

    def getConcVarsCount(self):
        return 0


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Total concentrations"
    dropdownLabelText = "Enter concentrations or volumes:"
    dropdownOptions = {
        "Volumes": GetTotalConcsFromVolumes,
        "Concentrations": GetTotalConcs,
    }
    attributeName = "getTotalConcs"
    setDefault = False
