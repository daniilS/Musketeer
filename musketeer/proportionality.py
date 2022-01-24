from . import moduleFrame


class GetConcs(moduleFrame.Strategy):
    def __call__(self, signalVars, totalConcs):
        return signalVars


class GetFraction(moduleFrame.Strategy):
    def __call__(self, signalVars, totalConcs):
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
    attributeName = "getProportionalSignals"
    setDefault = False
