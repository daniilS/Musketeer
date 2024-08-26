import tkinter as tk
import tkinter.ttk as ttk

import numpy as np

from . import moduleFrame
from . import style
from .scrolledFrame import ScrolledFrame
from .style import padding
from .table import ButtonFrame, WrappedLabel


class ContributingSpecies(moduleFrame.Strategy):
    requiredAttributes = ("filter",)

    # If set by a subclass to an index, then contributors.py will determine the default
    # number of contributing states in each species from the stoichiometry of that
    # molecule.
    singleMoleculeIndex = None

    def mapContributorsToSignals(self, contributorConcs):
        if contributorConcs.ndim == 2:
            return contributorConcs
        elif contributorConcs.ndim == 3:
            return contributorConcs[self.signalToMoleculeMap, :, :]

    def run(self):
        return self.filter


class GetContributingSpeciesSingle(ContributingSpecies):
    requiredAttributes = ContributingSpecies.requiredAttributes + (
        "singleMoleculeIndex",
    )

    @property
    def filter(self):
        return self.titration.speciation.outputStoichiometries[
            :, self.singleMoleculeIndex
        ].astype(bool)


class GetContributingSpeciesHost(GetContributingSpeciesSingle):
    singleMoleculeIndex = 0


class GetContributingSpeciesAll(ContributingSpecies):
    @property
    def filter(self):
        return np.ones(self.titration.speciation.outputCount, dtype=bool)


class ContributingSpeciesCustomPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Select contributing species")

        height = int(self.master.winfo_height() * 0.4)
        self.frame = ttk.Frame(self, height=height)
        self.frame.pack(expand=True, fill="both")

        label = ttk.Label(
            self.frame,
            text="Select all species that contribute to the signals.",
            justify="left",
            padding=5,
        )
        label.pack(expand=False, fill="x")

        self.checkbuttonsFrame = ttk.Frame(self.frame)
        self.checkbuttonsFrame.pack(expand=False, fill="none")

        self.checkbuttonVars = []
        for name, state in zip(
            self.titration.speciation.outputNames,
            self.getLastFilter(),
        ):
            var = tk.BooleanVar(self, value=bool(state))
            self.checkbuttonVars.append(var)
            checkbutton = ttk.Checkbutton(
                self.checkbuttonsFrame, text=name, variable=var
            )
            checkbutton.grid(sticky="w", pady=padding)

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def getLastFilter(self):
        lastFilter = self.titration.contributingSpecies.filter
        if len(lastFilter.shape) == 2:
            lastFilter = lastFilter.any(axis=0)
        if len(lastFilter) != self.titration.speciation.outputCount:
            lastFilter = np.full(self.titration.speciation.outputCount, False)

        return lastFilter

    def reset(self):
        for var, state in zip(
            self.checkbuttonVars,
            self.getLastFilter(),
        ):
            var.set(bool(state))

    def saveData(self):
        self.filter = np.array([var.get() for var in self.checkbuttonVars])
        self.saved = True
        self.destroy()


class GetContributingSpeciesCustom(ContributingSpecies):
    Popup = ContributingSpeciesCustomPopup
    popupAttributes = ("filter",)


class ContributorsPerSignalNotebook(ttk.Notebook):
    def __init__(self, master, titration, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.titration = titration


class ContributorsPerSignalPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter the contributing species")

        height = int(self.master.winfo_height() * 0.4)
        self.frame = ttk.Frame(self, height=height)
        self.frame.pack(expand=True, fill="both")

        label = WrappedLabel(
            self.frame,
            padding=padding * 2,
            text=(
                "For each signal, specify which component (free and in complexes) it is"
                " caused by."
            ),
        )
        label.pack(expand=False, fill="both")

        scrolledFrame = ScrolledFrame(
            self.frame, max_width=self.winfo_toplevel().master.winfo_width() - 200
        )
        scrolledFrame.pack(expand=True, fill="both")
        self.innerFrame = scrolledFrame.display_widget(ttk.Frame, stretch=True)

        self.mapVars = []

        radioFrame = ttk.Frame(self.innerFrame)
        radioFrame.pack(expand=True, fill="both", padx=padding * 2)

        columnsLabel = ttk.Label(radioFrame, text="Components:", font=style.boldFont)
        columnsLabel.grid(row=0, column=2, columnspan=titration.speciation.freeCount)

        rowsLabel = ttk.Label(radioFrame, text="Signals:", font=style.boldFont)
        rowsLabel.grid(row=2, column=0, rowspan=titration.numSignals)

        for i, freeName in enumerate(titration.speciation.freeNames):
            label = ttk.Label(radioFrame, text=freeName)
            label.grid(row=1, column=i + 2, sticky="w")
            radioFrame.columnconfigure(i + 2, uniform="map", pad=padding)

        for i, (title, index) in enumerate(
            zip(titration.processedSignalTitlesStrings, self.getDefaultMap())
        ):
            label = ttk.Label(radioFrame, text=title)
            label.grid(row=i + 2, column=1, padx=int(1.5 * padding))

            mapVar = tk.IntVar(self, value=index)
            self.mapVars.append(mapVar)
            for j in range(len(titration.speciation.freeNames)):
                radioButton = ttk.Radiobutton(radioFrame, variable=mapVar, value=j)
                radioButton.grid(row=i + 2, column=j + 2, sticky="w")

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def getDefaultMap(self):
        if (
            hasattr(self.titration.contributingSpecies, "signalToMoleculeMap")
            and len(self.titration.contributingSpecies.signalToMoleculeMap)
            == self.titration.numSignals
            and np.all(
                self.titration.contributingSpecies.signalToMoleculeMap
                <= self.titration.speciation.freeCount
            )
        ):
            return self.titration.contributingSpecies.signalToMoleculeMap
        else:
            return np.zeros(self.titration.numSignals, dtype=int)

    def reset(self):
        for var, index in zip(self.mapVars, self.getDefaultMap()):
            var.set(index)

    def saveData(self):
        self.signalToMoleculeMap = np.array([var.get() for var in self.mapVars])

        self.saved = True
        self.destroy()


class GetContributingSpeciesPerSignal(ContributingSpecies):
    Popup = ContributorsPerSignalPopup
    popupAttributes = ("signalToMoleculeMap",)

    @property
    def singleMoleculeIndex(self):
        return np.arange(self.titration.speciation.freeCount)

    @property
    def filter(self):
        # rows are all contributing molecules, columns are the corresponding
        # contributing species
        return (
            self.titration.speciation.outputStoichiometries[
                :, range(self.titration.speciation.freeCount)
            ]
            .astype(bool)
            .T
        )


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Spectra"
    dropdownLabelText = "Which species contribute to the spectra?"
    dropdownOptions = {
        "Only species containing Host": GetContributingSpeciesHost,
        "All species": GetContributingSpeciesAll,
        "Custom": GetContributingSpeciesCustom,
        "Custom, different per signal": GetContributingSpeciesPerSignal,
    }
    attributeName = "contributingSpecies"
