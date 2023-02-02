import tkinter.ttk as ttk
from abc import abstractmethod

import numpy as np

from . import moduleFrame
from .scrolledFrame import ScrolledFrame
from .style import padding
from .table import ButtonFrame, Table, WrappedLabel


class Contributors(moduleFrame.Strategy):
    requiredAttributes = (
        "contributorsMatrix",
        "contributorNames",
    )

    @abstractmethod
    def run(self, freeConcs, boundConcs):
        pass


class GetSignalVarsFromMatrix(Contributors):
    def run(self, freeConcs, boundConcs):
        allConcs = np.concatenate((freeConcs, boundConcs), 1)
        variableConcs = allConcs @ self.contributorsMatrix.T
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
        _contributorsMatrix = self.contributorsTable.data
        if np.all(_contributorsMatrix % 1 == 0):
            _contributorsMatrix = _contributorsMatrix.astype(int)

        self.titration._contributorsMatrix = _contributorsMatrix
        self.titration._contributorNames = self.contributorsTable.rowTitles

        self.saved = True
        self.destroy()


# TODO: convert to new format
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


class GetSignalVarsAll(Contributors):
    @property
    def contributorNames(self):
        return self.titration.speciation.outputNames

    @property
    def contributorsMatrix(self):
        return np.identity(self.titration.speciation.outputCount, dtype=int)

    def run(self, freeConcs, boundConcs):
        allConcs = np.concatenate((freeConcs, boundConcs), 1)
        return allConcs


class GetSignalVarsSingle(GetSignalVarsFromMatrix):
    requiredAttributes = GetSignalVarsFromMatrix.requiredAttributes + (
        "contributorIndex",
    )

    # TODO: make this work with polymers
    def filter(self):
        hostFree = np.zeros(self.titration.speciation.freeCount, dtype=int)
        hostFree[self.contributorIndex] = 1

        hostBound = abs(
            self.titration.speciation.stoichiometries[:, self.contributorIndex]
        )

        return np.concatenate((hostFree, hostBound))

    @property
    def contributorNames(self):
        return self.titration.speciation.outputNames[self.filter().astype(bool)]

    @property
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
        # "Custom": GetSignalVarsCustom,
    }
    attributeName = "contributors"
