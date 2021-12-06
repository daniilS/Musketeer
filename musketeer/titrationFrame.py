import tkinter.ttk as ttk
import tkinter.filedialog as fd

import numpy as np
import tksheet
from scipy.interpolate import interp1d
from cycler import cycler
from ttkbootstrap.widgets import InteractiveNotebook
import tkinter.messagebox as mb

from . import speciation
from . import equilibriumConstants
from . import totalConcentrations
from . import contributors
from . import proportionality
from . import fitSignals
from . import combineResiduals
from . import knownSignals
from .style import padding
from .scrolledFrame import ScrolledFrame
from .table import Table

# need to tell matplotlib to use the tkinter backend, otherwise the scale
# of figures can get messed up if it would default to a different backend
import matplotlib
matplotlib.use("TkAgg")

# TODO: stop using pyplot to avoid window closing issues?
import matplotlib.pyplot as plt  # noqa
from matplotlib.backends.backend_tkagg import (  # noqa
    NavigationToolbar2Tk, FigureCanvasTkAgg
)
from matplotlib.backend_bases import key_press_handler  # noqa


class TitrationFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.numFits = 0

        # options bar on the left
        scrolledFrame = ScrolledFrame(self)
        scrolledFrame.grid(column=0, row=0, sticky="nesw")
        # TODO: frame doesn't receive focus, so scroll wheel doesn't get bound.
        # Fix by binding scroll wheel event to root, then trigger the scrolling
        # method of the currently active notebook tab.
        # scrolledFrame.bind_arrow_keys(self)
        # scrolledFrame.bind_scroll_wheel(self)
        self.options = scrolledFrame.display_widget(ttk.Frame, stretch=True)

        for mod in (
            speciation,
            equilibriumConstants,
            totalConcentrations,
            contributors,
            proportionality,
            knownSignals,
            fitSignals,
            combineResiduals
        ):
            moduleFrame = mod.ModuleFrame(
                self.options, self.titration, self.updatePlots
            )
            moduleFrame.grid(sticky="nesw", pady=padding, ipady=padding)

        fitDataButton = ttk.Button(
            self.options, text="Fit", command=self.tryFitData
        )
        fitDataButton.grid(sticky="nesw", pady=padding, ipady=padding)

        # tabs with different fits
        self.notebook = InteractiveNotebook(self, padding=padding,
                                            style="Flat.Interactive.TNotebook")
        self.notebook.grid(column=1, row=0, sticky="nesw")

        if self.titration.continuous:
            self.inputSpectraFrame = InputSpectraFrame(self.notebook,
                                                       self.titration)
            self.notebook.add(self.inputSpectraFrame, text="Input Spectra")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=4)

    def updatePlots(self):
        if hasattr(self, "inputSpectraFrame"):
            self.inputSpectraFrame.plot()

    def tryFitData(self, *args, **kwargs):
        try:
            self.fitData(*args, **kwargs)
        except Exception as e:
            mb.showerror(title="Failed to fit data", message=e, parent=self)
            return

    def fitData(self):
        self.titration.fitData()
        self.numFits += 1
        nb = ttk.Notebook(self, padding=padding, style="Flat.TNotebook")
        self.notebook.add(nb, text=f"Fit {self.numFits}")

        if self.titration.continuous:
            continuousFittedFrame = ContinuousFittedFrame(nb, self.titration)
            nb.add(continuousFittedFrame, text="Fitted Spectra")
            discreteFittedFrame = DiscreteFromContinuousFittedFrame(
                nb, self.titration)
            nb.add(discreteFittedFrame,
                   text="Fitted spectra (select wavelengths)")
        else:
            discreteFittedFrame = DiscreteFittedFrame(nb, self.titration)
            nb.add(discreteFittedFrame, text="Fitted signals")

        resultsFrame = ResultsFrame(nb, self.titration)
        nb.add(resultsFrame, text="Results")

        self.notebook.select(str(nb))


class InputSpectraFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration

        rangeSelection = ttk.Frame(self)
        rangeSelection.grid(row=0, column=0, sticky="")

        ttk.Label(rangeSelection, text="Wavelength range:").pack(side="left")

        minWL = self.titration.signalTitles.min()
        maxWL = self.titration.signalTitles.max()
        decimals = self.titration.signalTitlesDecimals
        step = 1 / (10 ** decimals)

        self.fromSpinbox = ttk.Spinbox(
            rangeSelection, from_=minWL, to=maxWL, width=5, increment=step
        )
        self.fromSpinbox.set(f"{minWL:.{decimals}f}")
        self.fromSpinbox.pack(padx=padding, side="left")

        ttk.Label(rangeSelection, text="to").pack(side="left")

        self.toSpinbox = ttk.Spinbox(
            rangeSelection, from_=minWL, to=maxWL, width=5, increment=step
        )
        self.toSpinbox.set(f"{maxWL:.{decimals}f}")
        self.toSpinbox.pack(padx=padding, side="left")

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
        toolbar.grid(row=2, column=0, sticky="w", padx=10 * padding)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.grid_anchor("center")

        self.plot()

    def plot(self):
        ax = self.ax
        fig = self.fig
        titration = self.titration

        ax.cla()

        spectraColors = ["black"] +\
            ["#80808080"] * (titration.numAdditions - 2) +\
            ["tab:red"]
        colorCycler = cycler(color=spectraColors)
        ax.set_prop_cycle(colorCycler)

        ax.plot(
            titration.processedSignalTitles,
            titration.processedData.T
        )

        ax.set_xlabel(f"{titration.xQuantity} / {titration.xUnit}")
        ax.set_ylabel(f"{titration.yQuantity} / {titration.yUnit}")

        fig.tight_layout()
        fig.canvas.draw_idle()

    def updateWLRange(self):
        from_ = float(self.fromSpinbox.get())
        to = float(self.toSpinbox.get())
        self.titration.columnFilter = \
            (self.titration.signalTitles >= from_) & \
            (self.titration.signalTitles <= to)
        self.plot()


class ContinuousFittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.plot()

    def plot(self):
        titration = self.titration
        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = 10**titration.lastKs[:titration.kVarsCount()]
        fig, (ax) = plt.subplots()

        spectra = titration.lastFitResult
        names = titration.contributorNames()
        wavelengths = titration.processedSignalTitles
        for spectrum, name in zip(spectra, names):
            plt.plot(wavelengths, spectrum, label=name)

        ttk.Label(
            self, text=f"Fitted spectra (K = {ks[0]:.0f})",
            font='-size 15'
        ).grid(row=0, column=0, sticky="")
        ax.set_xlabel(f"{titration.xQuantity} / {titration.xUnit}")
        ax.set_ylabel(
            f"{titration.contributorQuantity} / {titration.contributorUnit}"
        )
        ax.legend()

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(
            canvas, self, pack_toolbar=False
        )
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky="w", padx=10 * padding)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.grid_anchor("center")


class FittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.guestConcs = titration.lastFreeConcs.T[-1]
        self.normalisation = False
        self.logScale = False

    def populate(self):
        titration = self.titration
        self.fig, self.ax = plt.subplots()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        self.toolbar = NavigationToolbar2Tk(
            self.canvas, self, pack_toolbar=False
        )
        self.toolbar.update()
        self.toolbar.grid(row=2, column=0, sticky="w", padx=10 * padding)

        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = 10**titration.lastKs[:titration.kVarsCount()]
        ttk.Label(
            self, text=f"Fitted curves (K = {ks[0]:.0f})",
            font='-size 15'
        ).grid(row=0, column=0, sticky="")

        self.toggleButtonsFrame = ttk.Frame(self)
        self.toggleButtonsFrame.grid(row=1, column=1, sticky="")
        self.normalisationButton = ttk.Checkbutton(
            self.toggleButtonsFrame, text="Normalise movement",
            command=self.toggleNormalisation, style="Outline.Toolbutton"
        )
        self.normalisationButton.pack(pady=padding, fill="x")
        self.logScaleButton = ttk.Checkbutton(
            self.toggleButtonsFrame, text="Logarithmic x axis",
            command=self.toggleLogScale, style="Outline.Toolbutton"
        )
        self.logScaleButton.pack(pady=padding, fill="x")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.grid_anchor("center")

    def toggleNormalisation(self):
        self.normalisation = not self.normalisation
        self.plot()

    def toggleLogScale(self):
        self.logScale = not self.logScale
        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.canvas.draw()

    def plot(self):
        self.ax.clear()

        titration = self.titration

        guestConcs = self.guestConcs

        if self.normalisation:
            curves = self.curves.T
            # get the largest difference from the first point for each signal
            diff = curves - curves[0]
            maxDiff = np.max(abs(diff), axis=0)
            curves = curves / maxDiff
            curves = curves.T * 100

            fittedCurves = self.fittedCurves.T
            fittedCurves = fittedCurves / maxDiff
            fittedCurves = fittedCurves.T * 100
            self.ax.set_ylabel(f"Normalised Δ{titration.yQuantity} / %")
        else:
            curves = self.curves
            fittedCurves = self.fittedCurves
            self.ax.set_ylabel(f"Δ{titration.yQuantity} / {titration.yUnit}")

        for curve, fittedCurve, name in zip(curves,
                                            fittedCurves,
                                            self.names):
            fittedZero = fittedCurve[0]
            curve -= fittedZero
            fittedCurve -= fittedZero
            self.ax.scatter(guestConcs, curve)

            smoothX = np.linspace(guestConcs.min(), guestConcs.max(), 100)
            # make sure the smooth curve actually goes through all the fitted
            # points
            smoothX = np.unique(np.concatenate((smoothX, guestConcs)))

            # interp1d requires all x values to be unique
            filter = np.concatenate((np.diff(guestConcs).astype(bool), [True]))
            spl = interp1d(guestConcs[filter], fittedCurve[filter],
                           kind="quadratic")
            smoothY = spl(smoothX)
            self.ax.plot(smoothX, smoothY, label=name)

        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.ax.set_xlabel(f"[{titration.freeNames[-1]}] / M")
        self.ax.legend()
        self.fig.tight_layout()

        self.canvas.draw()


class DiscreteFittedFrame(FittedFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curves = self.titration.processedData.T
        self.fittedCurves = self.titration.lastFittedCurves.T
        self.names = self.titration.processedSignalTitlesStrings
        self.populate()
        self.plot()


class DiscreteFromContinuousFittedFrame(FittedFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        peakIndices = self.titration.getPeakIndices()
        self.curves = self.titration.processedData.T[peakIndices]
        self.fittedCurves = self.titration.lastFittedCurves.T[peakIndices]
        peakTitles = self.titration.processedSignalTitlesStrings[peakIndices]
        self.names = [f"{title} {self.titration.xUnit}" for title in peakTitles]
        self.populate()
        self.plot()


class ResultsFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.showResults()

    def showResults(self):
        titration = self.titration
        kTable = Table(self, 0, 0, ["K", "α"], rowOptions=("readonlyTitles"),
                       columnOptions=("readonlyTitles"))

        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = 10**titration.lastKs[:titration.kVarsCount()]

        alphas = titration.knownAlphas.copy()
        polymerAlphas = alphas[np.any(titration.stoichiometries < 0, 1)]
        polymerAlphas[np.isnan(polymerAlphas)] = 10**titration.lastKs[
            titration.kVarsCount() + titration.getConcVarsCount():]

        for boundName, k, alpha in zip(self.titration.boundNames, ks, alphas):
            kTable.addRow(boundName,
                          [np.rint(k), alpha if not np.isnan(alpha) else ""])
        kTable.pack(side="top", pady=15)

        sheet = tksheet.Sheet(
            self,
            data=list(np.around(titration.lastFitResult, 2)),
            headers=list(titration.processedSignalTitlesStrings),
            row_index=list(titration.contributorNames()),
            set_all_heights_and_widths=True,
        )
        sheet.enable_bindings()
        sheet.pack(side="top", pady=15, fill="x")

        saveButton = ttk.Button(self, text="Save as CSV",
                                command=self.saveCSV, style="success.TButton")
        saveButton.pack(side="top", pady=15)

    def saveCSV(self):
        fileName = fd.asksaveasfilename(filetypes=[("CSV file", "*.csv")],
                                        defaultextension=".csv")
        data = self.titration.lastFitResult
        rowTitles = np.atleast_2d(self.titration.contributorNames()).T
        columnTitles = np.append("", self.titration.processedSignalTitles)
        output = np.vstack((columnTitles, np.hstack((rowTitles, data))))
        np.savetxt(fileName, output, fmt="%s", delimiter=",")
