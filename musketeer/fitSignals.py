import numpy as np
from numpy.linalg import lstsq
from scipy.optimize import lsq_linear

from . import moduleFrame


class FitSignals(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration

    # TODO: account for known signals
    def __call__TODO(self, signalVars):
        # rows are additions, columns are contributors
        knownMask = self.titration.signalValues != None
        knownValues = self.titration.signalValues[knownMask]
        knownSignals = signalVars[knownMask]
        unknownSignals = signalVars[~knownMask]

        knownSpectrum = knownValues @ knownSignals
        unknownSpectrum = self.titration.processedData - knownSpectrum
        fittedSignals, residuals, _, _ = lstsq(
            unknownSignals, unknownSpectrum, rcond=None
        )
        return fittedSignals, residuals

    def __call__(self, signalVars):
        unknownSignals = signalVars
        unknownSpectrum = self.titration.processedData
        fittedSignals, residuals, _, _ = lstsq(
            unknownSignals, unknownSpectrum, rcond=None
        )
        fittedCurves = unknownSignals @ fittedSignals
        return fittedSignals, residuals, fittedCurves


class FitSignalsNonnegative(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, signalVars):
        fittedSignals = np.empty((0, signalVars.shape[1]))
        residuals = np.empty((1, 0))
        for signal in self.titration.processedData.T:
            result = lsq_linear(signalVars, signal, (0, np.inf))
            fittedSignals = np.vstack((fittedSignals, result.x))
            residuals = np.append(residuals, result.cost)
        fittedSignals = fittedSignals.T
        fittedCurves = signalVars @ fittedSignals
        return fittedSignals, residuals, fittedCurves


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Fit signals"
    dropdownLabelText = "Fit signals to curve using:"
    # TODO: add least squares with linear constraints
    dropdownOptions = {
        "Ordinary least squares": FitSignals,
        "Nonnegative least squares": FitSignalsNonnegative
    }
    attributeName = "fitSignals"
