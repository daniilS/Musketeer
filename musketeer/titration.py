import numpy as np
from scipy.optimize import minimize
from scipy.signal import find_peaks


class Titration:
    def __init__(self):
        self.title = "Titration"
        # identical to [True, True, True, ..., True]
        self.rowFilter = slice(None)
        self.columnFilter = slice(None)

    @property
    def freeCount(self):
        return self.stoichiometries.shape[1]

    @property
    def boundCount(self):
        return self.stoichiometries.shape[0]

    @property
    def totalCount(self):
        return self.freeCount + self.boundCount

    @property
    def polymerIndices(self):
        return np.any(self.stoichiometries < 0, 1)

    @property
    def polymerCount(self):
        return np.count_nonzero(self.stoichiometries < 0)

    @property
    def numAdditions(self):
        return self.processedData.shape[0]

    @property
    def processedData(self):
        return self.rawData[self.rowFilter, :][:, self.columnFilter]

    @property
    def processedSignalTitles(self):
        return self.signalTitles[self.columnFilter]

    @property
    def signalTitles(self):
        return self._signalTitles

    @signalTitles.setter
    def signalTitles(self, titles):
        try:
            _signalTitles = np.array(titles, dtype=float)
        except ValueError:
            self._signalTitles = np.array(titles, dtype=str)
            self.continuous = False
            return

        self.continuous = True

        averageStep = abs(
            (_signalTitles[-1] - _signalTitles[0]) / (len(_signalTitles) - 1)
        )
        # Round to 3 significant figures
        self.averageStep = np.round(
            averageStep, int(np.ceil(-np.log10(averageStep)) + 2)
        )
        if self.averageStep >= 1.00:
            self.signalTitlesDecimals = 0
        else:
            leadingZeros = int(np.ceil(-np.log10(self.averageStep)))
            self.signalTitlesDecimals = (
                leadingZeros
                - 1
                + len(
                    str(round(self.averageStep * 10 ** (leadingZeros + 2))).rstrip("0")
                )
            )
        self._signalTitles = np.round(_signalTitles, self.signalTitlesDecimals)

    @property
    def processedSignalTitlesStrings(self):
        if self.processedSignalTitles.dtype == float:
            return np.array(
                [
                    f"{title:.{self.signalTitlesDecimals}f}"
                    for title in self.processedSignalTitles
                ]
            )
        else:
            return self.processedSignalTitles.astype(str)

    @property
    def processedAdditionTitles(self):
        return self.additionTitles[self.rowFilter]

    def getPeakIndices(self, maxPeaks=4, maxShoulderPeaks=2, threshold=0.1):
        # get the total movement for each signal
        movement = abs(np.diff(self.processedData, axis=0)).sum(axis=0)
        # get the largest difference from the first point for each signal
        diff = self.processedData - self.processedData[0]
        maxDiff = np.max(abs(diff), axis=0)
        # find the signals with the largest total movement
        peakIndices, peakProperties = find_peaks(movement, prominence=0)
        prominences = peakProperties["prominences"]
        # select the four most prominent peaks
        largestFilter = prominences.argsort()[-maxPeaks:]
        largestPeakIndices = peakIndices[largestFilter]

        # Shoulder peaks can appear as inflection points rather than maxima.
        # We'll add the two most prominent inflection points from a first-order
        # approximation of the first derivative of the total movement:
        inflectionIndices, inflectionProperties = find_peaks(
            -abs(np.diff(movement)), prominence=0
        )
        inflectionProminences = inflectionProperties["prominences"]
        inflectionFilter = inflectionProminences.argsort()[-maxShoulderPeaks:]
        largestInflectionsIndices = inflectionIndices[inflectionFilter]

        # combine the two arrays, without duplicates, and sort them
        largestPeakIndices = np.sort(
            np.unique(np.concatenate((largestPeakIndices, largestInflectionsIndices)))
        )

        # discard peaks that don't move far enough away from the baseline
        # compared to the other peaks
        peaksDiff = maxDiff[largestPeakIndices]
        return largestPeakIndices[peaksDiff >= np.max(peaksDiff) * threshold]

    def optimisationFunc(self, ksAndTotalConcs):
        # scipy.optimize optimizes everything as a single array, so split it
        kVars = ksAndTotalConcs[: self.kVarsCount()]
        totalConcVars = ksAndTotalConcs[
            self.kVarsCount() : -self.alphaVarsCount() or None
        ]
        alphaVars = ksAndTotalConcs[self.kVarsCount() + self.getConcVarsCount() :]

        # get all Ks and total concs, as some are fixed and thus aren't passed
        # to the function as arguments
        ks, alphas = self.getKs(kVars, alphaVars)
        totalConcs = self.getTotalConcs(totalConcVars)
        self.lastTotalConcs = totalConcs

        freeConcs, boundConcs = self.speciation(ks, totalConcs, alphas)
        self.lastFreeConcs, self.lastBoundConcs = freeConcs, boundConcs

        signalVars = self.getSignalVars(freeConcs, boundConcs)

        proportionalSignalVars = self.getProportionalSignals(signalVars, totalConcs)

        knownSpectra = self.getKnownSpectra()

        self.lastFitResult, residuals, self.lastFittedCurves = self.fitSignals(
            proportionalSignalVars, knownSpectra
        )

        combinedResiduals = self.combineResiduals(residuals)

        return combinedResiduals

    def optimisationFuncLog(self, logKsAndTotalConcs):
        ksAndTotalConcs = 10 ** logKsAndTotalConcs
        return self.optimisationFunc(ksAndTotalConcs)

    def optimise(self):
        initialGuessKs = np.full(self.kVarsCount(), 3)
        initialGuessConcs = np.full(self.getConcVarsCount(), -4)
        initialGuessAlphas = np.full(self.alphaVarsCount(), 0)
        initialGuess = np.concatenate(
            (initialGuessKs, initialGuessConcs, initialGuessAlphas)
        )

        result = minimize(
            self.optimisationFuncLog, x0=initialGuess, method="Nelder-Mead"
        )
        # to make sure the last fit is the optimal one
        self.optimisationFuncLog(result.x)
        return result.x

    def fitData(self):
        self.lastKs = self.optimise()
