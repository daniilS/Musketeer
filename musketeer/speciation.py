import numpy as np
import tkinter.ttk as ttk
import tkinter.messagebox as mb

from . import moduleFrame
from .table import Table, ButtonFrame
from .scrolledFrame import ScrolledFrame


class SpeciationDimerisation(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        titration.freeNames = np.array(["Host"])
        titration.stoichiometries = np.array([[2]])
        titration.boundNames = np.array(["H2"])

    def __call__(self, ks, totalConcs, alphas):
        K = ks[0]
        Htot = totalConcs.T[0]
        H = (-1 + np.sqrt(1 + 8 * Htot * K)) / (4 * K)
        H2 = (1 + 4 * Htot * K - np.sqrt(1 + 8 * Htot * K)) / (8 * K)

        free = np.atleast_2d(H).T
        bound = np.atleast_2d(H2).T
        return free, bound


class SpeciationHG(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        titration.freeNames = np.array(["Host", "Guest"])
        titration.stoichiometries = np.array([[1, 1]])
        titration.boundNames = np.array(["HG"])

    def __call__(self, ks, totalConcs, alphas):
        K = ks[0]
        Htot, Gtot = totalConcs.T
        H = (
            np.sqrt(
                Gtot ** 2 * K ** 2 - 2 * Gtot * K * (Htot * K - 1) + (Htot * K + 1) ** 2
            )
            - Gtot * K
            + Htot * K
            - 1
        ) / (2 * K)
        G = (
            np.sqrt(
                Htot ** 2 * K ** 2 - 2 * Htot * K * (Gtot * K - 1) + (Gtot * K + 1) ** 2
            )
            - Htot * K
            + Gtot * K
            - 1
        ) / (2 * K)
        HG = H * G * K

        free = np.vstack((H, G)).T
        bound = np.atleast_2d(HG).T
        return free, bound


class SpeciationTable(Table):
    def __init__(self, master, titration):
        if hasattr(titration, "freeNames"):
            freeNames = titration.freeNames
        else:
            freeNames = np.array(["Host", "Guest"])
        if hasattr(titration, "boundNames"):
            boundNames = titration.boundNames
        else:
            boundNames = np.array(["HG"])
        if hasattr(titration, "stoichiometries"):
            stoichiometries = titration.stoichiometries
        else:
            stoichiometries = np.array([[1, 1]])

        super().__init__(
            master,
            0,
            0,
            freeNames,
            allowBlanks=False,
            rowOptions=("titles", "new", "delete"),
            columnOptions=("titles", "new", "delete"),
            boldTitles=True,
        )
        for boundName, stoichiometry in zip(boundNames, stoichiometries):
            self.addRow(boundName, stoichiometry)

    def convertData(self, number):
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
        try:
            stoichiometries = self.speciationTable.data
        except Exception as e:
            mb.showerror(title="Could not save data", message=e, parent=self)
            return

        self.titration.stoichiometries = stoichiometries
        self.titration.freeNames = self.speciationTable.columnTitles
        self.titration.boundNames = self.speciationTable.rowTitles

        self.saved = True
        self.destroy()


class SpeciationCOGS(moduleFrame.Strategy):
    # TODO: see if this can be sped up using numba
    def COGS(self, M, y, k, alphas):
        free = y.copy()
        bound = np.empty(len(k))
        polymers = np.any(M < 0, 1)
        # the index of the species making up each of the polymers
        polymerParents = np.nonzero(M[polymers])[1]
        complexes = ~polymers

        P = np.empty(len(k))
        P[complexes] = np.sum(M[complexes, :], 1)
        P[polymers] = 2 * k[polymers] * y[polymerParents]
        P = 1 / max(P)
        tol = 1e-7
        while True:
            bound[complexes] = k[complexes] * np.prod(free ** M[complexes, :], 1)
            # cap the maximum guess to avoid divergence
            bound[polymers] = np.where(
                free[polymerParents] * k[polymers] >= 1,
                free[polymerParents] ** 2 * k[polymers] / P,
                (2 - k[polymers] * free[polymerParents])
                * (k[polymers] * free[polymerParents] ** 2)
                / (alphas * (1 - k[polymers] * free[polymerParents]) ** 2),
            )
            total = free + abs(M.T) @ bound  # total concentrations of species
            if all((total - y) <= tol * y):
                break
            # to handle 0 total concentration
            invTotal = np.where(total == 0, 1, 1 / total)
            free *= (y * invTotal) ** P
        return free, bound

    def __call__(self, ks, totalConcs, alphas):
        numPoints = totalConcs.shape[0]
        free = np.zeros((numPoints, self.titration.stoichiometries.shape[1]))
        bound = np.zeros((numPoints, self.titration.stoichiometries.shape[0]))
        for i in range(numPoints):
            free[i], bound[i] = self.COGS(
                self.titration.stoichiometries, totalConcs[i], ks, alphas
            )
        return free, bound


class SpeciationHG2(SpeciationCOGS):
    def __init__(self, titration):
        self.titration = titration
        titration.freeNames = np.array(["Host", "Guest"])
        titration.stoichiometries = np.array([[1, 1], [1, 2]])
        titration.boundNames = np.array(["HG", "HG2"])


class SpeciationCustom(SpeciationCOGS):
    Popup = SpeciationPopup
    popupAttributes = ("stoichiometries", "freeNames", "boundNames")


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Speciation"
    dropdownLabelText = "Select a binding isotherm:"
    dropdownOptions = {
        "1:1 binding": SpeciationHG,
        "1:2 binding": SpeciationHG2,
        "Dimerisation": SpeciationDimerisation,
        "Custom": SpeciationCustom,
    }
    attributeName = "speciation"
