import re
import tkinter as tk
import tkinter.ttk as ttk
from abc import abstractmethod
from decimal import Decimal

import numpy as np
from numpy import ma

from . import moduleFrame
from . import style
from .scrolledFrame import ScrolledFrame
from .table import ButtonFrame, Table, WrappedLabel

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
        return "?"
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
        return np.full(
            self.variableCount,
            self.defaultInitialGuess,
        )

    @property
    def defaultInitialGuess(self):
        return prefixes[self.concsUnit.strip("M")] * 1.0

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
            allowGuesses=True,
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
        try:
            stockConcsGuesses = self.titration.totalConcentrations.stockConcsGuesses
            assert stockConcsGuesses.shape == stockConcs.shape
        except (AttributeError, AssertionError):
            stockConcsGuesses = ma.masked_all_like(stockConcs)
        for name, row, rowGuesses in zip(freeNames, stockConcs, stockConcsGuesses):
            self.addRow(
                name,
                [
                    convertConc(conc, "M", self.concsUnit.get())
                    if guess is ma.masked
                    else "~" + convertConc(guess, "M", self.concsUnit.get())
                    for conc, guess in zip(row, rowGuesses)
                ],
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
            text='Enter "?" to optimise that concentration as a variable, or enter'
            " ~number to provide an initial guess for the optimisation.\n",
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
        unknownTotalConcsCheckbutton.pack(fill="both", padx=style.padding)

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

        if np.any(self.stockTable.initialGuesses == 0):
            raise ValueError(
                "Initial guesses for stock concentrations cannot be zero, as the "
                "optimisation algorithm optimises the logarithm of the concentrations."
            )
        self.stockConcsGuesses = (
            self.stockTable.initialGuesses * prefixes[self.concsUnit.strip("M")]
        )

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
        "stockConcsGuesses",
        "volumesUnit",
        "volumes",
        "freeNames",
    )

    def run(self, totalConcVars):
        stockConcs = np.copy(self.stockConcs)
        maskArray = ma.getmaskarray(self.stockConcs)

        if self.unknownTotalConcsLinked:
            # For each row (= species), all blank cells are assigned to a
            # single unknown variable.
            for rowIndex, totalConcVar in zip(
                np.where(self.rowsWithBlanks)[0], totalConcVars
            ):
                stockConcs[rowIndex, maskArray[rowIndex, :]] = totalConcVar
        else:
            stockConcs[maskArray] = totalConcVars

        return (self.volumes @ stockConcs.T) / np.sum(
            self.volumes, axis=1, keepdims=True
        )

    @property
    def totalConcs(self):
        # Known total concentrations can be used by other strategies.
        return ma.dot(self.volumes, self.stockConcs.T) / np.sum(
            self.volumes, axis=1, keepdims=True
        )

    @property
    def totalConcsGuesses(self):
        return ma.dot(self.volumes, self.stockConcsGuesses.T) / np.sum(
            self.volumes, axis=1, keepdims=True
        )

    @property
    def variableInitialGuesses(self):
        if self.unknownTotalConcsLinked:
            output = np.empty(self.variableCount)

            for i, row in enumerate(self.stockConcsGuesses[self.rowsWithBlanks, :]):
                rowGuesses = row[~ma.getmaskarray(row)]
                if len(np.unique(rowGuesses)) > 1:
                    raise ValueError(
                        "Multiple different initial guesses entered for "
                        f"{self.variableNames[i]}"
                    )
                elif len(rowGuesses) == 0:
                    output[i] = self.defaultInitialGuess
                else:
                    output[i] = rowGuesses[0]

            return output
        else:
            return self.stockConcsGuesses[ma.getmaskarray(self.stockConcs)].filled(
                self.defaultInitialGuess
            )

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
            1,
            2,
            freeNames,
            maskBlanks=True,
            allowGuesses=True,
            rowOptions=("readonlyTitles",),
            columnOptions=("titles", "new", "delete"),
        )

        self.populateDefault()

    def populateDefault(self):
        self.label(0 - self.headerGridRows, 2, "Unit:")
        _, self.concsUnit = self.dropdown(
            0 - self.headerGridRows, 3, ("nM", "μM", "mM", "M"), "mM"
        )

        self.readonlyEntry(self.headerCells - 1, 1, "Addition title:", align="left")

        if (
            self.titration.totalConcentrations is not None
            and self.titration.totalConcentrations.totalConcs.shape[0]
            == len(self.titration.additionTitles)
        ):
            self.concsUnit.set(self.titration.totalConcentrations.concsUnit)

            try:
                totalConcsGuesses = self.titration.totalConcentrations.totalConcsGuesses
                assert (
                    totalConcsGuesses.shape
                    == self.titration.totalConcentrations.totalConcs.shape
                )
            except (AttributeError, AssertionError):
                totalConcsGuesses = ma.masked_all_like(
                    self.titration.totalConcentrations.totalConcs
                )

            for name, row, rowGuesses in zip(
                self.titration.additionTitles,
                self.titration.totalConcentrations.totalConcs,
                totalConcsGuesses,
            ):
                self.addRow(
                    name,
                    [
                        convertConc(conc, "M", self.concsUnit.get())
                        if guess is ma.masked
                        else "~" + convertConc(guess, "M", self.concsUnit.get())
                        for conc, guess in zip(row, rowGuesses)
                    ],
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
            text='Enter "?" to optimise that concentration as a variable, or enter'
            " ~number to provide an initial guess for the optimisation.\n",
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
        unknownTotalConcsCheckbutton.pack(fill="both", padx=style.padding)

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
        self.totalConcs = self.concsTable.data * prefixes[self.concsUnit.strip("M")]
        self.freeNames = self.concsTable.columnTitles

        if np.any(self.concsTable.initialGuesses == 0):
            raise ValueError(
                "Initial guesses for the concentrations cannot be zero, as the "
                "optimisation algorithm optimises the logarithm of the concentrations."
            )
        self.totalConcsGuesses = (
            self.concsTable.initialGuesses * prefixes[self.concsUnit.strip("M")]
        )

        self.saved = True
        self.destroy()


class GetTotalConcs(totalConcentrations):
    Popup = ConcsPopup
    popupAttributes = (
        "unknownTotalConcsLinked",
        "concsUnit",
        "totalConcs",
        "totalConcsGuesses",
        "freeNames",
    )

    def run(self, totalConcVars):
        totalConcs = np.copy(self.totalConcs)
        maskArray = ma.getmaskarray(self.totalConcs)

        if self.unknownTotalConcsLinked:
            # For each row (= component), all blank cells are assigned to a
            # single unknown variable.
            for columnIndex, totalConcVar in zip(
                np.where(self.columnsWithBlanks)[0], totalConcVars
            ):
                totalConcs[maskArray[:, columnIndex], columnIndex] = totalConcVar
        else:
            totalConcs[maskArray] = totalConcVars

        return totalConcs

    @property
    def variableInitialGuesses(self):
        if self.unknownTotalConcsLinked:
            output = np.empty(self.variableCount)

            for i, column in enumerate(
                self.totalConcsGuesses[:, self.columnsWithBlanks].T
            ):
                columnGuesses = column[~ma.getmaskarray(column)]
                if len(np.unique(columnGuesses)) > 1:
                    raise ValueError(
                        "Multiple different initial guesses entered for "
                        f"{self.variableNames[i]}"
                    )
                elif len(columnGuesses) == 0:
                    output[i] = self.defaultInitialGuess
                else:
                    output[i] = columnGuesses[0]

            return output
        else:
            return self.totalConcsGuesses[ma.getmaskarray(self.totalConcs)].filled(
                self.defaultInitialGuess
            )

    @property
    def columnsWithBlanks(self):
        return np.any(ma.getmaskarray(self.totalConcs), axis=0)

    @property
    def variableNames(self):
        if self.unknownTotalConcsLinked:
            # return the number of columns (= component) with blank cells
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
    group = "Experimental Data"
    dropdownLabelText = "Enter concentrations or volumes:"
    dropdownOptions = {
        "Volumes": GetTotalConcsFromVolumes,
        "Concentrations": GetTotalConcs,
    }
    attributeName = "totalConcentrations"
    setDefault = False
