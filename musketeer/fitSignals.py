import tkinter.ttk as ttk
from abc import abstractmethod

import numpy as np
from numpy import ma
from scipy.linalg import lstsq
from scipy.optimize import lsq_linear

from . import moduleFrame
from .table import ButtonFrame, Table


class FitSignals(moduleFrame.Strategy):
    requiredAttributes = ()

    @abstractmethod
    def leastSquares(self, x, y):
        pass

    def run(self, contributorConcs, knownSpectra):
        hasMissingDatapoints = ma.is_masked(self.titration.processedData)
        hasKnownSpectra = np.any(ma.getmaskarray(knownSpectra) == False)  # noqa: E712
        hasDifferentSignalsPerMolecule = hasattr(
            self.titration.contributingSpecies, "signalToMoleculeMap"
        )

        if hasMissingDatapoints or hasKnownSpectra or hasDifferentSignalsPerMolecule:
            # need to process each signal separately
            explainedData = ma.dot(contributorConcs, knownSpectra).filled(0)
            unexplainedData = self.titration.processedData - explainedData

            fittedSpectra = knownSpectra.copy()

            signalsCount = unexplainedData.shape[1]
            contributorsCount = self.titration.contributors.outputCount
            residuals = np.empty(signalsCount)

            if hasattr(self.titration.contributingSpecies, "signalToMoleculeMap"):
                splitIndices = np.cumsum(
                    self.titration.contributors.contributorsCountPerMolecule
                )[:-1]

                # For each signal, take only the relevant contributors' concentrations
                contributorsSlicePerMolecule = np.split(
                    np.arange(contributorsCount), splitIndices
                )
                contributorsSlicePerSignal = [
                    contributorsSlicePerMolecule[molecule]
                    for molecule in self.titration.contributingSpecies.signalToMoleculeMap
                ]
            else:
                contributorsSlicePerSignal = [
                    np.arange(contributorsCount)
                ] * signalsCount

            for index, (
                signalData,
                signalKnownSpectra,
                signalContributorsSlice,
            ) in enumerate(
                zip(
                    unexplainedData.T,
                    knownSpectra.T,
                    contributorsSlicePerSignal,
                )
            ):
                dataMask = ~ma.getmaskarray(signalData)
                unknownSpectraMask = ma.getmaskarray(
                    signalKnownSpectra[signalContributorsSlice]
                )
                unknownSpectraSlice = signalContributorsSlice[unknownSpectraMask]
                relevantContributorConcs = contributorConcs[dataMask, :][
                    :, unknownSpectraSlice
                ]

                fittedSpectra[unknownSpectraSlice, index], residuals[index] = (
                    self.leastSquares(
                        np.array(relevantContributorConcs), signalData.compressed()
                    )
                )

            fittedCurves = ma.dot(contributorConcs, fittedSpectra)

            # Make the smooth curves ignore masked values, rather than treating them as
            # zeros.
            fittedCurves.data[fittedCurves.mask] = np.nan
        else:
            # can process all signals at once
            fittedSpectra, residuals = self.leastSquares(
                np.array(contributorConcs),
                np.array(self.titration.processedData),
            )
            fittedCurves = ma.dot(contributorConcs, fittedSpectra)

        return fittedSpectra, residuals, fittedCurves


class FitSignalsUnconstrained(FitSignals):
    def leastSquares(self, x, y):
        # For almost-singular matrices, the default "gelsd" driver can sometimes return
        # the correct residuals, but an incorrect value of b, which gives much worse
        # residuals when calculating x @ b - y. So instead, use "gelsy", and calculate
        # the residuals manually.
        b, _, _, _ = lstsq(x, y, cond=None, lapack_driver="gelsy")
        residuals = np.linalg.norm(x @ b - y, ord=2, axis=0) ** 2
        return b, residuals


class SignalConstraintsTable(Table):
    def __init__(self, master, titration):
        if hasattr(titration.fitSignals, "signalConstraints"):
            signalConstraints = np.where(
                np.isinf(titration.fitSignals.signalConstraints),
                "",
                titration.fitSignals.signalConstraints,
            )
        else:
            signalConstraints = None

        super().__init__(
            master,
            0,
            0,
            (
                "Lower",
                "Upper",
            ),
            maskBlanks=True,
            rowOptions=(),
            columnOptions="readonlyTitles",
            boldTitles=True,
            # empty rather than "?", as it is not a variable to be optimised
            blankValue="",
        )
        self.addRow(data=signalConstraints)


class SignalConstraintsPopup(moduleFrame.Popup):
    def __init__(self, titration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titration = titration
        self.title("Enter signal constraints")

        self.frame = ttk.Frame(self)
        self.frame.pack(expand=True, fill="both")

        constraintsLabel = ttk.Label(
            self.frame, text="Leave cells blank for no lower/upper bound."
        )
        constraintsLabel.pack()

        self.constraintsTable = SignalConstraintsTable(self.frame, titration)
        self.constraintsTable.pack(expand=True, fill="both")

        buttonFrame = ButtonFrame(self.frame, self.reset, self.saveData, self.destroy)
        buttonFrame.pack(expand=False, fill="both", side="bottom")

    def reset(self):
        self.constraintsTable.data = np.array([["", ""]])

    def saveData(self):
        constraints = self.constraintsTable.data[0]

        self.signalConstraints = np.where(
            np.isnan(constraints), (-np.inf, np.inf), constraints
        )

        self.saved = True
        self.destroy()


class FitSignalsConstrained(FitSignals):
    requiredAttributes = FitSignals.requiredAttributes + ("signalConstraints",)

    def leastSquares(self, x, y):
        if y.ndim == 1:
            return self.leastSquaresSingle(x, y)
        else:
            b, residuals = zip(*[self.leastSquaresSingle(x, col) for col in y.T])
            return np.array(b).T, np.array(residuals)

    def leastSquaresSingle(self, x, y):
        result = lsq_linear(
            x,
            y,
            self.signalConstraints,
            method="bvls",
        )
        # cost is 0.5 * ||A x - b||**2
        return result.x, 2 * result.cost


class FitSignalsNonnegative(FitSignalsConstrained):
    signalConstraints = np.array([0, np.inf])


class FitSignalsCustom(FitSignalsConstrained):
    Popup = SignalConstraintsPopup
    popupAttributes = ("signalConstraints",)


class FitSignalsODR(FitSignals):
    def run(self, contributorConcs, knownSpectra):
        X = np.asarray(contributorConcs)
        Y = np.asarray(self.titration.processedData)
        relativeWeightYOverX = 100
        scaling = (Y.mean() * Y.size) / (X.mean() * X.size) / relativeWeightYOverX
        m, n = X.shape
        XY = np.hstack([X, Y / scaling])
        U, s, Vh = np.linalg.svd(XY)
        V = Vh.T
        Vxy = V[:n, n:]
        Vyy = V[n:, n:]
        B = scaling * -Vxy @ np.linalg.inv(Vyy)
        EF = -XY @ V[:, n:] @ V[:, n:].T
        E, F = EF[:, :n], EF[:, n:]
        norm = np.linalg.norm(EF, ord="fro")
        fittedCurves = X @ B
        return B, norm**2, fittedCurves


class ModuleFrame(moduleFrame.ModuleFrame):
    group = "Spectra"
    dropdownLabelText = "Apply constraints to fitted spectra?"
    dropdownOptions = {
        "No": FitSignalsUnconstrained,
        "Nonnegative": FitSignalsNonnegative,
        "Custom constraints": FitSignalsCustom,
        # "USE ODR": FitSignalsODR,
    }
    attributeName = "fitSignals"
