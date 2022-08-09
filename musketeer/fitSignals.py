import numpy as np
from numpy import ma
from numpy.linalg import lstsq
from scipy.optimize import lsq_linear

from . import moduleFrame


class FitSignals(moduleFrame.Strategy):
    def __call__(self, signalVars, knownSpectra):
        # rows are additions, columns are contributors
        knownMask = ~np.isnan(knownSpectra[:, 0])
        knownSignals = signalVars[:, knownMask]
        unknownSignals = signalVars[:, ~knownMask]

        knownSpectrum = knownSignals @ knownSpectra[knownMask, :]
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


class FitSignalsNonnegative(moduleFrame.Strategy):
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
                    (0, np.inf),
                    method="bvls",
                )
                fittedSignals[:, index] = result.x
                residuals[index] = result.cost
        else:
            for index, signal in enumerate(unknownSpectrum.T):
                result = lsq_linear(unknownSignals, signal, (0, np.inf), method="bvls")
                fittedSignals[:, index] = result.x
                residuals[index] = result.cost

        fittedCurves = unknownSignals @ fittedSignals + knownSpectrum
        allSignals = knownSpectra.copy()
        allSignals[~knownMask, :] = fittedSignals
        return allSignals, residuals, fittedCurves


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Fit signals"
    dropdownLabelText = "Fit signals to curve using:"
    # TODO: add least squares with linear constraints
    dropdownOptions = {
        "Ordinary least squares": FitSignals,
        "Nonnegative least squares": FitSignalsNonnegative,
    }
    attributeName = "fitSignals"
