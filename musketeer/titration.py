import numpy as np
from scipy.optimize import minimize
from scipy.signal import find_peaks

titrationAttributes = (
    "title",
    "rawData",
    "continuousRange",
    "hasSignalTitles",
    "hasAdditionTitles",
    "additionTitles",
    "signalTitles",
    "transposeData",
    "yQuantity",
    "yUnit",
    "xQuantity",
    "xUnit",
    "fitResult",
    "lastKVars",
    "lastTotalConcVars",
    "lastKs",
    "lastTotalConcs",
    "lastSpeciesConcs",
    "lastSignalVars",
    "lastFittedSpectra",
    "lastFittedCurves",
)


class Titration:
    def __init__(self, title="Titration"):
        self.title = title
        self.continuousRange = np.array([-np.inf, np.inf])
        self.continuous = False
        self.hasSignalTitles = False
        self.hasAdditionTitles = False
        self.transposeData = False

    @property
    def numAdditions(self):
        return self.processedData.shape[0]

    @property
    def numSignals(self):
        return self.processedData.shape[1]

    @property
    def columnFilter(self):
        if self.continuous:
            from_, to = self.continuousRange
            return (self.signalTitles >= from_) & (self.signalTitles <= to)

        else:
            return slice(None)

    @property
    def processedData(self):
        return self.rawData[:, self.columnFilter]

    @property
    def processedSignalTitles(self):
        if self.hasSignalTitles:
            return self.signalTitles[self.columnFilter]
        else:
            return np.array(
                ["Signal " + str(i + 1) for i in range(self.processedData.shape[1])]
            )

    @property
    def processedSignalCount(self):
        return self.processedData.shape[1]

    @property
    def signalTitles(self):
        if self.hasSignalTitles:
            return self._signalTitles
        else:
            return np.array(
                ["Signal " + str(i + 1) for i in range(self.rawData.shape[1])]
            )

    @signalTitles.setter
    def signalTitles(self, titles):
        # TODO: replace flag with just setting titles to None
        if titles.size == 0:
            self.hasSignalTitles = False
            self.continuous = False
            return
        self.hasSignalTitles = True
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
    def signalTitlesStrings(self):
        if self.signalTitles.dtype == float:
            return np.array(
                [
                    f"{title:.{self.signalTitlesDecimals}f}"
                    for title in self.signalTitles
                ]
            )
        else:
            return self.signalTitles.astype(str)

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
    def additionTitles(self):
        if self.hasAdditionTitles:
            return self._additionTitles
        else:
            return np.array(
                ["Addition " + str(i + 1) for i in range(self.rawData.shape[0])]
            )

    @additionTitles.setter
    def additionTitles(self, additionTitles):
        if additionTitles.size == 0:
            return
        self.hasAdditionTitles = True
        self._additionTitles = additionTitles

    def getPeakIndices(self, maxPeaks=4, maxShoulderPeaks=2, threshold=0.1):
        numSignals = self.processedData.shape[1]
        if numSignals <= maxPeaks + maxShoulderPeaks:
            return np.arange(numSignals)
        # get the total movement for each signal
        movement = abs(np.diff(self.processedData, axis=0)).sum(axis=0)
        # get the range for each signal
        totalRange = np.abs(
            np.max(self.processedData, axis=0) - np.min(self.processedData, axis=0)
        )
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
        # remove peaks that got detected twice
        duplicatesFilter = [
            index not in peakIndices
            and index + 1 not in peakIndices
            and index - 1 not in peakIndices
            for index in inflectionIndices
        ]
        inflectionIndices = inflectionIndices[duplicatesFilter]
        inflectionProminences = inflectionProminences[duplicatesFilter]
        # select the two most prominent inflection points
        inflectionFilter = inflectionProminences.argsort()[-maxShoulderPeaks:]
        largestInflectionsIndices = inflectionIndices[inflectionFilter]

        # combine the two arrays, without duplicates, and sort them
        largestPeakIndices = np.sort(
            np.unique(np.concatenate((largestPeakIndices, largestInflectionsIndices)))
        )
        if len(largestPeakIndices) == 0:
            return np.array([np.argmax(movement)])

        # discard peaks that don't move far enough compared to the other peaks
        peaksRange = totalRange[largestPeakIndices]
        return largestPeakIndices[peaksRange >= np.max(peaksRange) * threshold]

    def optimisationFunc(self, ksAndTotalConcs):
        # scipy.optimize optimizes everything as a single array, so split it
        kVars = ksAndTotalConcs[: self.equilibriumConstants.variableCount]
        self.lastKVars = kVars
        totalConcVars = ksAndTotalConcs[self.equilibriumConstants.variableCount :]
        self.lastTotalConcVars = totalConcVars

        # get all Ks and total concs, as some are fixed and thus aren't passed
        # to the function as arguments
        speciationVars = self.equilibriumConstants.run(kVars)
        self.lastKs = speciationVars
        totalConcs = self.totalConcentrations.run(totalConcVars)
        self.lastTotalConcs = totalConcs

        speciesConcs = self.speciation.run(speciationVars, totalConcs)
        self.lastSpeciesConcs = speciesConcs

        contributingSpeciesFilter = self.contributingSpecies.run()
        signalVars, contributorsCountPerMolecule = self.contributors.run(speciesConcs)
        self.lastSignalVars = signalVars

        proportionalSignalVars = self.proportionality.run(
            signalVars, contributorsCountPerMolecule
        )

        knownSpectra = self.knownSignals.run()

        self.lastFittedSpectra, residuals, self.lastFittedCurves = self.fitSignals.run(
            proportionalSignalVars, knownSpectra
        )

        combinedResiduals = self.combineResiduals.run(residuals)
        self.lastResiduals = combinedResiduals

        return combinedResiduals

    def optimisationFuncLog(self, logKsAndTotalConcs):
        ksAndTotalConcs = 10**logKsAndTotalConcs
        return self.optimisationFunc(ksAndTotalConcs)

    def optimise(self, callback=None):
        initialGuessKs = np.log10(self.equilibriumConstants.variableInitialGuesses)
        initialGuessConcs = np.log10(self.totalConcentrations.variableInitialGuesses)
        initialGuess = np.concatenate((initialGuessKs, initialGuessConcs))

        result = minimize(
            self.optimisationFuncLog,
            x0=initialGuess,
            method="nelder-mead",
            callback=callback,
        )
        # to make sure the last fit is the optimal one
        self.optimisationFuncLog(result.x)
        return result.x

    def fitData(self, callback=None):
        self.fitResult = 10 ** self.optimise(callback)
