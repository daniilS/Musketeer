import numpy as np
from scipy.optimize import minimize


class Titration():
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

    def optimisationFunc(self, ksAndTotalConcs):
        # scipy.optimize optimizes everything as a single array, so split it
        kVars = ksAndTotalConcs[:self.kVarsCount()]
        totalConcVars = ksAndTotalConcs[
            self.kVarsCount():-self.alphaVarsCount()]
        alphaVars = ksAndTotalConcs[
            self.kVarsCount() + self.getConcVarsCount():]

        # get all Ks and total concs, as some are fixed and thus aren't passed
        # to the function as arguments
        ks, alphas = self.getKs(kVars, alphaVars)
        totalConcs = self.getTotalConcs(totalConcVars)

        freeConcs, boundConcs = self.speciation(ks, totalConcs, alphas)
        self.lastFreeConcs, self.lastBoundConcs = freeConcs, boundConcs

        signalVars = self.getSignalVars(freeConcs, boundConcs)

        proportionalSignalVars = \
            self.getProportionalSignals(signalVars, totalConcs)

        knownSpectra = self.getKnownSpectra()

        self.lastFitResult, residuals, self.lastFittedCurves = \
            self.fitSignals(proportionalSignalVars, knownSpectra)

        combinedResiduals = self.combineResiduals(residuals)

        return combinedResiduals

    def optimisationFuncLog(self, logKsAndTotalConcs):
        ksAndTotalConcs = 10**logKsAndTotalConcs
        return self.optimisationFunc(ksAndTotalConcs)

    def optimise(self):
        initialGuessKs = np.full(self.kVarsCount(), 3)
        initialGuessConcs = np.full(self.getConcVarsCount(), -4)
        initialGuessAlphas = np.full(self.alphaVarsCount(), 0)
        initialGuess = np.concatenate(
            (initialGuessKs, initialGuessConcs, initialGuessAlphas))

        result = minimize(
            self.optimisationFuncLog, x0=initialGuess, method="Nelder-Mead"
        )
        # to make sure the last fit is the optimal one
        self.optimisationFuncLog(result.x)
        return result.x

    def fitData(self):
        self.lastKs = self.optimise()
