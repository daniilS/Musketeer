import math
import tkinter.ttk as ttk

import numpy as np

from . import moduleFrame
from .scrolledFrame import ScrolledFrame
from .style import padding
from .table import ButtonFrame, Table, WrappedLabel


class Contributors:
    requiredAttributes = ()


class ContributorConcs(moduleFrame.Strategy):
    requiredAttributes = (
        "contributorsMatrix",
        "outputNames",
        "contributorsCountPerMolecule",
    )

    def run(self, speciesConcs):
        return (
            speciesConcs @ self.contributorsMatrix.T,
            self.contributorsCountPerMolecule,
        )


class ContributorsTable(Table):
    def __init__(
        self, master, outputNames, speciesNames, contributorsMatrix, speciesFilter
    ):
        if len(speciesNames) != len(speciesFilter):
            raise ValueError(
                f"Lengths of speciesNames ({len(speciesNames)}) and speciesFilter"
                f" ({len(speciesFilter)}) do not match."
            )

        self.speciesFilter = speciesFilter
        self.width = max(
            [len(name) for name in np.concatenate([outputNames, speciesNames])]
        )

        if contributorsMatrix.shape[1] == len(speciesFilter):
            data = contributorsMatrix[:, speciesFilter]
            rowTitles = outputNames
        else:
            data = np.eye(np.count_nonzero(speciesFilter), dtype=int)
            rowTitles = speciesNames[speciesFilter]
        columnTitles = speciesNames[speciesFilter]

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

    def processData(self):
        matrix = np.zeros([self.data.shape[0], len(self.speciesFilter)])
        matrix[:, self.speciesFilter] = self.data
        if np.all(matrix % 1 == 0):
            matrix = matrix.astype(int)

        contributorsMatrix = matrix
        outputNames = self.rowTitles
        # Returns an array so that ContributorConcsPopup can save it directly as a
        # popup attribute. ContributorConcsPerMoleculePopup will convert it to a long
        # array.
        contributorsCountPerMolecule = np.array([matrix.shape[0]])

        return contributorsMatrix, outputNames, contributorsCountPerMolecule


class ContributorConcsPopup(moduleFrame.Popup):
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

        scrolledFrame = ScrolledFrame(
            self.frame, max_width=self.winfo_toplevel().master.winfo_width() - 200
        )
        scrolledFrame.pack(expand=True, fill="both")
        self.innerFrame = scrolledFrame.display_widget(ttk.Frame, stretch=True)
        self.createTable()

    def createTable(self):
        self.contributorsTable = ContributorsTable(
            self.innerFrame,
            self.titration.contributors.outputNames,
            self.titration.speciation.outputNames,
            self.titration.contributors.contributorsMatrix,
            self.titration.contributingSpecies.filter,
        )
        self.contributorsTable.pack(expand=True, fill="both")

    def reset(self):
        self.contributorsTable.destroy()
        self.createTable()

    def saveData(self):
        (
            self.contributorsMatrix,
            self.outputNames,
            self.contributorsCountPerMolecule,
        ) = self.contributorsTable.processData()

        self.saved = True
        self.destroy()


class ContributorConcsPerMoleculePopup(moduleFrame.Popup):
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

        scrolledFrame = ScrolledFrame(
            self.frame, max_width=self.winfo_toplevel().master.winfo_width() - 200
        )
        scrolledFrame.pack(expand=True, fill="both")
        self.innerFrame = scrolledFrame.display_widget(ttk.Frame, stretch=True)
        self.createNotebook()

    def createNotebook(self):
        self.notebook = ttk.Notebook(self.innerFrame, style="Flat.TNotebook")
        self.notebook.pack(expand=True, fill="both", padx=padding, pady=padding)

        self.tables = []

        splitIndices = np.cumsum(
            self.titration.contributors.contributorsCountPerMolecule
        )[:-1]

        outputNamesPerMolecule = np.split(
            self.titration.contributors.outputNames, splitIndices
        )
        contributorsMatrixPerMolecule = np.vsplit(
            self.titration.contributors.contributorsMatrix, splitIndices
        )
        moleculeHasSignals = [
            index in self.titration.contributingSpecies.signalToMoleculeMap
            for index in range(self.titration.speciation.freeCount)
        ]

        for molecule, outputNames, contributorsMatrix, speciesFilter, hasSignals in zip(
            self.titration.speciation.freeNames,
            outputNamesPerMolecule,
            contributorsMatrixPerMolecule,
            self.titration.contributingSpecies.filter,  # already 1 row per molecule
            moleculeHasSignals,
        ):
            if hasSignals:
                table = ContributorsTable(
                    self.notebook,
                    outputNames,
                    self.titration.speciation.outputNames,
                    contributorsMatrix,
                    speciesFilter,
                )
                self.notebook.add(table, text=molecule)
                self.tables.append(table)
            else:
                self.tables.append(None)

    def reset(self):
        self.notebook.destroy()
        self.createNotebook()

    def saveData(self):
        contributorsMatrix = []
        outputNames = []
        contributorsCountPerMolecule = []
        for table in self.tables:
            if table is None:
                contributorsCountPerMolecule.append(np.array([0]))
            else:
                (
                    matrix,
                    names,
                    count,
                ) = table.processData()
                contributorsMatrix.append(matrix)
                outputNames.append(names)
                contributorsCountPerMolecule.append(count)

        self.contributorsMatrix = np.vstack(contributorsMatrix)
        self.outputNames = np.concatenate(outputNames)
        self.contributorsCountPerMolecule = np.concatenate(contributorsCountPerMolecule)

        self.saved = True
        self.destroy()


class ContributorConcsAll(ContributorConcs):
    @property
    def outputNames(self):
        singleMoleculeIndex = self.titration.contributingSpecies.singleMoleculeIndex
        filter = self.titration.contributingSpecies.filter
        if singleMoleculeIndex is None or type(singleMoleculeIndex) is int:
            return self.titration.speciation.outputNames[filter]
        elif type(singleMoleculeIndex) is np.ndarray:
            names = []
            for i in singleMoleculeIndex:
                moleculeName = self.titration.speciation.freeNames[i]
                allNames = np.array(
                    [
                        f"{moleculeName} in {complex}"
                        for complex in self.titration.speciation.outputNames
                    ]
                )
                allNames[i] = f"Free {moleculeName}"
                names.extend(allNames[filter[i]])
            return np.array(names)

    @property
    def contributorsMatrix(self):
        singleMoleculeIndex = self.titration.contributingSpecies.singleMoleculeIndex
        filter = self.titration.contributingSpecies.filter
        if singleMoleculeIndex is None:
            return np.diag(filter).astype(int)[filter]
        elif type(singleMoleculeIndex) is int:
            return self.matrixFromSingleMolecule(singleMoleculeIndex, filter)
        elif type(singleMoleculeIndex) is np.ndarray:
            # The index will currently always be equal to np.arange(freeCount), so a
            # matrix will be returned for each molecule. It may at some point become
            # more useful to instead only return matrices for the molecules that have
            # at least one signal mapped to them.
            return np.vstack(
                [
                    self.matrixFromSingleMolecule(i, filter[i])
                    for i in singleMoleculeIndex
                ]
            )

    @property
    def contributorsCountPerMolecule(self):
        singleMoleculeIndex = self.titration.contributingSpecies.singleMoleculeIndex
        filter = self.titration.contributingSpecies.filter
        if type(singleMoleculeIndex) is np.ndarray:
            return np.array(
                [
                    self.matrixFromSingleMolecule(i, filter[i]).shape[0]
                    for i in singleMoleculeIndex
                ]
            )
        else:
            return np.array([self.contributorsMatrix.shape[0]])

    def matrixFromSingleMolecule(self, index, filter):
        diagonal = abs(self.titration.speciation.outputStoichiometries[:, index])
        return np.diag(diagonal)[filter]


# TODO: fix for homodimers
class ContributorConcsIdentical(ContributorConcs):
    def calculateStates(self):
        moleculeCount = self.titration.speciation.freeCount
        freeStates = np.zeros(
            [self.titration.speciation.outputCount, moleculeCount], dtype=int
        )
        boundStates = np.zeros(
            [self.titration.speciation.outputCount, moleculeCount], dtype=int
        )

        # for each molecule, the maximum number of bonds it is known to form to each
        # other molecule
        # rows are the host molecules, columns are the guest molecules
        maximumValencyPerGuest = np.zeros([moleculeCount, moleculeCount], dtype=int)
        # maximum total number of bonds each molecule can form
        maximumTotalValency = np.zeros(moleculeCount, dtype=int)

        stoichiometries = self.titration.speciation.outputStoichiometries[
            self.titration.speciation.freeCount :
        ]
        # n-mer means host has n-1 binding sites for binding itself
        # 1 becomes 0, because that's the host molecule itself
        # -1 becomes -2 becomes 2, as polymers imply 2 binding sites
        guestStoichiometries = np.repeat(
            stoichiometries[np.newaxis, :, :], moleculeCount, axis=0
        )
        guestStoichiometries[range(moleculeCount), :, range(moleculeCount)] -= 1
        guestStoichiometries = np.abs(guestStoichiometries)

        # calculate maximum valency per guest and maximum total valency
        for host in range(moleculeCount):
            singleHost = np.abs(stoichiometries)[:, host] == 1
            maximumValencyPerGuest[host] = np.max(
                guestStoichiometries[host][singleHost, :], axis=0, initial=0
            )

            # We only consider guests that form binary complexes with the host
            formsBinaryComplex = np.zeros(moleculeCount, dtype=bool)
            for guest in range(moleculeCount):
                binaryComplex = np.zeros(moleculeCount, dtype=int)
                binaryComplex[host] += 1
                binaryComplex[guest] += 1
                formsBinaryComplex[guest] = np.any(
                    np.all(
                        # want to match -1 iff host == guest
                        np.abs(stoichiometries) == binaryComplex,
                        axis=1,
                    )
                )
            maximumValencyPerGuest[host, ~formsBinaryComplex] = 0

            # Find the maximum number of guests that can bind to one host molecule at
            # the same time, counting only those guests which can also form binary
            # complexes with the host.
            maximumTotalValency[host] = np.max(
                np.sum(
                    guestStoichiometries[host][singleHost, :][:, formsBinaryComplex],
                    axis=1,
                ),
                initial=0,
            )

        # calculate number of free and bound states for each molecule in each complex
        for host in range(moleculeCount):
            freeStates[host, host] = maximumTotalValency[host]
            for index, complex in enumerate(guestStoichiometries[host]):
                if stoichiometries[index, host] < 1:
                    # complexes handled separately below
                    continue
                else:
                    hostStoichiometry = stoichiometries[index, host]
                    maximumTotalValencyHost = (
                        maximumTotalValency[host] * hostStoichiometry
                    )
                valencyPerGuest = np.minimum(
                    complex * maximumValencyPerGuest[:, host],
                    maximumValencyPerGuest[host, :] * hostStoichiometry,
                )
                totalValency = np.minimum(
                    np.sum(valencyPerGuest),
                    maximumTotalValencyHost,
                )
                freeStates[moleculeCount + index, host] = (
                    maximumTotalValencyHost - totalValency
                )
                boundStates[moleculeCount + index, host] = totalValency

            complexIndices = np.where(stoichiometries[:, host] < 0)[0]
            terminal = complexIndices[0::2]
            internal = complexIndices[1::2]
            # Crude assumption for polymers with odd numbers of binding sites - users
            # are really expected to manually enter a contributors table in such cases.
            freeStates[moleculeCount + terminal, host] = math.ceil(
                maximumTotalValency[host] / 2
            )
            boundStates[moleculeCount + terminal, host] = math.floor(
                maximumTotalValency[host] / 2
            )
            freeStates[moleculeCount + internal, host] = 0
            boundStates[moleculeCount + internal, host] = maximumTotalValency[host]

        return freeStates, boundStates

    def getContributorsMatrixAndNames(self):
        freeStates, boundStates = self.calculateStates()
        allStates = np.empty(
            [
                2 * self.titration.speciation.freeCount,
                self.titration.speciation.outputCount,
            ],
            dtype=int,
        )
        allStates[0::2] = freeStates.T
        allStates[1::2] = boundStates.T

        allNames = np.concatenate(
            [
                [f"Free {molecule} site", f"Bound {molecule} site"]
                for molecule in self.titration.speciation.freeNames
            ]
        )

        singleMoleculeIndex = self.titration.contributingSpecies.singleMoleculeIndex
        if singleMoleculeIndex is None:
            relevantStates = allStates[:, self.titration.contributingSpecies.filter]
            rowFilter = np.any(relevantStates, axis=1)
        elif type(singleMoleculeIndex) is int:
            rowFilter = np.array([2 * singleMoleculeIndex, 2 * singleMoleculeIndex + 1])
        elif type(singleMoleculeIndex) is np.ndarray:
            rowFilter = np.empty(2 * len(singleMoleculeIndex), dtype=int)
            rowFilter[0::2] = 2 * singleMoleculeIndex
            rowFilter[1::2] = 2 * singleMoleculeIndex + 1
        return allStates[rowFilter], allNames[rowFilter]

    @property
    def outputNames(self):
        _, names = self.getContributorsMatrixAndNames()
        return names

    @property
    def contributorsMatrix(self):
        matrix, _ = self.getContributorsMatrixAndNames()
        return matrix

    @property
    def contributorsCountPerMolecule(self):
        singleMoleculeIndex = self.titration.contributingSpecies.singleMoleculeIndex
        if type(singleMoleculeIndex) is np.ndarray:
            return np.array([2] * len(singleMoleculeIndex))
        else:
            return np.array([self.contributorsMatrix.shape[0]])


class ContributorConcsCustom(ContributorConcs):
    @property
    def Popup(self):
        singleMoleculeIndex = self.titration.contributingSpecies.singleMoleculeIndex
        if type(singleMoleculeIndex) is np.ndarray:
            return ContributorConcsPerMoleculePopup
        else:
            return ContributorConcsPopup

    popupAttributes = (
        "contributorsMatrix",
        "outputNames",
        "contributorsCountPerMolecule",
    )


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Spectra"
    dropdownLabelText = "Specify relationship between fitted spectra?"
    dropdownOptions = {
        "All species have different spectra": ContributorConcsAll,
        "All binding sites have identical spectra": ContributorConcsIdentical,
        "Custom": ContributorConcsCustom,
    }
    attributeName = "contributors"
