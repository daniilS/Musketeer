from abc import abstractmethod

import numpy as np

from . import moduleFrame


class Proportionality(moduleFrame.Strategy):
    requiredAttributes = ()

    @abstractmethod
    def run(self, signalVars, totalConcs):
        pass


class GetConcs(Proportionality):
    def run(self, signalVars, totalConcs):
        return signalVars


class GetFraction(Proportionality):
    def run(self, signalVars, totalConcs):
        # divide by total concs
        # TODO: support different signals caused by different parent species
        return signalVars / np.sum(signalVars, axis=1, keepdims=True)


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Proportionality"
    dropdownLabelText = "What are the signals proportional to?"
    dropdownOptions = {
        "Concentration (slow exchange)": GetConcs,
        "Mole fraction (fast exchange)": GetFraction,
    }
    attributeName = "proportionality"
    setDefault = False
