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
    "_selectedSignalTitles",
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

    @property
    def peakIndices(self):
        if (
            hasattr(self, "_selectedSignalTitles")
            and self._selectedSignalTitles is not None
            and len(
                peakIndices := [
                    list(self.processedSignalTitles).index(title)
                    for title in self._selectedSignalTitles
                    if title in self.processedSignalTitles
                ]
            )
            != 0
        ):
            return peakIndices
        else:
            return self.getDefaultPeakIndices()

    @peakIndices.setter
    def peakIndices(self, peakIndices):
        if peakIndices is None:
            self._selectedSignalTitles = None
        else:
            self._selectedSignalTitles = self.processedSignalTitles[peakIndices]

    def getDefaultPeakIndices(self, maxPeaks=4, maxShoulderPeaks=2, threshold=0.1):
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
        peakIndices, peakProperties = find_peaks(
            np.pad(movement, [1, 1], mode="minimum"), prominence=0
        )
        peakIndices -= 1
        prominences = peakProperties["prominences"]

        # select the four most prominent peaks
        largestFilter = prominences.argsort()[-maxPeaks:]
        largestPeakIndices = peakIndices[largestFilter]

        # Shoulder peaks can appear as inflection points rather than maxima.
        # We'll add the two most prominent inflection points from a first-order
        # approximation of the first derivative of the total movement:
        leftShoulders, leftShoulderProperties = find_peaks(
            -np.gradient(movement), height=[None, 0], prominence=0
        )
        rightShoulders, rightShoulderProperties = find_peaks(
            np.gradient(movement), height=[None, 0], prominence=0
        )

        # Filter out duplicates, which happens when the peak height is exactly 0
        filter = np.isin(rightShoulders, leftShoulders, invert=True)
        shoulderIndices = np.concatenate([leftShoulders, rightShoulders[filter]])
        shoulderProminences = np.concatenate(
            [
                leftShoulderProperties["prominences"],
                rightShoulderProperties["prominences"][filter],
            ]
        )

        # filter out shoulder peaks that are too close to the main peaks
        filter = [
            index not in peakIndices
            and index + 1 not in peakIndices
            and index - 1 not in peakIndices
            for index in shoulderIndices
        ]
        shoulderIndices = shoulderIndices[filter]
        shoulderProminences = shoulderProminences[filter]

        # select the two most prominent inflection points
        filter = shoulderProminences.argsort()[-maxShoulderPeaks:]
        largestShoulderIndices = shoulderIndices[filter]

        # combine the two arrays, without duplicates, and sort them
        largestPeakIndices = np.sort(
            np.unique(np.concatenate((largestPeakIndices, largestShoulderIndices)))
        )
        if len(largestPeakIndices) == 0:
            return np.array([np.argmax(movement)])

        # discard peaks that don't move far enough compared to the other peaks
        peaksRange = totalRange[largestPeakIndices]
        return largestPeakIndices[peaksRange >= np.max(peaksRange) * threshold]

    @property
    def lastVars(self):
        return np.concatenate([self.lastKVars, self.lastTotalConcVars])

    @property
    def RMSE(self):
        return np.sqrt(np.mean((self.lastFittedCurves - self.processedData) ** 2))

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

        combinedResiduals = np.sqrt(np.sum(residuals))
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

    # Run the optimisation with one or more of the variables at a fixed value
    def optimiseFixed(
        self, fixedVars, initialGuess=None, callback=None, minimizeOptions={}
    ):
        initialGuessKs = np.log10(self.equilibriumConstants.variableInitialGuesses)
        initialGuessConcs = np.log10(self.totalConcentrations.variableInitialGuesses)
        _initialGuess = np.concatenate((initialGuessKs, initialGuessConcs))
        if initialGuess is not None:
            _initialGuess = initialGuess.filled(_initialGuess)

        initialGuessFiltered = _initialGuess[fixedVars.mask]

        def optimisationFuncLogFixed(logKsAndTotalConcs):
            ksAndTotalConcs = 10**logKsAndTotalConcs
            allKsAndTotalConcs = fixedVars.copy()
            allKsAndTotalConcs[fixedVars.mask] = ksAndTotalConcs
            return self.optimisationFunc(allKsAndTotalConcs.data)

        result = minimize(
            optimisationFuncLogFixed,
            x0=np.log10(initialGuessFiltered),
            method="nelder-mead",
            callback=callback,
            options=minimizeOptions,
        )
        # to make sure the last fit is the optimal one
        optimisationFuncLogFixed(result.x)
        return result.x

    def fitData(self, callback=None):
        self.fitResult = 10 ** self.optimise(callback)
