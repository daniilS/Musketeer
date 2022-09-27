import numpy as np
import tkinter.ttk as ttk
import tkinter.messagebox as mb

from . import moduleFrame
from .table import Table, ButtonFrame, WrappedLabel
from .scrolledFrame import ScrolledFrame
from .style import padding


class GetSignalVarsFromMatrix(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        self.titration.contributorsMatrix = self.contributorsMatrix
        self.titration.contributorNames = self.contributorNames

    def __call__(self, freeConcs, boundConcs):
        allConcs = np.concatenate((freeConcs, boundConcs), 1)
        variableConcs = allConcs @ self.titration.contributorsMatrix().T
        return variableConcs


class ContributorsTable(Table):
    def __init__(self, master, titration):
        columnTitles = np.concatenate((titration.freeNames, titration.boundNames))
        self.width = max([len(title) for title in columnTitles]) + 5
        super().__init__(
            master,
            0,
            0,
            columnTitles,
            allowBlanks=False,
            rowOptions=("titles", "new", "delete"),
            columnOptions=("readonlyTitles",),
            boldTitles=True,
        )
        for name, contributions in zip(
            titration.contributorNames(), titration.contributorsMatrix()
        ):
            self.addRow(name, contributions)

    def newRow(self):
        defaultEntries = np.full(self.dataCells.shape[1], "0")
        self.addRow("New state", defaultEntries)

    def convertData(self, number):
        # if all entries happen to be integers, this is handled by saveData()
        return float(number)


class ContributorsPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter the contributing states")

        height = int(self.master.winfo_height() * 0.4)
        self.frame = ttk.Frame(self, height=height)
        self.frame.pack(expand=True, fill="both")

        contributorsLabel = WrappedLabel(
            self.frame,
            padding=padding * 2,
            text=(
                "On each row, enter a state that contributes to the observed"
                " signal. For each column, specify how many of the state that"
                " species contains."
            ),
        )
        contributorsLabel.pack(expand=False, fill="both")

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

        scrolledFrame = ScrolledFrame(self.frame, max_width=1500)
        scrolledFrame.pack(expand=True, fill="both")
        self.innerFrame = scrolledFrame.display_widget(ttk.Frame, stretch=True)
        self.contributorsTable = ContributorsTable(self.innerFrame, titration)
        self.contributorsTable.pack(expand=True, fill="both")

    def reset(self):
        self.contributorsTable.destroy()
        self.contributorsTable = ContributorsTable(self.frame, self.titration)
        self.contributorsTable.pack(expand=True, fill="both")

    def saveData(self):
        try:
            _contributorsMatrix = self.contributorsTable.data
            if np.all(_contributorsMatrix % 1 == 0):
                _contributorsMatrix = _contributorsMatrix.astype(int)
        except Exception as e:
            mb.showerror(title="Could not save data", message=e, parent=self)
            return

        self.titration._contributorsMatrix = _contributorsMatrix
        self.titration._contributorNames = self.contributorsTable.rowTitles

        self.saved = True
        self.destroy()


class GetSignalVarsCustom(GetSignalVarsFromMatrix):
    Popup = ContributorsPopup
    popupAttributes = ("_contributorsMatrix", "_contributorNames")

    def __init__(self, titration, *args, **kwargs):
        titration._contributorsMatrix = titration.contributorsMatrix()
        titration._contributorNames = titration.contributorNames()
        super().__init__(titration, *args, **kwargs)

    def contributorsMatrix(self):
        return self.titration._contributorsMatrix

    def contributorNames(self):
        return self.titration._contributorNames


class GetSignalVarsAll(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        self.titration.contributorsMatrix = self.contributorsMatrix
        self.titration.contributorNames = self.contributorNames

    def contributorNames(self):
        return np.concatenate((self.titration.freeNames, self.titration.boundNames))

    def contributorsMatrix(self):
        totalCount = self.titration.freeCount + self.titration.boundCount
        return np.identity(totalCount, dtype=int)

    def __call__(self, freeConcs, boundConcs):
        allConcs = np.concatenate((freeConcs, boundConcs), 1)
        return allConcs


class GetSignalVarsSingle(GetSignalVarsFromMatrix):
    def filter(self):
        hostFree = np.zeros(self.titration.freeCount, dtype=int)
        hostFree[self.contributorIndex] = 1

        hostBound = abs(self.titration.stoichiometries[:, self.contributorIndex])

        return np.concatenate((hostFree, hostBound))

    def filter_binary(self):
        return self.filter().astype(bool).astype(int)

    def contributorNames(self):
        allNames = np.concatenate((self.titration.freeNames, self.titration.boundNames))
        return allNames[self.filter().astype(bool)]

    def contributorsMatrix(self):
        matrix = np.diag(self.filter())
        emptyRows = np.all(matrix == 0, axis=1)
        return matrix[~emptyRows]


class GetSignalVarsHost(GetSignalVarsSingle):
    contributorIndex = 0


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Contributors"
    dropdownLabelText = "What contributes to the signals?"
    dropdownOptions = {
        "Only Host": GetSignalVarsHost,
        "All": GetSignalVarsAll,
        "Custom": GetSignalVarsCustom,
    }
    attributeName = "getSignalVars"
