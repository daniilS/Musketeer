import tkinter.ttk as ttk
from abc import abstractmethod

import numpy as np
from numpy import ma
from scipy.optimize import minimize

from . import moduleFrame
from .scrolledFrame import ScrolledFrame
from .style import padding
from .table import ButtonFrame, Table, WrappedLabel

LN_10 = np.log(10)


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
    requiredAttributes = ("stoichiometries",)

    @abstractmethod
    def run(self, variables, totalConcs):
        pass

    # Other modules need to access freeNames and freeCount, but totalConcentrations
    # may not yet be loaded.
    @property
    def freeNames(self):
        try:
            return self.titration.totalConcentrations.freeNames
        except AttributeError:
            return np.array(["Host", "Guest"])

    @property
    def freeCount(self):
        return len(self.freeNames)

    @property
    def boundCount(self):
        return self.complexCount + 2 * self.polymerCount

    @property
    def polymerIndices(self):
        return np.any(self.stoichiometries < 0, 1)

    @property
    def polymerCount(self):
        return np.count_nonzero(self.stoichiometries < 0)

    @property
    def complexCount(self):
        return self.stoichiometries.shape[0] - self.polymerCount

    @property
    def boundNames(self):
        return stoichiometriesToBoundNames(
            self.freeNames,
            self.stoichiometries,
            "unchanged",
        )

    @property
    def variableStoichiomtries(self):
        # stoichiometries in dimer+polymer mode: insert a dimer before each polymer
        dimerRows = self.stoichiometries[self.polymerIndices].copy()
        dimerRows[dimerRows < 0] = 2
        return np.insert(
            self.stoichiometries, *np.where(self.polymerIndices), dimerRows, axis=0
        )

    @property
    def variableNames(self):
        return stoichiometriesToBoundNames(
            self.freeNames,
            self.stoichiometries,
            "dimer+polymer",
        )

    @property
    def outputStoichiometries(self):
        # stoichiometries in terminal+internal mode: duplicate each polymer
        polymerRows = self.stoichiometries[self.polymerIndices]
        return np.insert(
            self.stoichiometries, *np.where(self.polymerIndices), polymerRows, axis=0
        )

    @property
    def outputNames(self):
        return np.append(
            self.freeNames,
            stoichiometriesToBoundNames(
                self.freeNames,
                self.stoichiometries,
                "terminal+internal",
            ),
        )

    @property
    def outputBoundNames(self):
        return stoichiometriesToBoundNames(
            self.freeNames,
            self.stoichiometries,
            "terminal+internal",
        )

    def variablesToKs(self, variables):
        # The rest of the UI should be agnostic towards the treatment of polymers, so
        # this function is used to separate out the double K values (dimer and 3+_mer)
        # for polymers.
        complexKs = np.empty(self.complexCount)
        polymerK2s = ma.masked_all(self.freeCount)
        polymerKns = ma.masked_all(self.freeCount)

        polymersCounted = 0
        # breakpoint()
        for i in range(self.stoichiometries.shape[0]):
            if self.polymerIndices[i]:
                freeIndex = np.where(self.stoichiometries[i] < 0)[0][0]
                polymerK2s[freeIndex] = variables[i + polymersCounted]
                polymerKns[freeIndex] = variables[i + polymersCounted + 1]
                polymersCounted += 1
            else:
                complexKs[i - polymersCounted] = variables[i + polymersCounted]
        if not len(variables) == self.boundCount:
            raise ValueError(
                f"Expected {self.boundCount * 2} variables, got {len(variables)}."
            )
        return complexKs, polymerK2s, polymerKns

    def freeToBoundConcs(self, freeConcs, complexKs, polymerK2s, polymerKns):
        boundConcs = []
        polymersCounted = 0
        for i in range(self.stoichiometries.shape[0]):
            if self.polymerIndices[i]:
                j = np.where(self.stoichiometries[i] < 0)[0][0]
                terminal = (
                    2
                    * freeConcs[j] ** 2
                    * polymerK2s[j]
                    / (1 - freeConcs[j] * polymerKns[j])
                )
                internal = (
                    freeConcs[j] ** 3
                    * polymerK2s[j]
                    * polymerKns[j]
                    / (1 - freeConcs[j] * polymerKns[j])
                )
                boundConcs.extend([terminal, internal])
                polymersCounted += 1
            else:
                boundConcs.append(
                    complexKs[i - polymersCounted]
                    * np.prod(freeConcs ** self.stoichiometries[i])
                )
        return boundConcs


class SpeciationTable(Table):
    def __init__(self, master, titration):
        sortedTitleLengths = sorted(
            [len(name) for name in titration.totalConcentrations.freeNames]
        )
        self.width = max(6, sortedTitleLengths[-1] + 2)
        self.rowTitleWidth = min(20, sum(sortedTitleLengths[-2:]) + 3 + 2)

        super().__init__(
            master,
            0,
            0,
            titration.totalConcentrations.freeNames,
            rowOptions=("readonlyTitles", "new", "delete"),
            columnOptions=("readonlyTitles",),
            boldTitles=True,
            callback=self.updateTitles,
        )

        if (
            titration.speciation.stoichiometries.shape[1]
            == titration.totalConcentrations.freeCount
        ):
            for boundName, stoichiometry in zip(
                titration.speciation.boundNames, titration.speciation.stoichiometries
            ):
                stoichiometry = stoichiometry.astype(str)
                stoichiometry[stoichiometry == "-1"] = "n"
                self.addRow(boundName, stoichiometry)
        else:
            if titration.totalConcentrations.freeCount == 1:
                self.addRow("", np.array([1]))
            else:
                self.addRow(
                    "",
                    np.concatenate(
                        [
                            [1, 1],
                            [0] * (titration.totalConcentrations.freeCount - 2),
                        ]
                    ).astype(int),
                )
            self.updateTitles()

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
        self.frame = ttk.Frame(self, height=height)
        self.frame.pack(expand=True, fill="both")

        label = WrappedLabel(
            self.frame,
            padding=padding * 2,
            text=(
                "Each column corresponds to a molecule, and each row to a complex.\n"
                " Define each complex by adding a row with the stoichiometry of each"
                " molecule in the complex. For polymers, use 'n'. Leaving a cell blank"
                " is identical to entering '0'."
            ),
        )
        label.pack(expand=False, fill="both")

        scrolledFrame = ScrolledFrame(
            self.frame, max_width=self.winfo_toplevel().master.winfo_width() - 200
        )
        scrolledFrame.pack(expand=True, fill="both")
        self.innerFrame = scrolledFrame.display_widget(ttk.Frame, stretch=True)

        self.speciationTable = SpeciationTable(self.innerFrame, titration)
        self.speciationTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="x", side="bottom")

    def reset(self):
        self.speciationTable.destroy()
        self.speciationTable = SpeciationTable(self.innerFrame, self.titration)
        self.speciationTable.pack(expand=True, fill="both")

    def saveData(self):
        self.stoichiometries = self.speciationTable.data

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
        free = np.zeros((numPoints, self.titration.totalConcentrations.freeCount))
        bound = np.zeros((numPoints, self.complexCount + 2 * self.polymerCount))
        for i in range(numPoints):
            free[i], bound[i] = self.COGS(
                self.stoichiometries, totalConcs[i], ks, polymerKs
            )
        return free, bound


class SpeciationSolver(Speciation):
    # Optimise (total * log10(free))
    # This makes the derivative equal to ln(10) * (free + bound - total) / total
    #
    # So gtol in the minimisation algorithm can be set to the desired precision in
    # the total concentrations.
    def speciationLogConst(self, logFreeConst, ks, k2s, kns, total, M):
        free = 10 ** (logFreeConst / total)
        return (
            np.sum(free)
            - np.sum(logFreeConst) * LN_10
            + ks @ np.prod(free**M, 1)
            + self.speciationPolymers(free, k2s, kns)
        )

    def jacobianCalculatorLogConst(self, logFreeConst, ks, k2s, kns, total, M):
        free = 10 ** (logFreeConst / total)
        return (
            (
                (M.T @ (ks * np.prod(free**M, 1)))
                + free
                + self.jacobianPolymers(free, k2s, kns).filled(0.0)
                - total
            )
            * LN_10
            / total
        )

    def speciationPolymers(self, free, k2s, kns):
        result = np.sum(k2s * free**2 / (1 - free * kns))
        if result is np.ma.masked:
            return 0.0
        else:
            return result

    def jacobianPolymers(self, free, k2s, kns):
        return free**2 * k2s * (2 - free * kns) / (1 - free * kns) ** 2

    def getLowerBoundsLogConst(self, ks, k2s, kns, total, M):
        return total * np.log10(
            (total * self.polymersExactSolution(k2s, kns, total).filled(total))
            / (total + M.T @ (ks * np.prod(total**M, 1)))
        )

    # Could be calculated more precisely, for example as
    # UB = M @ (ks * np.prod(LOWER_BOUND**M, 1)))
    # However, as the gradient at the initial guess is almost always negative, the
    # upper bound is rarely actually used.
    def getUpperBoundsLogConst(self, ks, k2s, kns, total, M):
        upperBoundsPolymers = self.polymersExactSolution(k2s, kns, total)
        return total * np.log10(np.ma.min([total, upperBoundsPolymers], axis=0).data)

    def polymersExactSolution(self, k2s, kns, totals):
        output = np.ma.masked_all(len(totals))
        for i, (k2, kn, total) in enumerate(zip(k2s, kns, totals)):
            if not np.ma.is_masked(k2) and not np.ma.is_masked(kn):
                output[i] = self.polymersExactSolutionSingle(k2, kn, total)
        return output

    def polymersExactSolutionSingle(self, k2, kn, total):
        roots = np.roots(
            [
                k2 * kn - kn**2,
                total * kn**2 + 2 * kn - 2 * k2,
                -1 - 2 * total * kn,
                total,
            ]
        )
        real_roots = np.real(roots[np.isreal(roots)])
        return np.min(real_roots[real_roots > 0])

    def run(self, variables, totalConcs):
        # breakpoint()
        complexKs, polymerK2s, polymerKns = self.variablesToKs(variables)
        numPoints = totalConcs.shape[0]
        M = self.stoichiometries[~self.polymerIndices]
        free = np.empty((numPoints, self.freeCount))
        bound = np.empty((numPoints, self.complexCount + 2 * self.polymerCount))

        for i in range(numPoints):
            additionTotalConcs = totalConcs[i]

            # Filter the to exclude species and complexes that will have a concentration
            # of 0
            zeroTotalConcs = additionTotalConcs == 0
            zeroBound = np.any(self.stoichiometries[:, zeroTotalConcs], 1)
            if all(zeroBound):
                free[i] = additionTotalConcs
                bound[i] = 0
                continue
            zeroComplexes = zeroBound[~self.polymerIndices]

            filteredKs = complexKs[~zeroComplexes]
            filteredTotal = additionTotalConcs[~zeroTotalConcs]
            filteredM = M[~zeroComplexes, :][:, ~zeroTotalConcs]

            filteredK2s = polymerK2s[~zeroTotalConcs]
            filteredKns = polymerKns[~zeroTotalConcs]

            lb = self.getLowerBoundsLogConst(
                filteredKs, filteredK2s, filteredKns, filteredTotal, filteredM
            )
            ub = self.getUpperBoundsLogConst(
                filteredKs, filteredK2s, filteredKns, filteredTotal, filteredM
            )
            if any(lb > ub):
                # Correct for rounding errors. Unsure if this is necessary, as the only
                # obvious case when it should happen is if no complexes are formed,
                # which should be caught above.
                mask = np.logical_and(lb > ub, np.isclose(lb, ub))
                lb[mask], ub[mask] = ub[mask], lb[mask]

            if i == 0:
                # Initial guess: all species 100% free
                x0 = ub
            else:
                # If the total concentration increased, the initial guess is that all
                # the added molecules are free.
                # If the total concentration decreased, the initial guess is that the
                # free concentration decreases by the same fraction.
                #
                # The L-BFGS-B implementation will clip x0 to the bounds if necessary.
                initialGuess = free[i - 1].copy()
                difference = additionTotalConcs - totalConcs[i - 1]
                concsIncreased = difference >= 0

                initialGuess[concsIncreased] += difference[concsIncreased]
                initialGuess[~concsIncreased] *= (
                    totalConcs[i][~concsIncreased] / totalConcs[i - 1][~concsIncreased]
                )
                x0 = filteredTotal * np.log10(initialGuess[~zeroTotalConcs])

            result = minimize(
                self.speciationLogConst,
                x0=x0,
                args=(filteredKs, filteredK2s, filteredKns, filteredTotal, filteredM),
                jac=self.jacobianCalculatorLogConst,
                bounds=np.vstack((lb, ub)).T,
                options={
                    "ftol": 0,
                    "gtol": 1e-7 * LN_10,
                },
            )
            logFree = result.x / filteredTotal

            free[i, ~zeroTotalConcs] = 10**logFree
            free[i, zeroTotalConcs] = 0

            # get the concentrations of the bound species from those of the free
            bound[i] = self.freeToBoundConcs(free[i], complexKs, polymerK2s, polymerKns)

        return free, bound


class SpeciationHG2(SpeciationSolver):
    stoichiometries = np.array([[1, 1], [1, 2]])

    def run(self, variables, totalConcs):
        return super().run(variables, totalConcs)


class SpeciationCustom(SpeciationSolver):
    Popup = SpeciationPopup
    popupAttributes = ("stoichiometries",)


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
