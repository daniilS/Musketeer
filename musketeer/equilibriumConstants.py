import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as mb
from tkinter import font

from . import moduleFrame
from .table import Table, ButtonFrame
from .scrolledFrame import ScrolledFrame


class CustomKsTable(Table):
    def __init__(self, master, titration):
        self.titration = titration
        if hasattr(titration, "kVarsNames"):
            kVarsNames = titration.kVarsNames
        else:
            kVarsNames = [f"K_{name}" for name in titration.boundNames]
        if hasattr(titration, "ksMatrix"):
            ksMatrix = titration.ksMatrix
        else:
            ksMatrix = np.identity(titration.boundCount, dtype=int)
        if (
            hasattr(titration, "knownKs")
            and len(titration.knownKs) == ksMatrix.shape[0]
        ):
            knownKs = np.where(np.isnan(titration.knownKs), "", titration.knownKs)
        else:
            knownKs = np.full(ksMatrix.shape[0], "")
        columnTitles = np.append(
            [f"Global K for {name}" for name in titration.boundNames], "Value"
        )
        self.width = max([len(title) for title in columnTitles]) + 1

        super().__init__(
            master,
            0,
            0,
            columnTitles,
            allowBlanks=True,
            rowOptions=("titles", "new", "delete"),
            columnOptions=("readonlyTitles",),
            boldTitles=True,
            callback=self.createLabels,
        )
        self.addConstantsRow()
        for name, contributions, value in zip(kVarsNames, ksMatrix, knownKs):
            self.addRow(name, np.append(contributions, value))

    def addConstantsRow(self):
        if hasattr(self.titration, "ksConstants"):
            ksConstants = self.titration.ksConstants
        else:
            ksConstants = np.append(np.full(len(self.columnTitles) - 1, "1"), "")
        oldRowOptions = self.rowOptions
        self.rowOptions = ("readonlyTitles",)
        self.addRow("Statistical factor", ksConstants)
        self.rowOptions = oldRowOptions

    def createLabels(self, *args, **kwargs):
        try:
            labels = []
            superscripts = "⁰¹²³⁴⁵⁶⁷⁸⁹"
            variables = self.rowTitles[1:]
            for globalK, statFactor, variableFactors in zip(
                self.columnTitles[:-1],
                self.data[0, :-1],
                self.data[1:, :-1].T.astype(int),
            ):
                label = f"{globalK} = {statFactor:g}"
                for variable, factor in zip(variables, variableFactors):
                    if factor == 0 or factor == "":
                        continue
                    label += f" × {variable}"
                    if factor == 1:
                        continue
                    label += "".join(
                        [superscripts[int(digit)] for digit in str(factor)]
                    )
                labels.append(label)
            self.label.configure(text="\n".join(labels))
        except Exception:
            pass
        return True

    def convertData(self, number):
        if number == "":
            return np.nan
        else:
            return float(number)


class CustomKsPopup(tk.Toplevel):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter relationships between Ks")

        height = int(self.master.winfo_height() * 0.4)
        frame = ScrolledFrame(self, height=height, max_width=1500)
        frame.pack(expand=True, fill="both")

        self.innerFrame = frame.display_widget(ttk.Frame, stretch=True)

        self.customKsTable = CustomKsTable(self.innerFrame, titration)
        self.customKsTable.pack(expand=True, fill="both")

        self.labelFont = font.nametofont("TkTextFont").copy()
        self.labelFont["size"] = "12"

        self.equationsLabel = ttk.Label(
            self.innerFrame, anchor="center", font=self.labelFont, padding=5
        )
        self.equationsLabel.pack(expand=True, fill="both")
        self.customKsTable.label = self.equationsLabel
        self.customKsTable.createLabels()

        buttonFrame = ButtonFrame(
            self.innerFrame, self.reset, self.saveData, self.destroy
        )
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def reset(self):
        self.customKsTable.destroy()
        self.customKsTable = CustomKsTable(self.innerFrame, self.titration)
        self.customKsTable.pack(expand=True, fill="both")

    def saveData(self):
        try:
            _contributorsMatrix = self.customKsTable.data
        except Exception as e:
            mb.showerror(title="Could not save data", message=e, parent=self)
            return

        self.titration._contributorsMatrix = _contributorsMatrix
        self.titration._contributorNames = self.customKsTable.rowTitles

        self.destroy()


class GetKsCustom(moduleFrame.Strategy):
    popup = CustomKsPopup

    popupAttributes = ("knownKs", "knownAlphas")

    def __init__(self, titration):
        self.titration = titration
        if not (
            hasattr(titration, "knownKs")
            and len(titration.knownKs) == titration.boundCount
        ):
            titration.knownKs = np.full(titration.boundCount, np.nan)
        if not (
            hasattr(titration, "knownAlphas")
            and len(titration.knownAlphas) == titration.boundCount
        ):
            titration.knownAlphas = np.full(titration.boundCount, np.nan)
        titration.kVarsCount = self.kVarsCount
        titration.alphaVarsCount = self.alphaVarsCount

    def __call__(self, kVars, alphaVars):
        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = kVars
        alphas = self.titration.knownAlphas[self.titration.polymerIndices].copy()
        alphas[np.isnan(alphas)] = alphaVars
        return (ks, alphas)

    def kVarsCount(self):
        return np.count_nonzero(np.isnan(self.titration.knownKs))

    def alphaVarsCount(self):
        return np.count_nonzero(
            np.isnan(self.titration.knownAlphas[self.titration.polymerIndices])
        )


class KnownKsTable(Table):
    def __init__(self, master, titration):
        self.titration = titration
        super().__init__(
            master,
            0,
            0,
            ["Value", "α"],
            allowBlanks=True,
            rowOptions=("readonlyTitles",),
            columnOptions=("readonlyTitles",),
        )
        self.populateDefault()

    def populateDefault(self):
        for boundName, knownK, knownAlpha in zip(
            self.titration.boundNames,
            self.titration.knownKs,
            self.titration.knownAlphas,
        ):
            self.addRow(
                boundName,
                [
                    knownK if not np.isnan(knownK) else "",
                    knownAlpha if not np.isnan(knownAlpha) else "",
                ],
            )


class KnownKsPopup(tk.Toplevel):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter known equilibrium constants")

        height = int(self.master.winfo_height() * 0.4)
        frame = ScrolledFrame(self, height=height, max_width=1500)
        frame.pack(expand=True, fill="both")

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)
        knownKsLabel = ttk.Label(
            innerFrame, text="Enter known K values. Leave blank for unknown values."
        )
        knownKsLabel.pack()

        self.knownKsTable = KnownKsTable(innerFrame, titration)
        self.knownKsTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(innerFrame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def reset(self):
        self.knownKsTable.resetData()
        self.knownKsTable.columnTitles = ["Value", "α"]
        self.knownKsTable.populateDefault()

    def saveData(self):
        try:
            knownKs = self.knownKsTable.data[:, 0]
            knownAlphas = self.knownKsTable.data[:, 1]
        except Exception as e:
            mb.showerror(title="Could not save data", message=e, parent=self)
            return

        self.titration.knownKs = knownKs
        self.titration.knownAlphas = knownAlphas
        self.destroy()


class GetKsKnown(moduleFrame.Strategy):
    popup = KnownKsPopup
    popupAttributes = ("knownKs", "knownAlphas")

    def __init__(self, titration):
        self.titration = titration
        if not (
            hasattr(titration, "knownKs")
            and len(titration.knownKs) == titration.boundCount
        ):
            titration.knownKs = np.full(titration.boundCount, np.nan)
        if not (
            hasattr(titration, "knownAlphas")
            and len(titration.knownAlphas) == titration.boundCount
        ):
            titration.knownAlphas = np.full(titration.boundCount, np.nan)
        titration.kVarsCount = self.kVarsCount
        titration.alphaVarsCount = self.alphaVarsCount

    def __call__(self, kVars, alphaVars):
        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = kVars
        alphas = self.titration.knownAlphas[self.titration.polymerIndices].copy()
        alphas[np.isnan(alphas)] = alphaVars
        return (ks, alphas)

    def kVarsCount(self):
        return np.count_nonzero(np.isnan(self.titration.knownKs))

    def alphaVarsCount(self):
        return np.count_nonzero(
            np.isnan(self.titration.knownAlphas[self.titration.polymerIndices])
        )


class GetKsAll(moduleFrame.Strategy):
    # when every equilibrium constant is unknown and independent
    def __init__(self, titration):
        self.titration = titration
        titration.kVarsCount = self.kVarsCount
        titration.alphaVarsCount = self.alphaVarsCount

    def alphaVarsCount(self):
        return self.titration.polymerCount

    def kVarsCount(self):
        return self.titration.boundCount

    def __call__(self, kVars, alphaVars):
        # TODO: move this to a more sensible place
        self.titration.knownKs = np.full(self.titration.boundCount, np.nan)
        self.titration.knownAlphas = np.full(self.titration.boundCount, np.nan)
        return (kVars, alphaVars)


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Equilibrium constants"
    dropdownLabelText = "Which Ks to optimise?"
    dropdownOptions = {
        "Optimise all Ks": GetKsAll,
        "Specify some known Ks": GetKsKnown,
        "Custom": GetKsCustom,
    }
    attributeName = "getKs"
