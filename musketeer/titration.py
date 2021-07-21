import tkinter as tk
import tkinter.ttk as ttk

import numpy as np
from scipy.optimize import minimize
from scipy.interpolate import interp1d
from scipy.signal import find_peaks
from cycler import cycler

from . import equilibriumConstants
from . import totalConcentrations
from . import speciation
from . import signals
from . import proportionality
from . import fitSignals
from . import combineResiduals
from .style import padding
from .scrolledFrame import ScrolledFrame

# need to tell matplotlib to use the tkinter backend, otherwise the scale
# of figures can get messed up if it would default to a different backend
import matplotlib
matplotlib.use("TkAgg")

# TODO: stop using pyplot to avoid window closing issues?
import matplotlib.pyplot as plt # noqa
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # noqa
from .navigationToolbar2Tk import NavigationToolbar2Tk # noqa
from matplotlib.backend_bases import key_press_handler # noqa


class Titration():
    def __init__(self, frame=None):
        self.frame = frame
        self.freeNames = np.array(["Host", "Guest"])
        self.ksMatrix = np.array([[]])
        self.signalsMatrix = np.array([[]])
        self.stoichiometries = np.array([[]])

    @property
    def freeCount(self):
        return self.stoichiometries.shape[1]

    @property
    def boundCount(self):
        return self.stoichiometries.shape[0]

    @property
    def totalCount(self):
        return self.freeCount + self.boundCount

    @property
    def kVarsCount(self):
        return self.ksMatrix.shape[0]

    @property
    def numAdditions(self):
        return self.processedData.shape[0]

    @property
    def concVarsCount(self):
        # TODO: add support for unknown total concentrations
        return 0

    @property
    def processedData(self):
        return self.rawData[self.rowFilter, :][:, self.columnFilter]

    @property
    def processedSignalTitles(self):
        return self.signalTitles[self.columnFilter]

    def optimisationFunc(self, ksAndTotalConcs):
        # scipy.optimize optimizes everything as a single array, so split it
        kVars = ksAndTotalConcs[:self.kVarsCount]
        totalConcVars = ksAndTotalConcs[:self.kVarsCount]

        # get all Ks and total concs, as some are fixed and thus aren't passed
        # to the function as arguments
        ks = self.getKs(kVars)
        totalConcs = self.getTotalConcs(totalConcVars)

        freeConcs, boundConcs = self.speciation(ks, totalConcs)
        self.lastFreeConcs, self.lastBoundConcs = freeConcs, boundConcs

        signalVars = self.getSignalVars(freeConcs, boundConcs)

        proportionalSignalVars = \
            self.getProportionalSignals(signalVars, totalConcs)

        self.lastFitResult, residuals, self.lastFittedCurves = \
            self.fitSignals(proportionalSignalVars)

        combinedResiduals = self.combineResiduals(residuals)

        return combinedResiduals

    def optimisationFuncLog(self, logKsAndTotalConcs):
        ksAndTotalConcs = 10**logKsAndTotalConcs
        return self.optimisationFunc(ksAndTotalConcs)

    def optimise(self):
        initialGuessKs = np.full(self.kVarsCount, 3)
        initialGuessConcs = np.full(self.concVarsCount, -4)
        initialGuess = np.concatenate((initialGuessKs, initialGuessConcs))

        result = minimize(
            self.optimisationFuncLog, x0=initialGuess, method="Nelder-Mead"
        )

        return result.x

    def plotSpectra(self, K):
        self.fitFrame = ttk.Frame(self.notebook)
        self.notebook.add(self.fitFrame, text="Fitted spectra")
        fig, (ax) = plt.subplots()

        spectra = self.lastFitResult
        names = self.signalNames
        wavelengths = self.processedSignalTitles
        for spectrum, name in zip(spectra, names):
            plt.plot(wavelengths, spectrum, label=name)

        ax.set_title(f"Fitted spectra (K = {int(10**K)})")
        ax.set_xlabel("λ / nm")
        ax.set_ylabel("ε / $M^{-1} cm^{-1}$")
        ax.legend()

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.fitFrame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self.fitFrame, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="")

        self.fitFrame.rowconfigure(0, weight=1)
        self.fitFrame.rowconfigure(1, weight=1)
        self.fitFrame.columnconfigure(0, weight=1)

        self.plotSpectraDiscreteFromContinuous(K)

    def plotSpectraDiscreteFromContinuous(self, K):
        self.dfcFrame = ttk.Frame(self.notebook)
        self.notebook.add(
            self.dfcFrame, text="Fitted spectra (select wavelengths)"
        )
        fig, (ax) = plt.subplots()

        # get the total movement at each wavelength
        movement = abs(np.diff(self.processedData, axis=0)).sum(axis=0)
        # get the largest difference from the first point at each wavelength
        diff = self.processedData - self.processedData[0]
        maxDiff = np.max(abs(diff), axis=0)
        # find the wavelengths with the largest total movement
        peaksIndices, peakProperties = find_peaks(movement, prominence=0)
        prominences = peakProperties["prominences"]
        # select the four most prominent peaks
        largestFilter = prominences.argsort()[-4:]
        largestPeaksIndices = np.sort(peaksIndices[largestFilter])
        # discard peaks that don't move far enough away from the baseline
        # compared to the other peaks
        peaksDiff = maxDiff[largestPeaksIndices]
        threshold = np.max(peaksDiff) / 10
        filteredPeaks = largestPeaksIndices[peaksDiff >= threshold]

        curves = self.processedData.T[filteredPeaks]
        fittedCurves = self.lastFittedCurves.T[filteredPeaks]
        names = np.char.add(
            # TODO: move rounding to titrationReader
            self.processedSignalTitles[filteredPeaks]
            .round().astype(int).astype(str),
            " nm"
        )
        guestConcs = self.totalConcs.T[1]
        # TODO: move to separate function, also use from plotSpectraDiscrete
        for curve, fittedCurve, name in zip(curves, fittedCurves, names):
            fittedZero = fittedCurve[0]
            curve -= fittedZero
            fittedCurve -= fittedZero
            plt.scatter(guestConcs, curve)

            smoothX = np.linspace(guestConcs.min(), guestConcs.max(), 100)
            # make sure the smooth curve actually goes through all the fitted
            # points
            smoothX = np.unique(np.concatenate((smoothX, guestConcs)))

            spl = interp1d(guestConcs, fittedCurve, kind="quadratic")
            smoothY = spl(smoothX)
            plt.plot(smoothX, smoothY, label=name)

        ax.set_title(f"Fitted curves (K = {int(10**K)})")
        ax.set_xlabel(f"[{self.freeNames[1]}] / M")
        ax.set_ylabel("ΔAbs / AU")
        ax.legend()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.dfcFrame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self.dfcFrame, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="")

        self.dfcFrame.rowconfigure(0, weight=1)
        self.dfcFrame.rowconfigure(1, weight=1)
        self.dfcFrame.columnconfigure(0, weight=1)

    def plotSpectraDiscrete(self, K):
        self.fitFrame = ttk.Frame(self.notebook)
        self.notebook.add(self.fitFrame, text="Fitted signals")
        fig, (ax) = plt.subplots()

        curves = self.processedData.T
        fittedCurves = self.lastFittedCurves.T
        names = self.signalTitles
        guestConcs = self.totalConcs.T[1]
        for curve, fittedCurve, name in zip(curves, fittedCurves, names):
            fittedZero = fittedCurve[0]
            curve -= fittedZero
            fittedCurve -= fittedZero
            plt.scatter(guestConcs, curve)

            smoothX = np.linspace(guestConcs.min(), guestConcs.max(), 100)
            # make sure the smooth curve actually goes through all the fitted
            # points
            smoothX = np.unique(np.concatenate((smoothX, guestConcs)))

            spl = interp1d(guestConcs, fittedCurve, kind="quadratic")
            smoothY = spl(smoothX)
            plt.plot(smoothX, smoothY, label=name)

        ax.set_title(f"Fitted curves (K = {int(10**K)})")
        ax.set_xlabel(f"[{self.freeNames[1]}] / M")
        ax.set_ylabel("Δδ / ppm")
        ax.legend()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.fitFrame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self.fitFrame, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="")

        self.fitFrame.rowconfigure(0, weight=1)
        self.fitFrame.rowconfigure(1, weight=1)
        self.fitFrame.columnconfigure(0, weight=1)

    def fitData(self):
        K = self.optimise()[0]
        if self.continuous:
            self.plotSpectra(K)
        else:
            self.plotSpectraDiscrete(K)

    def createSpectraFrame(self):
        # TODO: make this a class
        self.spectraFrame = ttk.Frame(self.notebook)
        self.notebook.add(self.spectraFrame, text="Input spectra")

        rangeSelection = ttk.Frame(self.spectraFrame)
        rangeSelection.grid(row=0, column=0, sticky="")

        ttk.Label(rangeSelection, text="Wavelength range:").pack(side="left")

        # TODO: move rounding to titrationReader
        minWL = int(round(self.signalTitles.min()))
        maxWL = int(round(self.signalTitles.max()))
        self.spectraFrame.fromVar = tk.IntVar(self.spectraFrame, minWL)
        self.spectraFrame.toVar = tk.IntVar(self.spectraFrame, maxWL)

        ttk.Spinbox(
            rangeSelection, textvariable=self.spectraFrame.fromVar,
            from_=minWL, to=maxWL, width=5
            ).pack(padx=padding, side="left")

        ttk.Label(rangeSelection, text="to").pack(side="left")

        ttk.Spinbox(
            rangeSelection, textvariable=self.spectraFrame.toVar,
            from_=minWL, to=maxWL, width=5
            ).pack(padx=padding, side="left")

        self.spectraFrame.fig, (self.spectraFrame.ax) = plt.subplots()

        ttk.Button(
            rangeSelection, text="Update", command=self.updateWLRange
        ).pack(side="left")

        canvas = FigureCanvasTkAgg(
            self.spectraFrame.fig, master=self.spectraFrame
        )
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self.spectraFrame, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky="")

        self.spectraFrame.rowconfigure(0, weight=1)
        self.spectraFrame.rowconfigure(1, weight=1)
        self.spectraFrame.rowconfigure(2, weight=1)
        self.spectraFrame.columnconfigure(0, weight=1)

    def drawSpectraFrame(self):
        ax = self.spectraFrame.ax
        fig = self.spectraFrame.fig

        ax.cla()

        spectraColors =\
            ["black"] + ["#80808080"]*(self.numAdditions-2) + ["tab:red"]
        colorCycler = cycler(color=spectraColors)
        ax.set_prop_cycle(colorCycler)

        ax.plot(self.processedSignalTitles, self.processedData.T)

        # TODO: fix hardcoding
        ax.set_xlabel("λ (nm)")
        ax.set_ylabel("Abs (AU)")

        fig.tight_layout()
        fig.canvas.draw_idle()

    def updateWLRange(self):
        from_ = self.spectraFrame.fromVar.get()
        to = self.spectraFrame.toVar.get()
        self.columnFilter = (self.signalTitles.astype(int) >= from_) & \
            (self.signalTitles.astype(int) <= to)
        self.drawSpectraFrame()

    def populateFrame(self):
        if False:
            self.options = ttk.ScrolledFrame(
                self.frame, padding=padding, text="Options", borderwidth=1
            )
            self.options.grid(column=0, row=0, sticky="nesw")

        scrolledFrame = ScrolledFrame(self.frame)
        scrolledFrame.grid(column=0, row=0, sticky="nesw")
        # TODO: frame doesn't receive focus, so scroll wheel doesn't get bound.
        # Fix by binding scroll wheel event to root, then trigger the scrolling
        # method of the currently active notebook tab.
        # scrolledFrame.bind_arrow_keys(self.frame)
        # scrolledFrame.bind_scroll_wheel(self.frame)
        self.options = scrolledFrame.display_widget(ttk.Frame, stretch=True)

        self.notebook = ttk.Notebook(self.frame, padding=padding)
        self.notebook.grid(column=1, row=0, sticky="nesw")
        if self.continuous:
            self.createSpectraFrame()
            self.drawSpectraFrame()
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=4)

        for mod in (
            equilibriumConstants,
            totalConcentrations,
            speciation,
            signals,
            proportionality,
            fitSignals,
            combineResiduals
        ):
            moduleFrame = mod.ModuleFrame(self.options, self)
            moduleFrame.grid(sticky="nesw", pady=padding, ipady=padding)

        fitDataButton = ttk.Button(
            self.options, text="Fit", command=self.fitData
        )
        fitDataButton.grid(sticky="nesw", pady=padding, ipady=padding)

        return
