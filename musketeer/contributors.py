import numpy as np

from . import moduleFrame


class GetSignalVarsCustom(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        self.titration.contributorsMatrix = self.contributorsMatrix
        self.titration.contributorNames = self.contributorNames

    def __call__(self, freeConcs, boundConcs):
        allConcs = np.concatenate((freeConcs, boundConcs), 1)
        variableConcs = allConcs @ self.titration.contributorsMatrix().T
        return variableConcs

    # TODO: allow user to input contributorsMatrix


class GetSignalVarsAll(moduleFrame.Strategy):
    def __init__(self, titration):
        self.titration = titration
        self.titration.contributorsMatrix = self.contributorsMatrix
        self.titration.contributorNames = self.contributorNames

    def contributorNames(self):
        return np.concatenate(
            (self.titration.freeNames, self.titration.boundNames)
        )

    def contributorsMatrix(self):
        totalCount = self.titration.freeCount + self.titration.boundCount
        return np.identity(totalCount)

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

    def contributorNames(self):
        allNames = np.concatenate(
            (self.titration.freeNames, self.titration.boundNames)
        )
        return allNames[self.filter().astype(bool)]

    def contributorsMatrix(self):
        matrix = np.diag(self.filter())
        emptyRows = np.all(matrix == 0, axis=1)
        return matrix[~emptyRows]


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Contributors"
    dropdownLabelText = "What contributes to the signals?"
    dropdownOptions = {
        "Only host species": GetSignalVarsHost,
        "All species": GetSignalVarsAll,
        "Custom": GetSignalVarsCustom
    }
    attributeName = "getSignalVars"
