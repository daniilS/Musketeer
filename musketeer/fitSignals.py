import tkinter.ttk as ttk
from abc import abstractmethod

import numpy as np
from numpy import ma
from numpy.linalg import lstsq
from scipy.optimize import lsq_linear

from . import moduleFrame
from .table import ButtonFrame, Table


class FitSignals(moduleFrame.Strategy):
    requiredAttributes = ()

    @abstractmethod
    def run(self, signalVars, knownSpectra):
        pass


class FitSignalsOrdinary(FitSignals):
    def run(self, signalVars, knownSpectra):
        # rows are additions, columns are contributors
        knownMask = ~knownSpectra.mask[:, 0]
        knownSignals = signalVars[:, knownMask]
        unknownSignals = signalVars[:, ~knownMask]

        # TODO: investigate why this doesn't work with @
        knownSpectrum = np.dot(knownSignals, knownSpectra[knownMask, :])
        unknownSpectrum = self.titration.processedData - knownSpectrum

        if ma.is_masked(unknownSpectrum):
            signalsCount = unknownSpectrum.shape[1]
            unknownsCount = unknownSignals.shape[1]
            fittedSignals = np.empty((unknownsCount, signalsCount))
            residuals = np.empty(signalsCount)

            for index, signal in enumerate(unknownSpectrum.T):
                try:
                    fittedSignals[:, index], residuals[index], _, _ = lstsq(
                        unknownSignals[~signal.mask, :], signal.compressed(), rcond=None
                    )
                except ValueError:
                    # Should only happen with incorrect constraints
                    fittedSignals[:, index], _, _, _ = lstsq(
                        unknownSignals[~signal.mask, :], signal.compressed(), rcond=None
                    )
                    residuals[index] = np.linalg.norm(
                        unknownSignals[~signal.mask, :] @ fittedSignals[:, index]
                        - signal.compressed(),
                        ord=2,
                    )
        else:
            fittedSignals, residuals, _, _ = lstsq(
                unknownSignals, np.asarray(unknownSpectrum), rcond=None
            )

        fittedCurves = unknownSignals @ fittedSignals + knownSpectrum
        allSignals = knownSpectra.copy()
        allSignals[~knownMask, :] = fittedSignals
        return allSignals, residuals, fittedCurves


class SignalConstraintsTable(Table):
    def __init__(self, master, titration):
        if hasattr(titration, "signalConstraints"):
            signalConstraints = np.where(
                np.isinf(titration.fitSignals.signalConstraints),
                "",
                titration.fitSignals.signalConstraints,
            )
        else:
            signalConstraints = None

        super().__init__(
            master,
            0,
            0,
            (
                "Lower",
                "Upper",
            ),
            maskBlanks=True,
            rowOptions=(),
            columnOptions="readonlyTitles",
            boldTitles=True,
        )
        self.addRow(data=signalConstraints)


class SignalConstraintsPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter signal constraints")

        self.frame = ttk.Frame(self)
        self.frame.pack(expand=True, fill="both")

        constraintsLabel = ttk.Label(
            self.frame, text="Leave cells blank for no lower/upper bound."
        )
        constraintsLabel.pack()

        self.constraintsTable = SignalConstraintsTable(self.frame, titration)
        self.constraintsTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def reset(self):
        self.constraintsTable.data = np.array([["", ""]])

    def saveData(self):
        constraints = self.constraintsTable.data[0]

        self.signalConstraints = np.where(
            np.isnan(constraints), (-np.inf, np.inf), constraints
        )

        self.saved = True
        self.destroy()


class FitSignalsConstrained(FitSignals):
    requiredAttributes = FitSignals.requiredAttributes + ("signalConstraints",)

    def __call__(self, signalVars, knownSpectra):
        # rows are additions, columns are contributors
        knownMask = ~np.isnan(knownSpectra[:, 0])
        knownSignals = signalVars[:, knownMask]
        unknownSignals = signalVars[:, ~knownMask]

        knownSpectrum = knownSignals @ knownSpectra[knownMask, :]
        unknownSpectrum = self.titration.processedData - knownSpectrum

        signalsCount = unknownSpectrum.shape[1]
        unknownsCount = unknownSignals.shape[1]
        fittedSignals = np.empty((unknownsCount, signalsCount))
        residuals = np.empty(signalsCount)

        if ma.is_masked(unknownSpectrum):
            for index, signal in enumerate(unknownSpectrum.T):
                result = lsq_linear(
                    unknownSignals[~signal.mask, :],
                    signal.compressed(),
                    self.signalConstraints,
                    method="bvls",
                )
                fittedSignals[:, index] = result.x
                residuals[index] = result.cost
        else:
            for index, signal in enumerate(unknownSpectrum.T):
                result = lsq_linear(
                    unknownSignals,
                    signal,
                    self.signalConstraints,
                    method="bvls",
                )
                fittedSignals[:, index] = result.x
                residuals[index] = result.cost

        fittedCurves = unknownSignals @ fittedSignals + knownSpectrum
        allSignals = knownSpectra.copy()
        allSignals[~knownMask, :] = fittedSignals
        return allSignals, residuals, fittedCurves


class FitSignalsNonnegative(FitSignalsConstrained):
    def __init__(self, titration):
        self.titration = titration
        self.signalConstraints = np.array([0, np.inf])


class FitSignalsCustom(FitSignalsConstrained):
    Popup = SignalConstraintsPopup
    popupAttributes = ("signalConstraints",)


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Fit signals"
    dropdownLabelText = "Fit signals to curve using:"
    dropdownOptions = {
        "Ordinary least squares": FitSignalsOrdinary,
        "Nonnegative least squares": FitSignalsNonnegative,
        "Constrained least squares": FitSignalsCustom,
    }
    attributeName = "fitSignals"
