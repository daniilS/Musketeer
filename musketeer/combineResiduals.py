from abc import abstractmethod

import numpy as np

from . import moduleFrame


class combineResiduals(moduleFrame.Strategy):
    requiredAttributes = ()

    @abstractmethod
    def run(self, residuals):
        pass


class ResidualsSum(combineResiduals):
    def run(self, residuals):
        return np.sqrt(np.sum(residuals))


class ResidualsSumScaled(combineResiduals):
    # Provided for legacy reasons, not currently recommended
    # sum of the residuals, scaled by the number of data points for each signal
    def run(self, residuals):
        numPoints = self.titration.processedData.count(axis=0)
        return np.sqrt(np.sum(residuals / numPoints))


class ResidualsSumNormalised(combineResiduals):
    def run(self, residuals):
        raise NotImplementedError


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Fitting"
    dropdownLabelText = "Normalise residuals?"
    dropdownOptions = {
        "No": ResidualsSum,
        "By number of points": ResidualsSumScaled,
    }
    attributeName = "combineResiduals"
