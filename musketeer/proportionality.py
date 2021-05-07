from . import moduleFrame


class GetConcs():
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, signalVars, totalConcs):
        return signalVars


class GetFraction():
    def __init__(self, titration):
        self.titration = titration

    def __call__(self, signalVars, totalConcs):
        # divide by total host concs
        # TODO: support proportionality to other total concs
        return signalVars / totalConcs[:, [0]]


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Proportionality"
    dropdownLabelText = "What are the signals proportional to?"
    dropdownOptions = {
        "Concentration": GetConcs,
        "Mole fraction": GetFraction,
    }
    attributeName = "getProportionalSignals"
