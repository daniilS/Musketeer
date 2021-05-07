import numpy as np

from . import moduleFrame


class SpeciationHG():
    def __init__(self, titration):
        self.titration = titration
        titration.stoichiometries = np.array([
                [1, 1]
            ])
        titration.boundNames = np.array(["HG"])

    def __call__(self, ks, totalConcs):
        K = ks[0]
        Htot, Gtot = totalConcs.T
        H = (
            np.sqrt(Gtot**2 * K**2 - 2*Gtot*K*(Htot*K - 1) + (Htot*K + 1)**2)
            - Gtot*K + Htot*K - 1
        ) / (2*K)
        G = (
            np.sqrt(Htot**2 * K**2 - 2*Htot*K*(Gtot*K - 1) + (Gtot*K + 1)**2)
            - Htot*K + Gtot*K - 1
        ) / (2*K)
        HG = H * G * K

        free = np.vstack((H, G)).T
        bound = np.atleast_2d(HG).T
        return free, bound


class SpeciationCustom():
    def __call__(self):
        # TODO: copy gradient descent algorithm here
        raise NotImplementedError


class ModuleFrame(moduleFrame.ModuleFrame):
    frameLabel = "Speciation"
    dropdownLabelText = "Select a binding isotherm:"
    dropdownOptions = {
        "1:1 binding": SpeciationHG,
        "Custom": SpeciationCustom
    }
    attributeName = "speciation"
