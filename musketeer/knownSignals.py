import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as mb

from tksheet import Sheet

from . import moduleFrame
from .table import ButtonFrame
from .style import padding


class KnownSpectraPopup(tk.Toplevel):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter known spectra")

        self.sheet = Sheet(
            self,
            data=self.formatData(titration.knownSpectra),
            headers=list(titration.processedSignalTitlesStrings),
            row_index=list(titration.contributorNames()),
            set_all_heights_and_widths=True,
        )

        self.sheet.pack(side="top", expand=True, fill="both")
        self.sheet.enable_bindings()

        buttonFrame = ButtonFrame(self, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

        loadButton = ttk.Button(buttonFrame, text="Load from CSV", command=self.loadCSV)
        loadButton.pack(side="left", padx=padding)

    def formatData(self, data):
        formattedData = data.astype(str)
        formattedData[np.isnan(data)] = ""
        return list(formattedData)

    def reset(self):
        self.sheet.set_sheet_data(self.formatData(self.titration.knownSpectra))

    def saveData(self):
        try:
            data = np.array(self.sheet.get_sheet_data(), dtype=object)
            data[np.where(data == "")] = None
            data = data.astype(float)
        except Exception as e:
            mb.showerror(title="Could not save data", message=e, parent=self)
            return

        if not np.all(np.any(np.isnan(data), 1) == np.all(np.isnan(data), 1)):
            mb.showerror(
                title="Could not save data",
                parent=self,
                message="Please enter full spectra, or leave the entire row blank",
            )
            return

        self.titration.knownSpectra = data
        self.destroy()

    def loadCSV(self):
        return


class GetKnownSpectra(moduleFrame.Strategy):
    popup = KnownSpectraPopup
    popupAttributes = "knownSpectra"

    def __init__(self, titration):
        self.titration = titration
        if not (
            hasattr(titration, "knownSpectra")
            and titration.knownSpectra.shape
            == (len(titration.contributorNames()), len(titration.processedSignalTitles))
        ):
            titration.knownSpectra = np.full(
                (
                    len(self.titration.contributorNames()),
                    len(self.titration.processedSignalTitles),
                ),
                np.nan,
            )

    def __call__(self):
        return self.titration.knownSpectra


class GetAllSpectra(moduleFrame.Strategy):
    def __call__(self):
        return np.full(
            (
                len(self.titration.contributorNames()),
                len(self.titration.processedSignalTitles),
            ),
            np.nan,
        )


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Spectra"
    dropdownLabelText = "Which spectra to optimise?"
    dropdownOptions = {
        "Optimise all spectra": GetAllSpectra,
        "Specify some known spectra": GetKnownSpectra,
    }
    attributeName = "getKnownSpectra"
