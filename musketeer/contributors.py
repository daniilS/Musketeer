import tkinter as tk
import tkinter.ttk as ttk
from abc import abstractmethod

import numpy as np
from numpy import ma

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
    def __init__(self, master, rowTitles, columnTitles, data):
        self.width = max([len(title) for title in columnTitles])
        super().__init__(
            master,
            0,
            0,
            columnTitles,
            rowOptions=("titles", "new", "delete"),
            columnOptions=("readonlyTitles",),
            boldTitles=True,
        )
        for name, contributions in zip(rowTitles, data):
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
        self.createTable()

    def createTable(self):
        titration = self.titration
        if (
            titration.contributors.contributorsMatrix.shape[1]
            == titration.speciation.outputCount
        ):
            contributorsMatrix = titration.contributors.contributorsMatrix
        else:
            contributorsMatrix = np.eye(titration.speciation.outputCount)

        self.contributorsTable = ContributorsTable(
            self.innerFrame,
            titration.contributors.contributorNames,
            titration.speciation.outputNames,
            contributorsMatrix,
        )
        self.contributorsTable.pack(expand=True, fill="both")

    def reset(self):
        self.contributorsTable.destroy()
        self.createTable()

    def saveData(self):
        self.contributorsMatrix = self.contributorsTable.data
        if np.all(self.contributorsMatrix % 1 == 0):
            self.contributorsMatrix = self.contributorsMatrix.astype(int)

        self.contributorNames = self.contributorsTable.rowTitles

        self.saved = True
        self.destroy()


class GetSignalVarsCustom(GetSignalVarsFromMatrix):
    Popup = ContributorsPopup
    popupAttributes = ("contributorsMatrix", "contributorNames")


class ContributorsPerSpeciesNotebook(ttk.Notebook):
    def __init__(self, master, titration, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.titration = titration

        mapTab = ttk.Frame(self)
        self.add(mapTab, text="Map signal to species", sticky="nsew", padding=padding)
        contributorsLabel = WrappedLabel(
            mapTab,
            padding=padding * 2,
            text="For each signal, specify which species it is caused by.",
        )
        contributorsLabel.pack(expand=False, fill="both")

        if (
            hasattr(titration.contributors, "contributorsMatrixPerSpecies")
            and titration.contributors.contributorsMatrixPerSpecies.shape[2]
            == titration.speciation.outputCount
        ):
            contributorsMatrixPerSpecies = (
                titration.contributors.contributorsMatrixPerSpecies
            )
            contributorNamesPerSpecies = (
                titration.contributors.contributorNamesPerSpecies
            )
        else:
            (
                contributorsMatrixPerSpecies,
                contributorNamesPerSpecies,
            ) = self.createDefaultSetup()

        if (
            hasattr(titration.contributors, "signalToSpeciesMap")
            and len(titration.contributors.signalToSpeciesMap) == titration.numSignals
            and np.all(
                titration.contributors.signalToSpeciesMap
                <= titration.totalConcentrations.freeCount
            )
        ):
            signalToSpeciesMap = titration.contributors.signalToSpeciesMap
        else:
            signalToSpeciesMap = np.zeros(titration.numSignals, dtype=int)

        self.speciesTabs = []
        self.mapVars = []

        radioFrame = ttk.Frame(mapTab)
        radioFrame.pack(expand=True, fill="both")

        for i, (freeName, contributorNames, contributorsMatrix) in enumerate(
            zip(
                titration.totalConcentrations.freeNames,
                contributorNamesPerSpecies,
                contributorsMatrixPerSpecies,
            )
        ):
            label = ttk.Label(radioFrame, text=freeName)
            label.grid(row=0, column=i + 1, sticky="w")
            radioFrame.columnconfigure(i + 1, uniform="map", pad=padding)

            rowTitles = contributorNames[~contributorNames.mask]
            columnTitles = titration.speciation.outputNames[self.filter(i).astype(bool)]
            matrix = contributorsMatrix[~contributorsMatrix.mask].reshape(
                (len(rowTitles), len(columnTitles))
            )
            tab = ttk.Frame(self)
            contributorsLabel = WrappedLabel(
                tab,
                padding=padding * 2,
                text=(
                    "On each row, enter a state that contributes to the observed"
                    " signal. For each column, specify how many of the state that"
                    " species contains."
                ),
            )
            contributorsLabel.pack(expand=False, fill="both")

            scrolledFrame = ScrolledFrame(tab, max_width=1500)
            scrolledFrame.pack(expand=True, fill="both")
            innerFrame = scrolledFrame.display_widget(ttk.Frame, stretch=True)

            table = ContributorsTable(innerFrame, rowTitles, columnTitles, matrix)
            table.pack(expand=True, fill="both")
            self.add(tab, text=freeName, state="hidden", sticky="nsew", padding=padding)
            self.speciesTabs.append(tab)

        for i, (title, index) in enumerate(
            zip(titration.processedSignalTitlesStrings, signalToSpeciesMap)
        ):
            label = ttk.Label(radioFrame, text=title)
            label.grid(row=i + 1, column=0, padx=padding)

            mapVar = tk.StringVar(self)
            self.mapVars.append(mapVar)
            for j in range(len(titration.totalConcentrations.freeNames)):
                radioButton = ttk.Radiobutton(
                    radioFrame, variable=mapVar, value=j, command=self.updateTabs
                )
                radioButton.grid(row=i + 1, column=j + 1, sticky="w")
                if j == index:
                    radioButton.invoke()

    def updateTabs(self):
        # show tabs that have any signals mapped to them, hide the rest
        for i, tab in enumerate(self.speciesTabs):
            if any(mapVar.get() == str(i) for mapVar in self.mapVars):
                self.tab(tab, state="normal")
            else:
                self.tab(tab, state="hidden")

    def createDefaultSetup(self):
        contributorsMatrixPerSpecies = ma.array(
            np.empty(
                (
                    self.titration.totalConcentrations.freeCount,
                    self.titration.totalConcentrations.freeCount,
                    self.titration.totalConcentrations.outputCount,
                ),
                dtype=int,
            ),
            mask=True,
        )
        contributorNamesPerSpecies = ma.array(
            np.empty(
                (
                    self.titration.totalConcentrations.freeCount,
                    self.titration.totalConcentrations.freeCount,
                ),
                dtype=object,
            ),
            mask=True,
        )

        for i, name in enumerate(self.titration.totalConcentrations.freeNames):
            filter = self.filter(i)
            contributorsMatrixPerSpecies[i, i, filter.astype(bool)] = 1
            contributorNamesPerSpecies[i, i] = name

        return contributorsMatrixPerSpecies, contributorNamesPerSpecies

    def filter(self, index):
        free = np.zeros(self.titration.totalConcentrations.freeCount, dtype=int)
        free[index] = 1
        bound = abs(self.titration.speciation.stoichiometries[:, index])
        return np.concatenate((free, bound))


class ContributorsPerSpeciesPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter the contributing species")

        height = int(self.master.winfo_height() * 0.4)
        self.frame = ttk.Frame(self, height=height)
        self.frame.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")
        self.notebook = ContributorsPerSpeciesNotebook(
            self.frame, titration, style="Flat.TNotebook"
        )
        self.notebook.pack(expand=True, fill="both", padx=padding, pady=padding)

    def reset(self):
        self.notebook.destroy()
        self.notebook = ContributorsPerSpeciesNotebook(self.frame, self.titration)
        self.notebook.pack(expand=True, fill="both")

    def saveData(self):
        raise NotImplementedError

        self.saved = True
        self.destroy()


class GetSignalVarsPerSpecies(Contributors):
    Popup = ContributorsPerSpeciesPopup
    popupAttributes = (
        "contributorsMatrixPerSpecies",
        "contributorNamesPerSpecies",
        "signalToSpeciesMap",
    )

    contributorsMatrix = None
    contributorNames = None

    def run(*args):
        # TODO: implement
        raise NotImplementedError


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
    group = "Signals"
    dropdownLabelText = "What contributes to the signals?"
    dropdownOptions = {
        "Only Host": GetSignalVarsHost,
        "All": GetSignalVarsAll,
        "Custom": GetSignalVarsCustom,
        # "Custom per species": GetSignalVarsPerSpecies,
    }
    attributeName = "contributors"
