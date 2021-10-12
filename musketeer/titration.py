import numpy as np
from scipy.optimize import minimize


class Titration():
    def __init__(self):
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
        np.count_nonzero(self.stoichiometries < 0)

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
        totalConcVars = ksAndTotalConcs[self.kVarsCount():]

        # get all Ks and total concs, as some are fixed and thus aren't passed
        # to the function as arguments
        ks = self.getKs(kVars)
        totalConcs = self.getTotalConcs(totalConcVars)

        freeConcs, boundConcs = self.speciation(ks, totalConcs)
        self.lastFreeConcs, self.lastBoundConcs = freeConcs, boundConcs

        signalVars = self.getSignalVars(freeConcs, boundConcs)

        proportionalSignalVars = \
            self.getProportionalSignals(signalVars, totalConcs)

        self.lastFitResult, residuals, self.lastFittedCurves = \
            self.fitSignals(proportionalSignalVars)

        combinedResiduals = self.combineResiduals(residuals)

        return combinedResiduals

    def optimisationFuncLog(self, logKsAndTotalConcs):
        ksAndTotalConcs = 10**logKsAndTotalConcs
        return self.optimisationFunc(ksAndTotalConcs)

    def optimise(self):
        initialGuessKs = np.full(self.kVarsCount(), 3)
        initialGuessConcs = np.full(self.getConcVarsCount(), -4)
        initialGuess = np.concatenate((initialGuessKs, initialGuessConcs))

        result = minimize(
            self.optimisationFuncLog, x0=initialGuess, method="Nelder-Mead"
        )

        return result.x

    def fitData(self):
        self.lastKs = self.optimise()
