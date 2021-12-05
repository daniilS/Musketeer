import numpy as np

from . import moduleFrame


class ResidualsSum(moduleFrame.Strategy):
    def __call__(self, residuals):
        return np.sum(residuals)


class ResidualsSumScaled(moduleFrame.Strategy):
    # TODO: test & use
    # sum of the residuals, scaled by the number of data points for each signal
    def __call__(self, residuals):
        numPoints = np.sum(
            self.titration.processedData != None, axis=0  # noqa: E711
        )
        return np.sum(residuals / numPoints)


class ResidualsSumNormalised(moduleFrame.Strategy):
    def __call__(self, residuals):
        raise NotImplementedError


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Combine residuals"
    dropdownLabelText = "Method for combining residuals"
    dropdownOptions = {
        "Sum": ResidualsSum,
        "Normalised sum": ResidualsSumNormalised
    }
    attributeName = "combineResiduals"
