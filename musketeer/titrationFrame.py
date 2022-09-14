import os
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import packaging.version
from copy import deepcopy

import numpy as np
import tksheet
from scipy.interpolate import make_interp_spline
from cycler import cycler
from ttkbootstrap.widgets import InteractiveNotebook
import tkinter.messagebox as mb
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk, FigureCanvasTkAgg
from matplotlib.figure import Figure

from . import __version__
from . import speciation
from . import equilibriumConstants
from . import totalConcentrations
from . import contributors
from . import proportionality
from . import knownSignals
from . import fitSignals
from . import combineResiduals
from .style import padding
from .scrolledFrame import ScrolledFrame
from .table import Table

warningIcon = "::tk::icons::warning"

titrationModules = [
    speciation,
    equilibriumConstants,
    totalConcentrations,
    contributors,
    proportionality,
    knownSignals,
    fitSignals,
    combineResiduals,
]


class SaveLoadFrame(ttk.Frame):
    def __init__(self, parent, titration, moduleFrames, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.moduleFrames = moduleFrames

        loadOptionsButton = ttk.Button(
            self,
            text="Load Options",
            style="primary.Outline.TButton",
            command=self.loadOptions,
        )
        loadOptionsButton.grid(sticky="nesw", pady=(padding, padding / 2))

        saveOptionsButton = ttk.Button(
            self,
            text="Save Options",
            style="success.Outline.TButton",
            command=self.saveOptions,
        )
        saveOptionsButton.grid(sticky="nesw", pady=padding / 2)

        saveDataButton = ttk.Button(
            self,
            text="Save Processed Data",
            style="success.Outline.TButton",
            command=self.saveData,
        )
        saveDataButton.grid(sticky="nesw", pady=padding / 2)

        self.columnconfigure(0, weight=1)

    def loadOptions(self):
        fileName = fd.askopenfilename(
            title="Load options from file",
            filetypes=[("NumPy archive", "*.npz"), ("all files", "*.*")],
        )
        if fileName == "":
            return

        with np.load(fileName) as options:
            # TODO: check file version against current
            # TODO: show popup to choose which modules should be loaded
            for moduleName, dropdownValue in zip(
                options["moduleNames"], options["dropdownValues"]
            ):
                if moduleName not in self.moduleFrames:
                    continue
                moduleFrame = self.moduleFrames[moduleName]
                if dropdownValue not in moduleFrame.dropdownOptions:
                    continue
                moduleFrame.stringVar.set(dropdownValue)
                moduleFrame.lastValue = dropdownValue

                attributeName = moduleFrame.attributeName
                Strategy = moduleFrame.dropdownOptions[dropdownValue]
                strategy = Strategy(self.titration)
                setattr(self.titration, attributeName, strategy)
                for attr in strategy.popupAttributes:
                    if attr not in options:
                        continue
                    attrValue = options[attr]
                    if attrValue.shape == ():
                        attrValue = attrValue.item()
                    setattr(self.titration, attr, attrValue)

    def saveOptions(self):
        # TODO: handle errors
        popup = tk.Toplevel()
        popup.title("Choose which options to save")
        popupFrame = ttk.Frame(popup, padding=15)
        popupFrame.pack(expand=True, fill="both")

        label = ttk.Label(popupFrame, text="Choose which options to save:")
        label.pack(pady=(5, 15))

        popup.checkbuttons = {}
        popup.saved = False

        for name, moduleFrame in self.moduleFrames.items():
            checkbutton = ttk.Checkbutton(popupFrame, text=moduleFrame.frameLabel)
            if moduleFrame.stringVar.get() == "":
                checkbutton.state(["disabled"])
            else:
                checkbutton.state(["selected"])
            checkbutton.pack(anchor="w", pady=2.5)
            popup.checkbuttons[name] = checkbutton

        buttonsFrame = ttk.Frame(popupFrame)
        buttonsFrame.pack(expand=True, fill="x")

        cancelButton = ttk.Button(
            buttonsFrame,
            text="Cancel",
            style="secondary.TButton",
            command=popup.destroy,
        )
        cancelButton.grid(row=0, column=0, pady=5)

        saveButton = ttk.Button(
            buttonsFrame,
            text="Save",
            style="success.TButton",
            command=lambda: self.getSelectedOptions(popup),
        )
        saveButton.grid(row=0, column=1, pady=5)

        for col in range(2):
            buttonsFrame.columnconfigure(col, weight=1)

        # Only create the warning label now, so that we know what width to make it
        if (
            (
                isinstance(self.titration.rowFilter, slice)
                and self.titration.rowFilter != slice(None)
            )
            or (
                isinstance(self.titration.rowFilter, np.ndarray)
                and not self.titration.rowFilter.all()
            )
            or (
                type(self.titration.columnFilter) == slice
                and self.titration.columnFilter != slice(None)
            )
            or (
                isinstance(self.titration.columnFilter, np.ndarray)
                and not self.titration.columnFilter.all()
            )
        ):
            # row or column filter is active
            warningLabel = ttk.Label(
                popupFrame,
                text=(
                    "The input data has been modified, so it may need to be saved as a"
                    " universal CSV file for some options to be applied to it."
                ),
            )
            if warningIcon in popup.image_names():
                warningLabel.configure(
                    image=warningIcon,
                    compound="left",
                    wraplength=popup.winfo_reqwidth()
                    - popup.tk.call("image", "width", warningIcon),
                )
            else:
                warningLabel.configure(wraplength=popup.winfo_reqwidth())
            warningLabel.pack(before=label)

        popup.resizable(False, False)
        popup.wait_window()
        if not popup.saved:
            return

        options = {}
        moduleNames = np.array(popup.selectedOptions)

        dropdownValues = np.array([])

        for name in moduleNames:
            moduleFrame = self.moduleFrames[name]
            dropdownValue = moduleFrame.stringVar.get()
            dropdownValues = np.append(dropdownValues, dropdownValue)

            Strategy = moduleFrame.dropdownOptions[dropdownValue]
            for attr in Strategy.popupAttributes:
                options[attr] = getattr(self.titration, attr)

        options["version"] = __version__
        options["moduleNames"] = moduleNames
        options["dropdownValues"] = dropdownValues

        initialfile = os.path.splitext(self.titration.title)[0] + "_options"
        fileName = fd.asksaveasfilename(
            title="Save options to file",
            filetypes=[("NumPy archive", "*.npz")],
            initialfile=initialfile,
            defaultextension=".npz",
        )
        if fileName == "":
            return

        np.savez(fileName, **options)

    def getSelectedOptions(self, popup):
        popup.selectedOptions = []
        for name, checkbutton in popup.checkbuttons.items():
            if checkbutton.instate(["selected"]):
                popup.selectedOptions.append(name)
        popup.saved = True
        popup.destroy()

    def saveData(self):
        initialfile = os.path.splitext(self.titration.title)[0] + "_processed_input"
        fileName = fd.asksaveasfilename(
            title="Save processed input data as a universal CSV file",
            initialfile=initialfile,
            filetypes=[("CSV file", "*.csv")],
            defaultextension=".csv",
        )
        data = self.titration.processedData
        rowTitles = np.atleast_2d(self.titration.processedAdditionTitles).T
        columnTitles = np.append("", self.titration.processedSignalTitles)
        output = np.vstack((columnTitles, np.hstack((rowTitles, data))))
        np.savetxt(fileName, output, fmt="%s", delimiter=",")


class TitrationFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.numFits = 0

        # options bar on the left
        scrolledFrame = ScrolledFrame(self)
        scrolledFrame.grid(column=0, row=0, sticky="nesw")
        self.options = scrolledFrame.display_widget(
            ttk.Frame, stretch=True, padding=(0, 0, padding, 0)
        )

        self.moduleFrames = {}
        for mod in titrationModules:
            moduleFrame = mod.ModuleFrame(
                self.options, self.titration, self.updatePlots
            )
            self.moduleFrames[mod.__name__] = moduleFrame
            moduleFrame.grid(sticky="nesw", pady=padding, ipady=padding)

        fitDataButton = ttk.Button(self.options, text="Fit", command=self.tryFitData)
        fitDataButton.grid(sticky="nesw", pady=padding, ipady=padding)

        separator = ttk.Separator(self.options, orient="horizontal")
        separator.grid(sticky="nesw", pady=padding)

        saveLoadFrame = SaveLoadFrame(self.options, self.titration, self.moduleFrames)
        saveLoadFrame.grid(sticky="nesw")

        self.options.columnconfigure(0, weight=1)

        # tabs with different fits
        self.notebook = InteractiveNotebook(
            self, padding=padding, style="Flat.Interactive.TNotebook"
        )
        self.notebook.grid(column=1, row=0, sticky="nesw")

        if self.titration.continuous:
            self.inputSpectraFrame = InputSpectraFrame(self.notebook, self.titration)
            self.notebook.add(self.inputSpectraFrame, text="Input Spectra")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

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

        # TODO: link titrationCopy to options frame as well
        titrationCopy = deepcopy(self.titration)

        if self.titration.continuous:
            continuousFittedFrame = ContinuousFittedFrame(nb, titrationCopy)
            nb.add(continuousFittedFrame, text="Fitted Spectra")
            discreteFittedFrame = DiscreteFromContinuousFittedFrame(nb, titrationCopy)
            nb.add(discreteFittedFrame, text=f"Fit at select {titrationCopy.xQuantity}")
        else:
            discreteFittedFrame = DiscreteFittedFrame(nb, titrationCopy)
            nb.add(discreteFittedFrame, text="Fitted signals")

        speciationFrame = SpeciationFrame(nb, titrationCopy)
        nb.add(speciationFrame, text="Speciation")

        resultsFrame = ResultsFrame(nb, titrationCopy)
        nb.add(resultsFrame, text="Results")

        self.notebook.select(str(nb))
        nb.select(str(discreteFittedFrame))


class InputSpectraFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration

        rangeSelection = ttk.Frame(self)
        rangeSelection.grid(row=0, column=0, sticky="")

        ttk.Label(rangeSelection, text=f"Range of {titration.xQuantity} to fit:").pack(
            side="left"
        )

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

        self.fig = Figure()
        self.ax = self.fig.add_subplot()

        ttk.Button(rangeSelection, text="Update", command=self.updateWLRange).pack(
            side="left"
        )

        canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(canvas, self, pack_toolbar=False)
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

        spectraColors = (
            ["black"] + ["#80808080"] * (titration.numAdditions - 2) + ["tab:red"]
        )
        colorCycler = cycler(color=spectraColors)
        ax.set_prop_cycle(colorCycler)

        ax.plot(titration.processedSignalTitles, titration.processedData.T)

        ax.set_xlabel(f"{titration.xQuantity} / {titration.xUnit}")
        ax.set_ylabel(f"{titration.yQuantity} / {titration.yUnit}")

        fig.tight_layout()
        fig.canvas.draw_idle()

    def updateWLRange(self):
        from_ = float(self.fromSpinbox.get())
        to = float(self.toSpinbox.get())
        self.titration.columnFilter = (self.titration.signalTitles >= from_) & (
            self.titration.signalTitles <= to
        )
        self.plot()


class ContinuousFittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.plot()

    def plot(self):
        titration = self.titration
        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = 10 ** titration.lastKs[: titration.kVarsCount()]
        self.fig = Figure()
        self.ax = self.fig.add_subplot()

        spectra = titration.lastFitResult
        names = titration.contributorNames()
        wavelengths = titration.processedSignalTitles
        for spectrum, name in zip(spectra, names):
            self.ax.plot(wavelengths, spectrum, label=name)

        ttk.Label(self, text=f"Fitted spectra (K = {ks[0]:.0f})", font="-size 15").grid(
            row=0, column=0, sticky=""
        )
        self.ax.set_xlabel(f"{titration.xQuantity} / {titration.xUnit}")
        self.ax.set_ylabel(f"molar {titration.yQuantity} / {titration.yUnit} M⁻¹")
        self.ax.legend()

        self.fig.tight_layout()

        canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        toolbar = NavigationToolbar2Tk(canvas, self, pack_toolbar=False)
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
        self.xQuantity = titration.freeNames[-1]
        self.xConcs = titration.lastTotalConcs.T[-1]
        self.normalisation = False
        self.smooth = True
        self.logScale = False

    def populate(self):
        titration = self.titration
        self.fig = Figure()
        self.ax = self.fig.add_subplot()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        self.toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=2, column=0, sticky="w", padx=10 * padding)

        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = 10 ** titration.lastKs[: titration.kVarsCount()]
        ttk.Label(self, text=f"Fitted curves (K = {ks[0]:.0f})", font="-size 15").grid(
            row=0, column=0, sticky=""
        )

        self.toggleButtonsFrame = ttk.Frame(self)
        self.toggleButtonsFrame.grid(row=1, column=1, sticky="")
        self.normalisationButton = ttk.Checkbutton(
            self.toggleButtonsFrame,
            text="Normalise movement",
            command=self.toggleNormalisation,
            style="Outline.Toolbutton",
        )
        self.normalisationButton.pack(pady=padding, fill="x")
        self.logScaleButton = ttk.Checkbutton(
            self.toggleButtonsFrame,
            text="Logarithmic x axis",
            command=self.toggleLogScale,
            style="Outline.Toolbutton",
        )
        self.logScaleButton.pack(pady=padding, fill="x")
        self.smoothButton = ttk.Checkbutton(
            self.toggleButtonsFrame,
            text="Smooth curves",
            command=self.toggleSmooth,
            style="Outline.Toolbutton",
        )
        self.smoothButton.state(("selected",))
        self.smoothButton.pack(pady=padding, fill="x")

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

    def toggleSmooth(self):
        self.smooth = not self.smooth
        self.plot()

    def plot(self):
        self.ax.clear()

        titration = self.titration

        # xQuantity and xUnit for the fitted plot. Different from the xQuantity
        # and xUnit in the titration object, which are used for the input
        # spectra.
        xQuantity = self.xQuantity
        xUnit = titration.concsUnit
        xConcs = self.xConcs / totalConcentrations.prefixes[xUnit.strip("M")]

        if self.normalisation:
            curves = self.curves.T.copy()
            fittedCurves = self.fittedCurves.T.copy()
            # normalise so that all the fitted curves have the same amplitude
            fittedDiff = self.fittedCurves.T - self.fittedCurves.T[0]
            maxFittedDiff = np.max(abs(fittedDiff), axis=0)
            curves = curves / maxFittedDiff

            diff = curves - curves[0]
            negatives = abs(np.amin(diff, axis=0)) > abs(np.amax(diff, axis=0))
            curves[:, negatives] *= -1
            curves = curves.T * 100

            fittedCurves = fittedCurves / maxFittedDiff
            fittedCurves[:, negatives] *= -1
            fittedCurves = fittedCurves.T * 100
            self.ax.set_ylabel(f"Normalised Δ{titration.yQuantity} / %")
        else:
            curves = self.curves
            fittedCurves = self.fittedCurves
            self.ax.set_ylabel(f"Δ{titration.yQuantity} / {titration.yUnit}")

        for curve, fittedCurve, name in zip(curves, fittedCurves, self.names):
            fittedZero = fittedCurve[0]
            curve -= fittedZero
            fittedCurve -= fittedZero
            self.ax.scatter(xConcs, curve)

            # add step - 1 points between each data point
            step = 10
            smoothXCount = (xConcs.size - 1) * step + 1
            smoothX = np.interp(
                np.arange(smoothXCount), np.arange(smoothXCount, step=step), xConcs
            )

            # make_interp_spline requires all x values to be unique
            filter = np.concatenate((np.diff(xConcs).astype(bool), [True]))
            if (not self.smooth) or xConcs[filter].size < 3:
                # cannot do spline interpolation with fewer than 3 unique x-values
                self.ax.plot(xConcs, fittedCurve, label=name)
                continue
            spl = make_interp_spline(
                xConcs[filter], fittedCurve[filter], bc_type="natural"
            )
            smoothY = spl(smoothX)
            self.ax.plot(smoothX, smoothY, label=name)

        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.ax.set_xlabel(f"[{xQuantity}] / {xUnit}")
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


class SpeciationFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.xQuantity = titration.freeNames[-1]
        self.xConcs = titration.lastTotalConcs.T[-1]
        self.speciesVar = tk.StringVar(self)
        self.logScale = False
        self.smooth = True
        self.populate()
        self.plot()

    def populate(self):
        titration = self.titration
        self.fig = Figure()
        self.ax = self.fig.add_subplot()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="")

        self.toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=2, column=0, sticky="w", padx=10 * padding)

        self.optionsFrame = ttk.Frame(self)
        self.optionsFrame.grid(row=1, column=1, sticky="")
        self.speciesLabel = ttk.Label(
            self.optionsFrame, anchor="center", justify="center", text="Select species:"
        )
        self.speciesLabel.pack(pady=padding, fill="x")

        self.speciesDropdown = ttk.OptionMenu(
            self.optionsFrame,
            self.speciesVar,
            titration.freeNames[0],
            command=lambda *args: self.plot(),
            *titration.freeNames,
            style="primary.Outline.TMenubutton",
        )
        self.speciesDropdown.pack()
        self.logScaleButton = ttk.Checkbutton(
            self.optionsFrame,
            text="Logarithmic x axis",
            command=self.toggleLogScale,
            style="Outline.Toolbutton",
        )
        self.logScaleButton.pack(pady=padding, fill="x")
        self.smoothButton = ttk.Checkbutton(
            self.optionsFrame,
            text="Smooth curves",
            command=self.toggleSmooth,
            style="Outline.Toolbutton",
        )
        self.smoothButton.state(("selected",))
        self.smoothButton.pack(pady=padding, fill="x")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.grid_anchor("center")

    def toggleLogScale(self):
        self.logScale = not self.logScale
        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.canvas.draw()

    def toggleSmooth(self):
        self.smooth = not self.smooth
        self.plot()

    @property
    def freeIndex(self):
        return np.where(self.titration.freeNames == self.speciesVar.get())[0][0]

    def plot(self):
        self.ax.clear()

        titration = self.titration

        # xQuantity and xUnit for the fitted plot. Different from the xQuantity
        # and xUnit in the titration object, which are used for the input
        # spectra.
        totalConcs = titration.lastTotalConcs[:, self.freeIndex]
        additionsFilter = totalConcs != 0
        totalConcs = totalConcs[additionsFilter]

        xQuantity = self.xQuantity
        xUnit = titration.concsUnit
        xConcs = (
            self.xConcs[additionsFilter]
            / totalConcentrations.prefixes[xUnit.strip("M")]
        )

        freeConcs = titration.lastFreeConcs[additionsFilter, :][:, self.freeIndex]
        freeName = self.speciesVar.get()

        factor = abs(titration.stoichiometries[:, self.freeIndex])
        boundFilter = factor.astype(bool)

        boundConcs = titration.lastBoundConcs * factor
        boundConcs = boundConcs[additionsFilter, :][:, boundFilter]
        boundNames = titration.boundNames[boundFilter]

        curves = 100 * np.vstack((freeConcs, boundConcs.T)) / totalConcs
        names = np.append(freeName, boundNames)
        self.ax.set_ylabel(f"% of {freeName}")

        for curve, name in zip(curves, names):
            # add step - 1 points between each data point
            step = 10
            smoothXCount = (xConcs.size - 1) * step + 1
            smoothX = np.interp(
                np.arange(smoothXCount), np.arange(smoothXCount, step=step), xConcs
            )

            # make_interp_spline requires all x values to be unique
            filter = np.concatenate((np.diff(xConcs).astype(bool), [True]))
            if (not self.smooth) or xConcs[filter].size < 3:
                # cannot do spline interpolation with fewer than 3 unique x-values
                self.ax.plot(xConcs, curve, label=name)
                continue
            spl = make_interp_spline(xConcs[filter], curve[filter], bc_type="natural")
            smoothY = spl(smoothX)
            self.ax.plot(smoothX, smoothY, label=name)

        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.ax.set_xlabel(f"[{xQuantity}] / {xUnit}")
        self.ax.legend()
        self.fig.tight_layout()

        self.canvas.draw()


class ResultsFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.showResults()

    def showResults(self):
        titration = self.titration
        kTable = Table(
            self,
            0,
            0,
            ["K (M⁻ⁿ)", "α"],
            rowOptions=("readonlyTitles",),
            columnOptions=("readonlyTitles",),
        )

        ks = self.titration.knownKs.copy()
        ks[np.isnan(ks)] = 10 ** titration.lastKs[: titration.kVarsCount()]

        alphas = titration.knownAlphas.copy()
        polymerAlphas = alphas[np.any(titration.stoichiometries < 0, 1)]
        polymerAlphas[np.isnan(polymerAlphas)] = (
            10
            ** titration.lastKs[titration.kVarsCount() + titration.getConcVarsCount() :]
        )

        for kVarName, k, alpha in zip(self.titration.kVarsNames, ks, alphas):
            kTable.addRow(kVarName, [np.rint(k), alpha if not np.isnan(alpha) else ""])
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

        saveButton = ttk.Button(
            self, text="Save as CSV", command=self.saveCSV, style="success.TButton"
        )
        saveButton.pack(side="top", pady=15)

    def saveCSV(self):
        initialfile = os.path.splitext(self.titration.title)[0] + "_fit"
        fileName = fd.asksaveasfilename(
            title="Save fitted spectra",
            initialfile=initialfile,
            filetypes=[("CSV file", "*.csv")],
            defaultextension=".csv",
        )
        data = self.titration.lastFitResult
        rowTitles = np.atleast_2d(self.titration.contributorNames()).T
        columnTitles = np.append("", self.titration.processedSignalTitles)
        output = np.vstack((columnTitles, np.hstack((rowTitles, data))))
        np.savetxt(fileName, output, fmt="%s", delimiter=",")
