import csv
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.ttk as ttk
import warnings

import numpy as np
from numpy import ma
from tksheet import Sheet

from . import moduleFrame
from .style import padding
from .table import ButtonFrame


class KnownSignals(moduleFrame.Strategy):
    requiredAttributes = ("knownSpectra",)

    def run(self):
        return self.knownSpectra


class KnownSpectraPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter known spectra")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.sheet = Sheet(
                self,
                empty_vertical=0,
                empty_horizontal=0,
                data=list(titration.knownSignals.knownSpectra.astype(str).filled("?")),
                headers=list(titration.processedSignalTitlesStrings),
                row_index=list(titration.contributors.outputNames),
                set_all_heights_and_widths=True,
            )
        self.sheet.MT.configure(height=self.sheet.MT.row_positions[-1] + 1)
        self.sheet.RI.configure(height=0)

        self.sheet.enable_bindings()
        self.sheet.set_width_of_index_to_text()

        buttonFrame = ButtonFrame(self, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

        loadButton = ttk.Button(buttonFrame, text="Load from CSV", command=self.loadCSV)
        loadButton.pack(side="left", padx=padding)

        self.sheet.pack(side="top", expand=True, fill="both")

    def reset(self):
        self.sheet.set_sheet_data(
            self.formatData(self.titration.knownSignals.knownSpectra)
        )

    def saveData(self):
        data = np.array(self.sheet.get_sheet_data(), dtype=object)
        data[data == "?"] = "nan"
        if np.any(data == ""):
            raise ValueError(
                'Please enter a value in each cell. For unknown values, please enter "?".'
            )
        data = data.astype(float)

        self.knownSpectra = ma.masked_invalid(data)
        self.spectraTitles = self.titration.contributors.outputNames
        self.signalTitles = self.titration.processedSignalTitlesStrings
        self.saved = True
        self.destroy()

    def loadCSV(self):
        fileType = tk.StringVar(self)
        filePath = fd.askopenfilename(
            master=self,
            title="Load from CSV",
            filetypes=[("All files", "*.*"), ("CSV files", "*.csv")],
            typevariable=fileType,
        )
        if filePath == "":
            return
        with open(filePath, encoding="utf-8-sig") as file:
            d = csv.Sniffer().sniff(file.readline() + file.readline())
            file.seek(0)
            data = np.array(list(csv.reader(file, dialect=d)))

        if data[0, 0] == "":
            # first row contains signal titles
            signalTitles = data[0, 1:]
            spectraTitles = data[1:, 0]
            spectra = data[1:, 1:].astype(float)
            for spectrumTitle, spectrum in zip(spectraTitles, spectra):
                if spectrumTitle in self.titration.contributors.outputNames:
                    for signalTitle, value in zip(signalTitles, spectrum):
                        if signalTitle in self.titration.processedSignalTitlesStrings:
                            self.sheet.set_cell_data(
                                np.where(
                                    self.titration.contributors.outputNames
                                    == spectrumTitle
                                )[0][0],
                                np.where(
                                    self.titration.processedSignalTitlesStrings
                                    == signalTitle
                                )[0][0],
                                value,
                            )
        else:
            spectraTitles = data[:, 0]
            spectra = data[:, 1:].astype(float)
            for spectrumTitle, spectrum in zip(spectraTitles, spectra):
                if spectrumTitle in self.titration.contributors.outputNames:
                    self.sheet.set_row_data(
                        np.where(
                            self.titration.contributors.outputNames == spectrumTitle
                        )[0][0],
                        list(spectrum),
                    )
        self.sheet.redraw()


class KnownSpectraPerMoleculePopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter any known spectra")

        height = int(self.master.winfo_height() * 0.4)
        self.frame = ttk.Frame(self, height=height)
        self.frame.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

        self.createNotebook()

    def createNotebook(self):
        self.notebook = ttk.Notebook(self.frame, style="Flat.TNotebook")
        self.notebook.pack(expand=True, fill="both", padx=padding, pady=padding)

        self.sheets = []

        splitIndices = np.cumsum(
            self.titration.contributors.contributorsCountPerMolecule
        )[:-1]

        spectraTitlesPerMolecule = np.split(
            self.titration.contributors.outputNames, splitIndices
        )
        knownSpectraPerMolecule = np.vsplit(
            self.titration.knownSignals.knownSpectra, splitIndices
        )
        signalsFilterPerMolecule = [
            self.titration.contributingSpecies.signalToMoleculeMap == i
            for i in range(self.titration.speciation.freeCount)
        ]

        for (
            molecule,
            spectraTitles,
            knownSpectra,
            contributorsCount,
            signalsFilter,
        ) in zip(
            self.titration.speciation.freeNames,
            spectraTitlesPerMolecule,
            knownSpectraPerMolecule,
            self.titration.contributors.contributorsCountPerMolecule,
            signalsFilterPerMolecule,
        ):
            if contributorsCount > 0:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    sheet = Sheet(
                        self,
                        empty_vertical=0,
                        empty_horizontal=0,
                        data=list(
                            knownSpectra[:, signalsFilter].astype(str).filled("?")
                        ),
                        headers=list(
                            self.titration.processedSignalTitlesStrings[signalsFilter]
                        ),
                        row_index=list(spectraTitles),
                        set_all_heights_and_widths=True,
                    )
                sheet.MT.configure(height=sheet.MT.row_positions[-1] + 1)
                sheet.RI.configure(height=0)

                sheet.enable_bindings()
                sheet.set_width_of_index_to_text()

                self.notebook.add(sheet, text=molecule)
                self.sheets.append(sheet)
            else:
                self.sheets.append(None)

    def reset(self):
        # TODO: FIX!
        self.contributorsTable.destroy()
        self.createTable()

    def saveData(self):
        knownSpectraAll = ma.masked_all(
            [
                self.titration.contributors.outputCount,
                self.titration.processedSignalCount,
            ]
        )
        splitIndices = np.cumsum(
            self.titration.contributors.contributorsCountPerMolecule
        )[:-1]
        knownSpectraPerMolecule = np.vsplit(
            knownSpectraAll, splitIndices
        )  # returns a view, so can edit

        signalsFilterPerMolecule = [
            self.titration.contributingSpecies.signalToMoleculeMap == i
            for i in range(self.titration.speciation.freeCount)
        ]

        for sheet, knownSpectra, signalsFilter in zip(
            self.sheets,
            knownSpectraPerMolecule,
            signalsFilterPerMolecule,
        ):
            if sheet is None:
                continue
            data = np.array(sheet.get_sheet_data(), dtype=object)
            data[data == "?"] = "nan"
            if np.any(data == ""):
                raise ValueError(
                    'Please enter a value in each cell. For unknown values, please enter "?".'
                )
            data = data.astype(float)
            knownSpectra[:, signalsFilter] = ma.masked_invalid(data)

        self.knownSpectra = knownSpectraAll
        self.spectraTitles = self.titration.contributors.outputNames
        self.signalTitles = self.titration.processedSignalTitlesStrings
        self.saved = True
        self.destroy()


class GetKnownSpectra(KnownSignals):
    Popup = KnownSpectraPopup
    popupAttributes = ("knownSpectra", "spectraTitles", "signalTitles")

    @property
    def Popup(self):
        singleMoleculeIndex = self.titration.contributingSpecies.singleMoleculeIndex
        if type(singleMoleculeIndex) is np.ndarray:
            return KnownSpectraPerMoleculePopup
        else:
            return KnownSpectraPopup

    @property
    def knownSpectra(self):
        currentContributors = self.titration.contributors.outputNames
        lastContributors = self.spectraTitles
        lastSignals = self.signalTitles
        currentSignals = self.titration.processedSignalTitlesStrings

        if not set(currentSignals).issubset(lastSignals):
            return ma.masked_all((len(currentContributors), len(currentSignals)))
        relevantSignalIndices = [
            np.where(lastSignals == signal)[0][0] for signal in currentSignals
        ]
        relevantSignals = self._knownSpectra[:, relevantSignalIndices]

        output = ma.masked_all((len(currentContributors), len(currentSignals)))
        for spectrumTitle, spectrum in zip(lastContributors, relevantSignals):
            if spectrumTitle in currentContributors:
                output[np.where(currentContributors == spectrumTitle)[0][0], :] = (
                    spectrum
                )
        return output

    @knownSpectra.setter
    def knownSpectra(self, value):
        self._knownSpectra = value


class GetAllSpectra(KnownSignals):
    @property
    def knownSpectra(self):
        return ma.masked_all(
            (
                self.titration.contributors.outputCount,
                self.titration.processedSignalCount,
            )
        )


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Spectra"
    dropdownLabelText = "Specify any known spectra?"
    dropdownOptions = {
        "Optimise all spectra": GetAllSpectra,
        "Specify some known spectra": GetKnownSpectra,
    }
    attributeName = "knownSignals"
