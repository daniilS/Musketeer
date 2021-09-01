import numpy as np

from . import moduleFrame


class GetSignalVarsCustom(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        self.titration.signalsMatrix = self.signalsMatrix
        self.titration.signalNames = self.signalNames

    def __call__(self, freeConcs, boundConcs):
        allConcs = np.concatenate((freeConcs, boundConcs), 1)
        variableConcs = allConcs @ self.titration.signalsMatrix.T
        return variableConcs

    # TODO: allow user to input signalsMatrix


class GetSignalVarsAll(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        self.titration.signalsMatrix = self.signalsMatrix
        self.titration.signalNames = self.signalNames

    @property
    def signalNames(self):
        return np.concatenate(
            (self.titration.freeNames, self.titration.boundNames)
        )

    @property
    def signalsMatrix(self):
        totalCount = self.titration.freeCount + self.titration.boundCount
        self.titration.signalsMatrix = np.identity(totalCount)

    def __call__(self, freeConcs, boundConcs):
        allConcs = np.concatenate((freeConcs, boundConcs), 1)
        return allConcs


class GetSignalVarsHost(GetSignalVarsCustom):
    def filter(self):
        hostFree = np.zeros(self.titration.freeCount)
        hostFree[0] = 1

        hostBound = self.titration.stoichiometries[:, 0]\
            .astype(bool)\
            .astype(int)
        return np.concatenate((hostFree, hostBound))

    @property
    def signalNames(self):
        allNames = np.concatenate(
            (self.titration.freeNames, self.titration.boundNames)
        )
        return allNames[self.filter().astype(bool)]

    @property
    def signalsMatrix(self):
        signalsMatrix = np.diag(self.filter())
        emptyRows = np.all(signalsMatrix == 0, axis=1)
        return signalsMatrix[~emptyRows]


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Signals"
    dropdownLabelText = "What contributes to the signals?"
    dropdownOptions = {
        "Only host species": GetSignalVarsHost,
        "All species": GetSignalVarsAll,
        "Custom": GetSignalVarsCustom
    }
    attributeName = "getSignalVars"
