import tkinter.ttk as ttk
from abc import abstractmethod

import numpy as np
from numpy import ma

from . import moduleFrame
from .scrolledFrame import ScrolledFrame
from .table import ButtonFrame, Table


def stoichiometriesToBoundNames(freeNames, stoichiometries, polymerMode):
    polymerModes = ("unchanged", "dimer+polymer", "terminal+internal")

    if polymerMode not in polymerModes:
        raise ValueError(
            f"Unknown polymer mode {polymerMode}: must be one of {polymerModes}."
        )
    trans = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

    boundNames = []
    for row in stoichiometries:
        boundName = ""
        for freeName, stoichiometry in zip(freeNames, row):
            if stoichiometry == 0:
                continue

            if boundName != "":
                boundName += "·"

            if stoichiometry == 1:
                boundName += freeName
            elif stoichiometry == -1:
                boundName += freeName + "ₙ"
            else:
                boundName += freeName + str(stoichiometry).translate(trans)
        if "ₙ" in boundName and polymerMode == "dimer+polymer":
            # insert a dimer before the polymer entry
            boundNames.append(boundName.replace("ₙ", "₂"))
            boundNames.append(boundName)
        elif "ₙ" in boundName and polymerMode == "terminal+internal":
            # separate the terminal and internal parts of the polymer
            boundNames.append(boundName + " terminal")
            boundNames.append(boundName + " internal")
        else:
            boundNames.append(boundName)
    return np.array(boundNames)


class Speciation(moduleFrame.Strategy):
    requiredAttributes = ("freeNames", "stoichiometries")

    @abstractmethod
    def run(self, variables, totalConcs):
        pass

    @property
    def freeCount(self):
        return self.stoichiometries.shape[1]

    @property
    def boundCount(self):
        return self.stoichiometries.shape[0]

    @property
    def speciesCount(self):
        return self.freeCount + self.boundCount

    @property
    def polymerIndices(self):
        return np.any(self.stoichiometries < 0, 1)

    @property
    def polymerCount(self):
        return np.count_nonzero(self.stoichiometries < 0)

    @property
    def complexCount(self):
        return self.boundCount - self.polymerCount

    @property
    def boundNames(self):
        return stoichiometriesToBoundNames(
            self.freeNames, self.stoichiometries, "unchanged"
        )

    @property
    def variableNames(self):
        return stoichiometriesToBoundNames(
            self.freeNames, self.stoichiometries, "dimer+polymer"
        )

    @property
    def outputNames(self):
        return np.append(
            self.freeNames,
            stoichiometriesToBoundNames(
                self.freeNames, self.stoichiometries, "terminal+internal"
            ),
        )

    def variablesToKs(self, variables):
        # The rest of the UI should be agnostic towards the treatment of polymers, so
        # this function is used to separate out the double K values (dimer and 3+_mer)
        # for polymers.
        ks = np.empty(self.boundCount)
        polymerKs = np.empty(self.boundCount)

        polymersCounted = 0
        for i in range(self.boundCount):
            ks[i] = variables[i + polymersCounted]
            if self.polymerIndices[i]:
                polymerKs[i] = variables[i + polymersCounted + 1]
                polymersCounted += 1
        polymerKs = ma.masked_array(polymerKs, ~self.polymerIndices)
        if not len(variables) == self.boundCount + polymersCounted:
            raise ValueError(
                f"Expected {self.boundCount + polymersCounted} variables, got"
                f" {len(variables)}."
            )
        return ks, polymerKs


class SpeciationTable(Table):
    def __init__(self, master, titration):
        super().__init__(
            master,
            0,
            0,
            titration.speciation.freeNames,
            rowOptions=("readonlyTitles", "new", "delete"),
            columnOptions=("titles", "new", "delete"),
            boldTitles=True,
            callback=self.updateTitles,
        )
        for boundName, stoichiometry in zip(
            titration.speciation.boundNames, titration.speciation.stoichiometries
        ):
            self.addRow(boundName, stoichiometry)

    def updateTitles(self, *args, **kwargs):
        for cell, title in zip(
            self.cells[2 : self.headerCells :, 1], self.columnTitles
        ):
            cell.set(title)

        self.rowTitles = stoichiometriesToBoundNames(
            self.columnTitles, self.data, polymerMode="unchanged"
        )

    def addFreeRow(self, index=-1):
        row = self.cells.shape[0]
        freeRow = np.full(self.cells.shape[1], None)

        freeRow[0] = self.deleteRowButton(row, 0, "Delete Row", state="disabled")
        freeRow[1] = self.readonlyEntry(
            row, 1, self.columnTitles[index], font=self.titleFont
        )

        freeRow[2:] = [
            self.readonlyEntry(row, 2 + column, "0", align="right")
            for column in range(self.cells.shape[1] - 2)
        ]
        freeRow[-1].set("1")

        self.cells = np.insert(self.cells, self.headerCells, freeRow, axis=0)
        self.headerCells += 1

        self.redraw()

    def addColumn(self, firstEntry="", data=None):
        super().addColumn(firstEntry, data)

        for row in range(2, self.headerCells):
            self.cells[row, -1] = self.readonlyEntry(
                row, self.cells.shape[-1], "0", align="right"
            )

        self.addFreeRow()

    def deleteColumn(self, column):
        super().deleteColumn(column)
        self.headerCells -= 1
        self.deleteRow(column)
        self.updateTitles()

    def convertData(self, number):
        if number == "n":
            return -1
        elif number == "":
            return 0
        else:
            return int(number)


class SpeciationPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter speciation table")

        height = int(self.master.winfo_height() * 0.4)
        frame = ScrolledFrame(self, height=height, max_width=1500)
        frame.pack(expand=True, fill="both")

        self.innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        self.speciationTable = SpeciationTable(self.innerFrame, titration)
        self.speciationTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(
            self.innerFrame, self.reset, self.saveData, self.destroy
        )
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def reset(self):
        self.speciationTable.destroy()
        self.speciationTable = SpeciationTable(self.innerFrame, self.titration)
        self.speciationTable.pack(expand=True, fill="both")

    def saveData(self):
        stoichiometries = self.speciationTable.data

        self.stoichiometries = stoichiometries
        self.freeNames = self.speciationTable.columnTitles

        self.saved = True
        self.destroy()


class SpeciationDimerisation(Speciation):
    freeNames = np.array(["Host"])
    stoichiometries = np.array([[2]])

    def run(self, variables, totalConcs):
        K = variables[0]
        Htot = totalConcs.T[0]
        H = (-1 + np.sqrt(1 + 8 * Htot * K)) / (4 * K)
        H2 = (1 + 4 * Htot * K - np.sqrt(1 + 8 * Htot * K)) / (8 * K)

        free = np.atleast_2d(H).T
        bound = np.atleast_2d(H2).T
        return free, bound


class SpeciationHG(Speciation):
    freeNames = np.array(["Host", "Guest"])
    stoichiometries = np.array([[1, 1]])

    def run(self, variables, totalConcs):
        K = variables[0]
        Htot, Gtot = totalConcs.T
        H = (
            np.sqrt(
                Gtot**2 * K**2 - 2 * Gtot * K * (Htot * K - 1) + (Htot * K + 1) ** 2
            )
            - Gtot * K
            + Htot * K
            - 1
        ) / (2 * K)
        G = (
            np.sqrt(
                Htot**2 * K**2 - 2 * Htot * K * (Gtot * K - 1) + (Gtot * K + 1) ** 2
            )
            - Htot * K
            + Gtot * K
            - 1
        ) / (2 * K)
        HG = H * G * K

        free = np.vstack((H, G)).T
        bound = np.atleast_2d(HG).T
        return free, bound


class SpeciationCOGS(Speciation):
    # TODO: see if this can be sped up using numba
    def COGS(self, M, y, ks, polymerKs):
        free = y.copy()
        bound = np.empty(len(ks))
        polymers = np.any(M < 0, 1)
        # the index of the species making up each of the polymers
        polymerParents = np.nonzero(M[polymers])[1]
        complexes = ~polymers

        P = np.empty(len(ks))
        P[complexes] = np.sum(M[complexes, :], 1)
        P[polymers] = 2 * ks[polymers] * y[polymerParents]
        P = 1 / max(P)
        tol = 1e-7
        while True:
            bound[complexes] = ks[complexes] * np.prod(free ** M[complexes, :], 1)
            # cap the maximum guess to avoid divergence
            bound[polymers] = np.where(
                free[polymerParents] * polymerKs[polymers] >= 1,
                free[polymerParents] ** 2 * polymerKs[polymers] / P,
                (2 - polymerKs[polymers] * free[polymerParents])
                * (ks[polymers] * free[polymerParents] ** 2)
                / ((1 - polymerKs[polymers] * free[polymerParents]) ** 2),
            )
            total = free + abs(M.T) @ bound  # total concentrations of species
            if all((total - y) <= tol * y):
                break
            # to handle 0 total concentration
            invTotal = np.where(total == 0, 1, 1 / total)
            free *= (y * invTotal) ** P

        # For polymers, return separate entries for terminal and internal groups
        bound = []
        paddedPolymerParents = ma.array(np.empty(len(ks)), mask=True)
        paddedPolymerParents[polymers] = polymerParents
        for k, polymerK, stoichiometries, isPolymer, parent in zip(
            ks, polymerKs, M, self.polymerIndices, paddedPolymerParents
        ):
            if not isPolymer:
                bound.append(k * np.prod(free**stoichiometries))
            else:
                # terminal
                bound.append(2 * free[parent] ** 2 * k / (1 - free[parent] * polymerK))
                # internal
                bound.append(
                    (free[parent] ** 3 * k * polymerK)
                    / (1 - free[parent] * polymerK) ** 2
                )

        return free, np.array(bound)

    def run(self, variables, totalConcs):
        ks, polymerKs = self.variablesToKs(variables)
        numPoints = totalConcs.shape[0]
        free = np.zeros((numPoints, self.freeCount))
        bound = np.zeros((numPoints, self.complexCount + 2 * self.polymerCount))
        for i in range(numPoints):
            free[i], bound[i] = self.COGS(
                self.stoichiometries, totalConcs[i], ks, polymerKs
            )
        return free, bound


"""
class SpeciationSolver:
    def __init__(self, parent):
        self.parent = parent

    def speciationLog(self, logFree, ks, total, M):
        free = 10 ** logFree
        return (
            np.sum(free)
            - total @ logFree * 2.30258509299
            + ks @ np.prod(free ** M.T, 1)
        )

    def jacobianCalculatorLog(self, logFree, ks, total, M):
        free = 10 ** logFree
        return ((M @ (ks * np.prod(free ** M.T, 1))) + free - total) * 2.30258509299

    def getLowerBounds(self, ks, total, M):
        return np.log10(total ** 2 / (total + M @ (ks * np.prod(total ** M.T, 1))))

    def getUpperBounds(self, ks, total, M):
        return np.log10(total)

    def run(self, ks, alphas, totalConcs):
        numPoints = totalConcs.shape[0]
        M = self.parent.stoichiometries
        free = np.empty((numPoints, M.shape[1]))
        bound = np.empty((numPoints, M.shape[0]))

        for i in range(numPoints):
            additionTotalConcs = totalConcs[i]

            # Filter the to exclude species and complexes that will have a concentration
            # of 0
            zeroTotalConcs = additionTotalConcs == 0
            zeroBound = np.any(self.parent.stoichiometries[:, zeroTotalConcs], 1)
            filteredKs = ks[~zeroBound]
            filteredTotal = additionTotalConcs[~zeroTotalConcs]
            filteredM = self.parent.stoichiometries[~zeroBound, :][:, ~zeroTotalConcs]

            lb = self.getLowerBounds(filteredKs, filteredTotal, filteredM)
            ub = self.getLowerBounds(filteredKs, filteredTotal, filteredM)

            logFree = minimize(
                self.speciationLog,
                x0=ub,
                args=(filteredKs, filteredTotal, filteredM),
                jac=self.jacobianCalculatorLog,
                bounds=np.vstack((lb, ub)).T,
                tol=1e-8 / 10 ** (len(filteredTotal)),
            ).x

            free[i, ~zeroTotalConcs] = 10 ** logFree
            free[i, zeroTotalConcs] = 0

            # get the concentrations of the bound species from those of the free
            bound[i] = ks * np.prod(free[i] ** M, 1)
        return free, bound


class speciationGrad(moduleFrame.Strategy):
    def run(self, ks, alphas, totalConcs):
        if self.polymerCount == 0:
            algorithm = SpeciationAlgorithm()
        else:
            algorithm = SpeciationAlgorithmWithPolymers()
        return algorithm.run(ks, alphas, totalConcs)


class SpeciationCustomGrad(speciationGrad):
    Popup = SpeciationPopup
    popupAttributes = ("stoichiometries", "freeNames", "boundNames")
"""


class SpeciationHG2(SpeciationCOGS):
    freeNames = np.array(["Host", "Guest"])
    stoichiometries = np.array([[1, 1], [1, 2]])


class SpeciationCustom(SpeciationCOGS):
    Popup = SpeciationPopup
    popupAttributes = ("freeNames", "stoichiometries")


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Equilibria"
    dropdownLabelText = "Select a binding isotherm:"
    dropdownOptions = {
        "1:1 binding": SpeciationHG,
        "1:2 binding": SpeciationHG2,
        "Dimerisation": SpeciationDimerisation,
        "Custom": SpeciationCustom,
        # "Custom Grad": SpeciationCustomGrad,
    }
    attributeName = "speciation"
