import tkinter as tk
import tkinter.ttk as ttk

import numpy as np
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


class TitrationFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration

        # options bar on the left
        scrolledFrame = ScrolledFrame(self)
        scrolledFrame.grid(column=0, row=0, sticky="nesw")
        # TODO: frame doesn't receive focus, so scroll wheel doesn't get bound.
        # Fix by binding scroll wheel event to root, then trigger the scrolling
        # method of the currently active notebook tab.
        # scrolledFrame.bind_arrow_keys(self.frame)
        # scrolledFrame.bind_scroll_wheel(self.frame)
        self.options = scrolledFrame.display_widget(ttk.Frame, stretch=True)

        for mod in (
            equilibriumConstants,
            totalConcentrations,
            speciation,
            signals,
            proportionality,
            fitSignals,
            combineResiduals
        ):
            moduleFrame = mod.ModuleFrame(
                self.options, self.titration, self.updatePlots
            )
            moduleFrame.grid(sticky="nesw", pady=padding, ipady=padding)

        fitDataButton = ttk.Button(
            self.options, text="Fit", command=self.fitData
        )
        fitDataButton.grid(sticky="nesw", pady=padding, ipady=padding)

        # tabs with various plots
        self.notebook = ttk.Notebook(self, padding=padding)
        self.notebook.grid(column=1, row=0, sticky="nesw")

        if self.titration.continuous:
            self.inputSpectraFrame = InputSpectraFrame(self, self.titration)
            self.notebook.add(self.inputSpectraFrame, text="Input Spectra")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=4)

    def updatePlots(self):
        if hasattr(self, "inputSpectraFrame"):
            self.inputSpectraFrame.plot()

    def fitData(self):
        self.titration.fitData()
        if self.titration.continuous:
            self.continuousFittedFrame = ContinuousFittedFrame(
                self, self.titration
            )
            self.notebook.add(
                self.continuousFittedFrame, text="Fitted Spectra"
            )
            self.discreteFittedFrame = DiscreteFromContinuousFittedFrame(
                self, self.titration
            )
            self.notebook.add(
                self.discreteFittedFrame,
                text="Fitted spectra (select wavelengths)"
            )
        else:
            self.discreteFittedFrame = DiscreteFittedFrame(
                self, self.titration
            )
            self.notebook.add(
                self.discreteFittedFrame,
                text="Fitted signals"
            )


class InputSpectraFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration

        rangeSelection = ttk.Frame(self)
        rangeSelection.grid(row=0, column=0, sticky="")

        ttk.Label(rangeSelection, text="Wavelength range:").pack(side="left")

        # TODO: move rounding to titrationReader
        minWL = int(round(self.titration.signalTitles.min()))
        maxWL = int(round(self.titration.signalTitles.max()))
        self.fromVar = tk.IntVar(self, minWL)
        self.toVar = tk.IntVar(self, maxWL)

        ttk.Spinbox(
            rangeSelection, textvariable=self.fromVar,
            from_=minWL, to=maxWL, width=5
            ).pack(padx=padding, side="left")

        ttk.Label(rangeSelection, text="to").pack(side="left")

        ttk.Spinbox(
            rangeSelection, textvariable=self.toVar,
            from_=minWL, to=maxWL, width=5
            ).pack(padx=padding, side="left")

        self.fig, (self.ax) = plt.subplots()

        ttk.Button(
            rangeSelection, text="Update", command=self.updateWLRange
        ).pack(side="left")

        canvas = FigureCanvasTkAgg(
            self.fig, master=self
        )
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky="")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        self.plot()

    def plot(self):
        ax = self.ax
        fig = self.fig
        titration = self.titration

        ax.cla()

        spectraColors =\
            ["black"] + ["#80808080"]*(titration.numAdditions-2) + ["tab:red"]
        colorCycler = cycler(color=spectraColors)
        ax.set_prop_cycle(colorCycler)

        ax.plot(
            titration.processedSignalTitles,
            titration.processedData.T
        )

        # TODO: fix hardcoding
        ax.set_xlabel("λ (nm)")
        ax.set_ylabel("Abs (AU)")

        fig.tight_layout()
        fig.canvas.draw_idle()

    def updateWLRange(self):
        from_ = self.fromVar.get()
        to = self.toVar.get()
        self.titration.columnFilter = \
            (self.titration.signalTitles.astype(int) >= from_) & \
            (self.signalTitles.astype(int) <= to)
        self.drawPlot()


class ContinuousFittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.plot()

    def plot(self):
        titration = self.titration
        K = titration.lastKs[0]  # TODO: support multiple Ks
        fig, (ax) = plt.subplots()

        spectra = titration.lastFitResult
        names = titration.signalNames
        wavelengths = titration.processedSignalTitles
        for spectrum, name in zip(spectra, names):
            plt.plot(wavelengths, spectrum, label=name)

        ttk.Label(
            self, text=f"Fitted spectra (K = {int(10**K)})",
            font='-size 15'
        ).grid(row=0, column=0, sticky="")
        ax.set_xlabel("λ / nm")
        ax.set_ylabel("ε / $M^{-1} cm^{-1}$")
        ax.legend()

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky="")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)


class DiscreteFromContinuousFittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.plot()

    def plot(self):
        titration = self.titration
        K = titration.lastKs[0]  # TODO: support multiple Ks
        fig, (ax) = plt.subplots()

        # TODO: move to Titration class
        # get the total movement at each wavelength
        movement = abs(np.diff(titration.processedData, axis=0)).sum(axis=0)
        # get the largest difference from the first point at each wavelength
        diff = titration.processedData - titration.processedData[0]
        maxDiff = np.max(abs(diff), axis=0)
        # find the wavelengths with the largest total movement
        peaksIndices, peakProperties = find_peaks(movement, prominence=0)
        prominences = peakProperties["prominences"]
        # select the four most prominent peaks
        largestFilter = prominences.argsort()[-4:]
        largestPeaksIndices = peaksIndices[largestFilter]

        # Shoulder peaks can appear as inflection points rather than maxima.
        # We'll add the two most prominent inflection points from a first-order
        # approximation of the first derivative of the total movement:
        inflectionIndices, inflectionProperties = \
            find_peaks(-abs(np.diff(movement)), prominence=0)
        inflectionProminences = inflectionProperties["prominences"]
        inflectionFilter = inflectionProminences.argsort()[-2:]
        largestInflectionsIndices = inflectionIndices[inflectionFilter]

        # combine the two arrays, without duplicates, and sort them
        largestPeaksIndices = np.sort(np.unique(np.concatenate(
            (largestPeaksIndices, largestInflectionsIndices)
        )))

        # discard peaks that don't move far enough away from the baseline
        # compared to the other peaks
        peaksDiff = maxDiff[largestPeaksIndices]
        threshold = np.max(peaksDiff) / 10
        filteredPeaks = largestPeaksIndices[peaksDiff >= threshold]

        curves = titration.processedData.T[filteredPeaks]
        fittedCurves = titration.lastFittedCurves.T[filteredPeaks]
        names = np.char.add(
            # TODO: move rounding to titrationReader
            titration.processedSignalTitles[filteredPeaks]
            .round().astype(int).astype(str),
            " nm"
        )
        guestConcs = titration.totalConcs.T[1]
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

        ttk.Label(
            self, text=f"Fitted curves (K = {int(10**K)})",
            font='-size 15'
        ).grid(row=0, column=0, sticky="")
        ax.set_xlabel(f"[{titration.freeNames[1]}] / M")
        ax.set_ylabel("ΔAbs / AU")
        ax.legend()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky="")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)


class DiscreteFittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.plot()

    def plot(self):
        titration = self.titration
        K = titration.lastKs[0]  # TODO: support multiple Ks
        fig, (ax) = plt.subplots()

        curves = titration.processedData.T
        fittedCurves = titration.lastFittedCurves.T
        names = titration.signalTitles
        guestConcs = titration.totalConcs.T[1]
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

        ttk.Label(
            self, text=f"Fitted curves (K = {int(10**K)})",
            font='-size 15'
        ).grid(row=0, column=0, sticky="")
        ax.set_xlabel(f"[{titration.freeNames[1]}] / M")
        ax.set_ylabel("Δδ / ppm")
        ax.legend()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky="")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
