import numpy as np

from . import moduleFrame


class ResidualsSum():
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, residuals):
        return np.sum(residuals)


class ResidualsSumScaled():
    # TODO: test & use
    # sum of the residuals, scaled by the number of data points for each signal
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, residuals):
        numPoints = np.sum(
            self.titration.processedData != None, axis=0  # noqa: E711
        )
        return np.sum(residuals / numPoints)


class ResidualsSumNormalised():
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
