from abc import abstractmethod

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
        # divide by total host concs
        # TODO: support proportionality to other total concs
        return signalVars / totalConcs[:, [0]]


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Proportionality"
    dropdownLabelText = "What are the signals proportional to?"
    dropdownOptions = {
        "Concentration (slow exchange)": GetConcs,
        "Mole fraction (fast exchange)": GetFraction,
    }
    attributeName = "proportionality"
    setDefault = False
