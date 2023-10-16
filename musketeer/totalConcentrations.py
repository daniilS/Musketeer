import re
import tkinter as tk
import tkinter.ttk as ttk
from abc import abstractmethod
from decimal import Decimal

import numpy as np
from numpy import ma

from . import moduleFrame
from .scrolledFrame import ScrolledFrame
from .table import ButtonFrame, Table, WrappedLabel

DEFAULT_INITIAL_CONC = 1e-7

prefixesDecimal = {
    "": Decimal(1),
    "m": Decimal(1e-3),
    "u": Decimal(1e-6),
    "μ": Decimal(1e-6),
    "n": Decimal(1e-9),
}

prefixes = dict([key, float(value)] for key, value in prefixesDecimal.items())


def convertConc(conc, fromUnit, toUnit):
    if conc is ma.masked:
        return ""
    conc = Decimal(conc)
    convertedConc = float(
        conc * prefixesDecimal[fromUnit.strip("M")] / prefixesDecimal[toUnit.strip("M")]
    )
    return f"{convertedConc:g}"  # strip trailing zeroes


class totalConcentrations(moduleFrame.Strategy):
    requiredAttributes = (
        "concsUnit",
        "totalConcs",
        "freeNames",
        "variableNames",
    )

    # TODO: support entering initial guesses
    @property
    def variableInitialGuesses(self):
        return np.full(len(self.variableNames), DEFAULT_INITIAL_CONC)

    @property
    def freeCount(self):
        return len(self.freeNames)

    @abstractmethod
    def run(self, totalConcVars):
        pass


class StockTable(Table):
    def __init__(self, master, titration):
        try:
            stockTitles = titration.totalConcentrations.stockTitles
        except AttributeError:
            stockTitles = ("Stock 1", "Stock 2")

        try:
            freeNames = titration.totalConcentrations.freeNames
        except AttributeError:
            freeNames = ("Host", "Guest")

        super().__init__(
            master,
            2,
            0,
            stockTitles,
            maskBlanks=True,
            rowOptions=("titles", "new", "delete"),
            columnOptions=("titles", "new", "delete"),
        )

        self.titration = titration

        self.label(0 - self.headerGridRows, 0, "Stock concentrations:", 4)
        self.label(1 - self.headerGridRows, 2, "Unit:")
        _, self.concsUnit = self.dropdown(
            1 - self.headerGridRows, 3, ("nM", "μM", "mM", "M"), "mM"
        )
        try:
            self.concsUnit.set(titration.totalConcentrations.concsUnit)
        except AttributeError:
            pass

        try:
            self.populate(freeNames, titration.totalConcentrations.stockConcs)
        except AttributeError:
            self.populateDefault(freeNames)

    def populate(self, freeNames, stockConcs):
        for name, row in zip(freeNames, stockConcs):
            self.addRow(
                name, [convertConc(conc, "M", self.concsUnit.get()) for conc in row]
            )

    def populateDefault(self, freeNames):
        for name in freeNames:
            self.addRow(name)


class VolumesTable(Table):
    def __init__(self, master, titration):
        try:
            stockTitles = titration.totalConcentrations.stockTitles
        except AttributeError:
            stockTitles = ("Stock 1", "Stock 2")
        super().__init__(
            master,
            2,
            2,
            stockTitles,
            rowOptions=("readonlyTitles", "delete"),
            columnOptions=(),
        )

        self.titration = titration

        self.label(0 - self.headerGridRows, 0, "Cumulative addition volumes:", 4)
        self.label(1 - self.headerGridRows, 2, "Unit:")
        _, self.volumesUnit = self.dropdown(
            1 - self.headerGridRows, 3, ("nL", "μL", "mL", "L"), "μL"
        )
        try:
            self.volumesUnit.set(titration.totalConcentrations.volumesUnit)
        except AttributeError:
            pass

        self.readonlyEntry(self.headerCells - 1, 1, "Addition title:", align="left")

        if (
            self.titration.totalConcentrations is not None
            and hasattr(titration.totalConcentrations, "volumes")
            and (
                self.titration.totalConcentrations.volumes.shape[0]
                == len(self.titration.additionTitles)
            )
        ):
            self.populate(titration.totalConcentrations.volumes)
        else:
            self.populateDefault()

    # TODO: instead make the columnspan of the titles 2
    def deleteRowButton(self, *args, **kwargs):
        button = super().deleteRowButton(*args, **kwargs)
        button.state(["disabled"])
        return button

    def populate(self, volumes):
        for name, row in zip(self.titration.additionTitles, volumes):
            self.addRow(
                name,
                [
                    self.convertVolume(volume, "L", self.volumesUnit.get())
                    for volume in row
                ],
            )

    def populateDefault(self):
        for name in self.titration.additionTitles:
            self.addRow(name)

    def addColumn(self, firstEntry="", data=None):
        super().addColumn(firstEntry, data)
        column = self.cells.shape[1] - 1
        copyFirstButton = self.button(self.headerCells - 2, column, "Copy first")
        copyFirstButton.configure(
            command=lambda button=copyFirstButton: self.copyFirst(
                button.grid_info()["column"]
            )
        )
        self.cells[self.headerCells - 2, column] = copyFirstButton

        copyTitlesButton = self.button(self.headerCells - 1, column, "Copy from titles")
        copyTitlesButton.configure(
            command=lambda button=copyTitlesButton: self.copyFromTitles(
                button.grid_info()["column"]
            )
        )
        self.cells[self.headerCells - 1, column] = copyTitlesButton

    def copyFirst(self, column):
        cells = self.cells[self.headerCells :, column]
        first = cells[0].get()
        for cell in cells:
            cell.set(first)

    def copyFromTitles(self, column):
        cells = self.cells[self.headerCells :]
        for row in cells:
            title = row[1].get()
            volume = self.getVolumeFromString(title, self.volumesUnit.get())
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
        frame = ScrolledFrame(
            self,
            height=height,
            max_width=self.winfo_toplevel().master.winfo_width() - 200,
        )
        frame.pack(expand=True, fill="both")

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        unknownConcsFrame = ttk.Frame(innerFrame, borderwidth=5)
        unknownConcsFrame.pack(expand=True, fill="both")
        unknownConcsLabel = WrappedLabel(
            unknownConcsFrame,
            text="Leave cells blank to optimise that concentration as a variable.\n",
        )
        unknownConcsLabel.pack(expand=False, fill="both")
        self.unknownTotalConcsLinkedVar = tk.BooleanVar()
        try:
            self.unknownTotalConcsLinkedVar.set(
                self.titration.totalConcentrations.unknownTotalConcsLinked
            )
        except AttributeError:
            self.unknownTotalConcsLinkedVar.set(True)
        unknownTotalConcsCheckbutton = ttk.Checkbutton(
            unknownConcsFrame,
            variable=self.unknownTotalConcsLinkedVar,
            text="Link unknown concentrations in the same row?",
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
        self.freeNames = self.stockTable.rowTitles

        self.stockTitles = self.stockTable.columnTitles
        self.unknownTotalConcsLinked = self.unknownTotalConcsLinkedVar.get()

        self.concsUnit = self.stockTable.concsUnit.get()
        self.stockConcs = self.stockTable.data * prefixes[self.concsUnit.strip("M")]

        self.volumesUnit = self.volumesTable.volumesUnit.get()
        self.volumes = self.volumesTable.data * prefixes[self.volumesUnit.strip("L")]

        self.saved = True
        self.destroy()


class GetTotalConcsFromVolumes(totalConcentrations):
    Popup = VolumesPopup
    popupAttributes = (
        "stockTitles",
        "unknownTotalConcsLinked",
        "concsUnit",
        "stockConcs",
        "volumesUnit",
        "volumes",
        "freeNames",
    )

    def run(self, totalConcVars):
        stockConcs = np.copy(self.stockConcs)
        if self.unknownTotalConcsLinked:
            # For each row (= species), all blank cells are assigned to a
            # single unknown variable.
            for rowIndex, totalConcVar in zip(
                np.where(self.rowsWithBlanks)[0], totalConcVars
            ):
                stockConcs[rowIndex, np.isnan(stockConcs[rowIndex])] = totalConcVar
        else:
            stockConcs[np.isnan(stockConcs)] = totalConcVars

        moles = self.volumes @ stockConcs.T
        totalVolumes = np.atleast_2d(np.sum(self.volumes, 1)).T
        totalConcs = moles / totalVolumes

        return totalConcs

    @property
    def totalConcs(self):
        # If all total concentrations are known, they can be used by other strategies.
        if len(self.variableNames) != 0:
            return np.empty((0, 0))
        else:
            return self.run(np.empty((0,)))

    @property
    def rowsWithBlanks(self):
        return np.any(ma.getmaskarray(self.stockConcs), axis=1)

    @property
    def variableNames(self):
        if self.unknownTotalConcsLinked:
            # return the number of rows (= species) with blank cells
            concVarsNames = self.freeNames[self.rowsWithBlanks]
            return np.array([f"[{name}]" for name in concVarsNames])
        else:
            concVarsNames = []
            for freeName, concs in zip(self.freeNames, self.stockConcs):
                concVarsNames.extend(
                    [
                        f"[{freeName}] in {stock}"
                        for stock in self.stockTitles[ma.getmaskarray(concs)]
                    ]
                )
            return np.array(concVarsNames)


class ConcsTable(Table):
    # TODO: merge with VolumesTable
    def __init__(self, master, titration):
        self.titration = titration

        try:
            freeNames = titration.totalConcentrations.freeNames
        except AttributeError:
            freeNames = ("Host", "Guest")

        super().__init__(
            master,
            2,
            2,
            freeNames,
            maskBlanks=True,
            rowOptions=("readonlyTitles",),
            columnOptions=("titles", "new", "delete"),
        )

        self.populateDefault()

    def populateDefault(self):
        self.label(0 - self.headerGridRows, 0, "Concentrations:", 4)
        self.label(1 - self.headerGridRows, 2, "Unit:")
        _, self.concsUnit = self.dropdown(
            1 - self.headerGridRows, 3, ("nM", "μM", "mM", "M"), "mM"
        )

        self.readonlyEntry(self.headerCells - 1, 1, "Addition title:", align="left")

        if (
            self.titration.totalConcentrations is not None
            and self.titration.totalConcentrations.totalConcs.shape[0]
            == len(self.titration.additionTitles)
        ):
            self.concsUnit.set(self.titration.totalConcentrations.concsUnit)
            for name, row in zip(
                self.titration.additionTitles,
                self.titration.totalConcentrations.totalConcs,
            ):
                self.addRow(
                    name, [convertConc(conc, "M", self.concsUnit.get()) for conc in row]
                )
        else:
            for name in self.titration.additionTitles:
                self.addRow(name)

    def addColumn(self, firstEntry="", data=None):
        super().addColumn(firstEntry, data)
        column = self.cells.shape[1] - 1
        copyFirstButton = self.button(self.headerCells - 2, column, "Copy first")
        copyFirstButton.configure(
            command=lambda button=copyFirstButton: self.copyFirst(
                button.grid_info()["column"]
            )
        )
        self.cells[self.headerCells - 2, column] = copyFirstButton

        copyTitlesButton = self.button(self.headerCells - 1, column, "Copy from titles")
        copyTitlesButton.configure(
            command=lambda button=copyTitlesButton: self.copyFromTitles(
                button.grid_info()["column"]
            )
        )
        self.cells[self.headerCells - 1, column] = copyTitlesButton

    def copyFirst(self, column):
        cells = self.cells[self.headerCells :, column]
        first = cells[0].get()
        for cell in cells:
            cell.set(first)

    def copyFromTitles(self, column):
        cells = self.cells[self.headerCells :]
        for row in cells:
            title = row[1].get()
            conc = self.getConcFromString(title, self.concsUnit.get())
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
        frame = ScrolledFrame(
            self,
            height=height,
            max_width=self.winfo_toplevel().master.winfo_width() - 200,
        )
        frame.pack(expand=True, fill="both")

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        unknownConcsFrame = ttk.Frame(innerFrame, borderwidth=5)
        unknownConcsFrame.pack(expand=True, fill="both")
        unknownConcsLabel = WrappedLabel(
            unknownConcsFrame,
            text="Leave cells blank to optimise that concentration as a variable.\n",
        )
        unknownConcsLabel.pack(expand=False, fill="both")
        self.unknownTotalConcsLinkedVar = tk.BooleanVar()
        try:
            self.unknownTotalConcsLinkedVar.set(
                self.titration.totalConcentrations.unknownTotalConcsLinked
            )
        except AttributeError:
            self.unknownTotalConcsLinkedVar.set(True)
        unknownTotalConcsCheckbutton = ttk.Checkbutton(
            unknownConcsFrame,
            variable=self.unknownTotalConcsLinkedVar,
            text="Link unknown concentrations in the same column?",
        )
        unknownTotalConcsCheckbutton.pack()

        self.concsTable = ConcsTable(innerFrame, titration)
        self.concsTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(innerFrame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both")

    def reset(self):
        self.concsTable.resetData()
        try:
            self.concsTable.columnTitles = self.titration.totalConcentrations.freeNames
        except AttributeError:
            self.concsTable.columnTitles = ("Host", "Guest")
        self.concsTable.populateDefault()

    def saveData(self):
        self.concsUnit = self.concsTable.concsUnit.get()
        self.unknownTotalConcsLinked = self.unknownTotalConcsLinkedVar.get()
        print(self.unknownTotalConcsLinked)
        self.totalConcs = self.concsTable.data * prefixes[self.concsUnit.strip("M")]
        self.freeNames = self.concsTable.columnTitles

        self.saved = True
        self.destroy()


class GetTotalConcs(totalConcentrations):
    Popup = ConcsPopup
    popupAttributes = (
        "unknownTotalConcsLinked",
        "concsUnit",
        "totalConcs",
        "freeNames",
    )

    def run(self, totalConcVars):
        totalConcs = np.copy(self.totalConcs)

        if self.unknownTotalConcsLinked:
            # For each row (= species), all blank cells are assigned to a
            # single unknown variable.
            for columnIndex, totalConcVar in zip(
                np.where(self.columnsWithBlanks)[0], totalConcVars
            ):
                totalConcs[
                    np.isnan(totalConcs[:, columnIndex]), columnIndex
                ] = totalConcVar
        else:
            totalConcs[np.isnan(totalConcs)] = totalConcVars

        return totalConcs

    @property
    def columnsWithBlanks(self):
        return np.any(ma.getmaskarray(self.totalConcs), axis=0)

    @property
    def variableNames(self):
        if self.unknownTotalConcsLinked:
            # return the number of columns (= species) with blank cells
            concVarsNames = self.freeNames[self.columnsWithBlanks]
            return np.array([f"[{name}]" for name in concVarsNames])
        else:
            concVarsNames = []
            for freeName, concs in zip(self.freeNames, self.totalConcs.T):
                concVarsNames.extend(
                    [
                        f"[{freeName}] in {additionTitle}"
                        for additionTitle in self.titration.additionTitles[
                            ma.getmaskarray(concs)
                        ]
                    ]
                )
            return np.array(concVarsNames)


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Experiment"
    dropdownLabelText = "Enter concentrations or volumes:"
    dropdownOptions = {
        "Volumes": GetTotalConcsFromVolumes,
        "Concentrations": GetTotalConcs,
    }
    attributeName = "totalConcentrations"
    setDefault = False
