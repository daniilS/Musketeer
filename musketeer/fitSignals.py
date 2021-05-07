from numpy.linalg import lstsq

from . import moduleFrame


class FitSignals():
    def __init__(self, titration):
        self.titration = titration

    # TODO: account for known signals
    def __call__TODO(self, signalVars):
        knownMask = self.titration.signalValues != None  # noqa: E711
        # I said what I said, flake8
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


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Fit signals"
    dropdownLabelText = "Fit signals to curve using:"
    # TODO: add least squares with linear constraints
    dropdownOptions = {
        "Ordinary least squares": FitSignals
    }
    attributeName = "fitSignals"
