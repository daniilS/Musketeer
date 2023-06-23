import tkinter as tk
import tkinter.ttk as ttk

import numpy as np

from . import moduleFrame
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
        free = np.zeros(self.titration.speciation.freeCount, dtype=bool)
        free[self.singleMoleculeIndex] = True

        bound = self.titration.speciation.outputStoichiometries[
            :, self.singleMoleculeIndex
        ].astype(bool)

        return np.concatenate([free, bound])


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
        currentFilter = self.titration.contributingSpecies.filter
        if len(currentFilter.shape) == 2:
            currentFilter = currentFilter.any(axis=0)
        for name, state in zip(
            self.titration.speciation.outputNames,
            self.titration.contributingSpecies.filter,
        ):
            var = tk.BooleanVar(self, value=bool(state))
            self.checkbuttonVars.append(var)
            checkbutton = ttk.Checkbutton(
                self.checkbuttonsFrame, text=name, variable=var
            )
            checkbutton.grid(sticky="w", pady=padding)

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def reset(self):
        for var, state in zip(
            self.checkbuttonVars,
            self.titration.contributingSpecies.filter,
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
                "For each signal, specify which molecule (free and in complexes) it is"
                " caused by."
            ),
        )
        label.pack(expand=False, fill="both")

        scrolledFrame = ScrolledFrame(self.frame, max_width=1500)
        scrolledFrame.pack(expand=True, fill="both")
        self.innerFrame = scrolledFrame.display_widget(ttk.Frame, stretch=True)

        self.mapVars = []

        radioFrame = ttk.Frame(self.innerFrame)
        radioFrame.pack(expand=True, fill="both")

        for i, freeName in enumerate(titration.speciation.freeNames):
            label = ttk.Label(radioFrame, text=freeName)
            label.grid(row=0, column=i + 1, sticky="w")
            radioFrame.columnconfigure(i + 1, uniform="map", pad=padding)

        for i, (title, index) in enumerate(
            zip(titration.processedSignalTitlesStrings, self.getDefaultMap())
        ):
            label = ttk.Label(radioFrame, text=title)
            label.grid(row=i + 1, column=0, padx=(3 * padding, int(1.5 * padding)))

            mapVar = tk.IntVar(self, value=index)
            self.mapVars.append(mapVar)
            for j in range(len(titration.speciation.freeNames)):
                radioButton = ttk.Radiobutton(radioFrame, variable=mapVar, value=j)
                radioButton.grid(row=i + 1, column=j + 1, sticky="w")

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
        free = np.eye(self.titration.speciation.freeCount, dtype=bool)

        bound = (
            self.titration.speciation.outputStoichiometries[
                :, range(self.titration.speciation.freeCount)
            ]
            .astype(bool)
            .T
        )

        return np.hstack([free, bound])


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