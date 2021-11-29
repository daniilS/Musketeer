import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as mb

from . import moduleFrame
from .table import Table, ButtonFrame
from .scrolledFrame import ScrolledFrame


class KnownKsTable(Table):
    def __init__(self, master, titration):
        self.titration = titration
        super().__init__(master, 0, 0, ["Value", "α"], allowBlanks=True,
                         rowOptions=("readonlyTitles"),
                         columnOptions=("readonlyTitles")
                         )
        self.populateDefault()

    def populateDefault(self):
        for boundName, knownK, knownAlpha in zip(self.titration.boundNames,
                                                 self.titration.knownKs,
                                                 self.titration.knownAlphas):
            self.addRow(boundName, [
                knownK if not np.isnan(knownK) else "",
                knownAlpha if not np.isnan(knownAlpha) else ""
            ])


class KnownKsPopup(tk.Toplevel):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter known equilibrium constants")
        self.grab_set()

        height = int(self.master.winfo_height() * 0.4)
        frame = ScrolledFrame(self, height=height, max_width=1500)
        frame.pack(expand=True, fill="both")
        frame.bind_arrow_keys(self)
        frame.bind_scroll_wheel(self)

        innerFrame = frame.display_widget(ttk.Frame, stretch=True)
        knownKsLabel = ttk.Label(
            innerFrame,
            text="Enter known K values. Leave blank for unknown values."
        )
        knownKsLabel.pack()

        self.knownKsTable = KnownKsTable(innerFrame, titration)
        self.knownKsTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(
            innerFrame, self.reset, self.saveData, self.destroy
        )
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
    def __init__(self, titration):
        self.titration = titration
        if not (hasattr(titration, 'knownKs')
                and len(titration.knownKs) == titration.boundCount
                ):
            titration.knownKs = np.full(titration.boundCount, np.nan)
        if not (hasattr(titration, 'knownAlphas')
                and len(titration.knownAlphas) == titration.boundCount
                ):
            titration.knownAlphas = np.full(titration.boundCount, np.nan)
        titration.kVarsCount = self.kVarsCount
        titration.alphaVarsCount = self.alphaVarsCount

    def __call__(self, kVars, alphaVars):
        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = kVars
        alphas = self.titration.knownAlphas[self.polymerIndices].copy()
        alphas[np.isnan(alphas)] = alphaVars
        return (ks, alphas)

    def showPopup(self):
        popup = KnownKsPopup(self.titration)
        popup.wait_window(popup)

    @property
    def polymerIndices(self):
        return np.any(self.titration.stoichiometries < 0, 1)

    def kVarsCount(self):
        return np.count_nonzero(np.isnan(self.titration.knownKs))

    def alphaVarsCount(self):
        return np.count_nonzero(np.isnan(
            self.titration.knownAlphas[self.polymerIndices])
        )


class GetKsAll(moduleFrame.Strategy):
    # when every equilibrium constant is unknown and independent
    def __init__(self, titration):
        self.titration = titration
        titration.ksMatrix = np.identity(titration.boundCount)
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
        "Specify some known Ks": GetKsKnown
    }
    attributeName = "getKs"
