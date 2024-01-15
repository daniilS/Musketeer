from abc import abstractmethod

import numpy as np
from numpy import ma

from . import moduleFrame


class Proportionality(moduleFrame.Strategy):
    requiredAttributes = ()

    @abstractmethod
    def run(self, contributorConcs, contributorsCountPerMolecule):
        pass


class GetConcs(Proportionality):
    def run(self, contributorConcs, contributorsCountPerMolecule):
        return contributorConcs


class GetFraction(Proportionality):
    def run(self, contributorConcs, contributorsCountPerMolecule):
        splitIndices = np.cumsum(contributorsCountPerMolecule, axis=-1)[:-1]
        concsPerMolecule = np.hsplit(contributorConcs, splitIndices)
        proportionalConcs = np.hstack(
            [
                concs / np.sum(concs, axis=-1, keepdims=True)
                for concs in concsPerMolecule
            ]
        )
        return ma.masked_invalid(proportionalConcs)


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Experimental Data"
    dropdownLabelText = "What are the signals proportional to?"
    dropdownOptions = {
        "Concentration (slow exchange)": GetConcs,
        "Mole fraction (fast exchange)": GetFraction,
    }
    attributeName = "proportionality"
    setDefault = False
