import os
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from copy import deepcopy
from pathlib import PurePath

import numpy as np
import tksheet
from cycler import cycler
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.interpolate import make_interp_spline
from ttkbootstrap.widgets import InteractiveNotebook

from . import (
    __version__,
    combineResiduals,
    contributors,
    editData,
    equilibriumConstants,
    fitSignals,
    knownSignals,
    proportionality,
    speciation,
    totalConcentrations,
)
from .patchMatplotlib import NavigationToolbarVertical
from .scrolledFrame import ScrolledFrame
from .style import padding
from .table import Table
from .titration import Titration, titrationAttributes

# Magic value indicating that the data in a .fit file should be copied from the original
# titration
COPY_ORIGINAL_ARRAY = "COPY_OGIRINAL_ARRAY"

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


class TitrationFrame(ttk.Frame):
    def __init__(self, parent, titration, filePath=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.filePath = filePath
        self.numFits = 0

        # options bar on the left
        scrolledFrame = ScrolledFrame(self)
        scrolledFrame.grid(column=0, row=0, sticky="nesw")
        self.options = scrolledFrame.display_widget(
            ttk.Frame, stretch=True, padding=(0, 0, padding, 0)
        )

        editDataButton = ttk.Button(
            self.options,
            text="Edit data",
            command=self.editData,
            style="Outline.TButton",
        )
        editDataButton.grid(sticky="nesw", pady=padding)

        self.moduleFrames = {}
        for mod in titrationModules:
            moduleFrame = mod.ModuleFrame(self.options)
            self.moduleFrames[mod.__name__] = moduleFrame
            moduleFrame.grid(sticky="nesw", pady=padding, ipady=padding)

        fitDataButton = ttk.Button(
            self.options, style="success.TButton", text="Fit", command=self.fitData
        )
        fitDataButton.grid(sticky="nesw", pady=padding, ipady=padding)

        separator = ttk.Separator(self.options, orient="horizontal")
        separator.grid(sticky="nesw", pady=padding)

        copyFitButton = ttk.Button(self.options, text="Copy fit", command=self.copyFit)
        copyFitButton.grid(sticky="nesw", pady=padding, ipady=padding)

        self.options.columnconfigure(0, weight=1)

        # tabs with different fits
        self.notebook = InteractiveNotebook(
            self,
            padding=padding,
            newtab=self.newFit,
            style="Flat.Interactive.TNotebook",
        )
        self.notebook.grid(column=1, row=0, sticky="nesw")

        if type(titration) is Titration:
            self.originalTitration = titration
            self.newFit()
        elif type(titration) is np.lib.npyio.NpzFile:
            self.originalTitration = Titration()
            for attribute in titrationAttributes:
                try:
                    value = titration[f".original.{attribute}"]
                except KeyError:
                    continue
                if value.shape == ():
                    value = value.item()
                setattr(self.originalTitration, attribute, value)

            for name in titration[".fits"]:
                fit = Titration()

                for attribute in titrationAttributes:
                    try:
                        value = titration[f"{name}.{attribute}"]
                    except KeyError:
                        continue

                    if value.shape == ():
                        value = value.item()
                    if (type(value) == type(COPY_ORIGINAL_ARRAY)) and (
                        value == COPY_ORIGINAL_ARRAY
                    ):
                        value = getattr(self.originalTitration, attribute).copy()
                    setattr(fit, attribute, value)

                for module in titrationModules:
                    moduleFrame = module.ModuleFrame
                    # in case no valid strategy is present in the loaded file
                    setattr(fit, moduleFrame.attributeName, None)

                    try:
                        SelectedStrategy = moduleFrame.dropdownOptions[
                            titration[f"{name}.{moduleFrame.attributeName}"].item()
                        ]
                    except KeyError:
                        # no stategy selected
                        continue

                    selectedStrategy = SelectedStrategy(fit)
                    for popupAttributeName in selectedStrategy.popupAttributes:
                        key = f"{name}.{moduleFrame.attributeName}.{popupAttributeName}"
                        try:
                            popupAttribute = titration[key]
                        except KeyError:
                            continue
                        if popupAttribute.shape == ():
                            popupAttribute = popupAttribute.item()
                        setattr(selectedStrategy, popupAttributeName, popupAttribute)

                    try:
                        selectedStrategy.checkAttributes()
                    except NotImplementedError:
                        # required attribute missing
                        continue

                    setattr(fit, moduleFrame.attributeName, selectedStrategy)

                self.newFit(fit, name, setDefault=False)

            self.numFits = titration[".numFits"].item()

        self.notebook.bind("<<NotebookTabChanged>>", self.switchFit, add=True)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def editData(self):
        root = self.winfo_toplevel()
        popup = editData.EditDataPopup(self.currentTab.titration, master=root)
        popup.geometry(f"+{root.winfo_x()+100}+{root.winfo_y()+100}")
        popup.show()
        if hasattr(self.currentTab, "inputSpectraFrame"):
            self.currentTab.inputSpectraFrame.plot()

    @property
    def currentTab(self):
        return self.notebook.nametowidget(self.notebook.select())

    # TODO: make inner notebooks into separate class
    def newFit(self, titration=None, name=None, setDefault=True):
        if titration is None:
            titration = deepcopy(self.originalTitration)
        for moduleFrame in self.moduleFrames.values():
            moduleFrame.update(titration, setDefault)
        self.numFits += 1
        nb = ttk.Notebook(self, padding=padding, style="Flat.TNotebook")
        nb.titration = titration
        if name is None:
            name = f"Fit {self.numFits}"
            titration.title = name
        self.notebook.add(nb, text=name)

        if titration.continuous:
            nb.inputSpectraFrame = InputSpectraFrame(nb, nb.titration)
            nb.add(nb.inputSpectraFrame, text="Input Spectra")

        if hasattr(titration, "fitResult"):
            try:
                self.showFit(nb)
            except Exception:
                pass  # TODO make more robust
        self.notebook.select(str(nb))

    def copyFit(self):
        self.newFit(deepcopy(self.currentTab.titration), setDefault=False)

    def switchFit(self, event):
        nb = self.currentTab
        for moduleFrame in self.moduleFrames.values():
            moduleFrame.update(nb.titration)

    def fitData(self):
        nb = self.currentTab
        try:
            nb.titration.fitData()
        except Exception as e:
            mb.showerror(title="Failed to fit data", message=e, parent=self)
            return
        self.showFit(nb)

    def showFit(self, nb):
        if hasattr(nb.titration, "fitResult"):
            lastTabClass = type(nb.nametowidget(nb.select()))
            for tab in nb.tabs():
                widget = nb.nametowidget(tab)
                if isinstance(widget, InputSpectraFrame):
                    continue
                nb.forget(widget)
                widget.destroy()
        else:
            lastTabClass = None

        if nb.titration.continuous:
            nb.continuousFittedFrame = ContinuousFittedFrame(nb, nb.titration)
            nb.add(nb.continuousFittedFrame, text="Fitted Spectra")
            nb.discreteFittedFrame = DiscreteFromContinuousFittedFrame(nb, nb.titration)
            nb.add(
                nb.discreteFittedFrame, text=f"Fit at select {nb.titration.xQuantity}"
            )
        else:
            nb.discreteFittedFrame = DiscreteFittedFrame(nb, nb.titration)
            nb.add(nb.discreteFittedFrame, text="Fitted signals")

        nb.speciationFrame = SpeciationFrame(nb, nb.titration)
        nb.add(nb.speciationFrame, text="Speciation")

        nb.resultsFrame = ResultsFrame(nb, nb.titration)
        nb.add(nb.resultsFrame, text="Results")

        if lastTabClass is not None:
            for tab in nb.tabs():
                widget = nb.nametowidget(tab)
                if isinstance(widget, lastTabClass):
                    nb.select(str(widget))
                    break
        else:
            nb.select(str(nb.discreteFittedFrame))

    def saveFile(self, saveAs=False):
        options = {}
        options[".version"] = __version__
        options[".numFits"] = self.numFits

        for titrationAttribute in titrationAttributes:
            try:
                options[f".original.{titrationAttribute}"] = getattr(
                    self.originalTitration, titrationAttribute
                )
            except AttributeError:
                continue

        fits = np.array([])

        for tkpath in self.notebook.tabs():
            tab = self.notebook.nametowidget(tkpath)
            if not isinstance(tab, ttk.Notebook):
                continue
            fit = self.notebook.tab(tkpath)["text"][: -self.notebook._padding_spaces]
            fits = np.append(fits, fit)

            titration = tab.titration
            for titrationAttribute in titrationAttributes:
                if (titrationAttribute == "rawData") and np.array_equal(
                    titration.rawData, self.originalTitration.rawData
                ):
                    options[f"{fit}.{titrationAttribute}"] = COPY_ORIGINAL_ARRAY
                    continue

                try:
                    options[f"{fit}.{titrationAttribute}"] = getattr(
                        titration, titrationAttribute
                    )
                except AttributeError:
                    continue

            for module in titrationModules:
                moduleFrame = module.ModuleFrame
                strategy = getattr(titration, moduleFrame.attributeName)
                if strategy is None:
                    continue

                options[f"{fit}.{moduleFrame.attributeName}"] = list(
                    moduleFrame.dropdownOptions.keys()
                )[
                    list(moduleFrame.dropdownOptions.values()).index(
                        type(getattr(titration, moduleFrame.attributeName))
                    )
                ]

                for popupAttributeName in strategy.popupAttributes:
                    options[
                        f"{fit}.{moduleFrame.attributeName}.{popupAttributeName}"
                    ] = getattr(strategy, popupAttributeName)

        options[".fits"] = fits

        if self.filePath is None:
            filePath = fd.asksaveasfilename(
                title="Save as",
                initialfile="New Titration.fit",
                filetypes=[("Musketeer file", "*.fit")],
                defaultextension=".fit",
            )
        elif saveAs or PurePath(self.filePath).suffix != ".fit":
            filePath = fd.asksaveasfilename(
                title="Save as",
                initialdir=PurePath(self.filePath).parent,
                initialfile=PurePath(self.filePath).stem + ".fit",
                filetypes=[("Musketeer file", "*.fit")],
                defaultextension=".fit",
            )
        else:
            filePath = self.filePath

        if filePath != "":
            if filePath != self.filePath:
                self.filePath = filePath
                self.master.tab(self, text=PurePath(self.filePath).name)
            try:
                with open(self.filePath, "wb") as f:
                    np.savez_compressed(f, **options)
            except Exception as e:
                mb.showerror(title="Failed to save file", message=e, parent=self)


class InputSpectraFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration

        rangeSelection = ttk.Frame(self)
        rangeSelection.grid(row=0, column=1, sticky="s", pady=padding)

        ttk.Label(rangeSelection, text=f"Range of {titration.xQuantity} to fit:").pack(
            side="left"
        )

        minWL = self.titration.signalTitles.min()
        maxWL = self.titration.signalTitles.max()
        decimals = self.titration.signalTitlesDecimals
        step = 1 / (10**decimals)

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

        self.fig = Figure(layout="constrained")
        self.ax = self.fig.add_subplot()

        ttk.Button(rangeSelection, text="Update", command=self.updateWLRange).pack(
            side="left"
        )

        canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=1, sticky="nw")

        toolbar = NavigationToolbarVertical(canvas, self, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ne")

        self.columnconfigure(
            0,
            weight=1000,
            uniform="column",
            minsize=max(w.winfo_reqwidth() for w in toolbar.children.values()),
        )
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1000, uniform="column")
        self.rowconfigure(
            0,
            weight=1000,
            uniform="row",
            minsize=max(w.winfo_reqheight() for w in rangeSelection.children.values()),
        )
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1000, uniform="row")
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

        fig.canvas.draw_idle()

    def updateWLRange(self):
        from_ = float(self.fromSpinbox.get())
        to = float(self.toSpinbox.get())
        self.titration.continuousRange = np.array([from_, to])
        self.plot()


class ContinuousFittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.populate()
        self.plot()

    def populate(self):
        self.fig = Figure(layout="constrained")
        self.ax = self.fig.add_subplot()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=1, sticky="nw")

        toolbar = NavigationToolbarVertical(self.canvas, self, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ne")

        self.optionsFrame = ttk.Frame(self)
        self.optionsFrame.grid(row=1, column=2, sticky="w")
        self.speciesLabel = ttk.Label(
            self.optionsFrame, anchor="center", justify="center", text="Show:"
        )
        self.speciesLabel.pack(pady=padding, fill="x")

        self.deconvolutionVar = tk.StringVar()
        deconvolutionOptions = (
            f"Molar {self.titration.yQuantity}",
            "Deconvolution at start",
            "Deconvolution at endpoint",
        )
        self.deconvolutionDropdown = ttk.OptionMenu(
            self.optionsFrame,
            self.deconvolutionVar,
            deconvolutionOptions[0],
            command=lambda *args: self.plot(),
            *deconvolutionOptions,
            style="primary.Outline.TMenubutton",
        )
        self.deconvolutionDropdown.pack()

        self.columnconfigure(
            0,
            weight=1000,
            uniform="column",
            minsize=max(w.winfo_reqwidth() for w in toolbar.children.values()),
        )
        self.columnconfigure(1, weight=1, minsize=0)
        self.columnconfigure(
            2,
            weight=1000,
            uniform="column",
            minsize=max(
                w.winfo_reqwidth() for w in self.optionsFrame.children.values()
            ),
        )
        self.rowconfigure(0, weight=1000, uniform="row")
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1000, uniform="row")
        self.grid_anchor("center")

    def plot(self):
        self.ax.clear()

        titration = self.titration
        spectra = titration.lastFittedSpectra
        names = titration.contributors.contributorNames
        wavelengths = titration.processedSignalTitles

        deconvolution = self.deconvolutionVar.get()
        if deconvolution == f"Molar {titration.yQuantity}":
            for spectrum, name in zip(spectra, names):
                self.ax.plot(wavelengths, spectrum, label=name)
            self.ax.set_ylabel(f"molar {titration.yQuantity} / {titration.yUnit} M⁻¹")
        else:
            if deconvolution == "Deconvolution at start":
                deconvolutionPoint = 0
            elif deconvolution == "Deconvolution at endpoint":
                deconvolutionPoint = -1

            self.ax.plot(
                wavelengths,
                titration.processedData[deconvolutionPoint],
                color="0.5",
                label="Observed",
            )
            self.ax.plot(
                wavelengths,
                titration.lastFittedCurves[deconvolutionPoint],
                color="0",
                linestyle="--",
                label="Fitted",
            )
            for spectrum, name in zip(
                spectra * titration.lastSignalVars[[deconvolutionPoint], :].T, names
            ):
                self.ax.plot(
                    wavelengths,
                    spectrum,
                    label=name,
                )
            self.ax.set_ylabel(f"{titration.yQuantity} / {titration.yUnit}")

        self.ax.legend()
        self.ax.set_xlabel(f"{titration.xQuantity} / {titration.xUnit}")
        self.canvas.draw()


class FittedFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.xQuantity = titration.speciation.freeNames[-1]
        self.xConcs = titration.lastTotalConcs.T[-1]
        self.normalisation = False
        self.smooth = True
        self.logScale = False

    def populate(self):
        self.fig = Figure(layout="constrained")
        self.ax = self.fig.add_subplot()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=1, sticky="nw")

        self.toolbar = NavigationToolbarVertical(self.canvas, self, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=1, column=0, sticky="ne")

        self.toggleButtonsFrame = ttk.Frame(self)
        self.toggleButtonsFrame.grid(row=1, column=2, sticky="w")
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

        separator = ttk.Separator(self.toggleButtonsFrame, orient="horizontal")
        separator.pack(pady=padding, fill="x")

        self.saveCurvesButton = ttk.Button(
            self.toggleButtonsFrame,
            text="Save fitted curves",
            command=self.saveCurves,
            style="success.Outline.TButton",
        )
        self.saveCurvesButton.pack(pady=padding, fill="x")

        self.columnconfigure(
            0,
            weight=1000,
            uniform="column",
            minsize=max(w.winfo_reqwidth() for w in self.toolbar.children.values()),
        )
        self.columnconfigure(1, weight=1, minsize=0)
        self.columnconfigure(
            2,
            weight=1000,
            uniform="column",
            minsize=max(
                w.winfo_reqwidth() for w in self.toggleButtonsFrame.children.values()
            ),
        )
        self.rowconfigure(0, weight=1000, uniform="row")
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1000, uniform="row")
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

    def saveCurves(self):
        initialfile = os.path.splitext(self.titration.title)[0] + "_fitted_curves"
        fileName = fd.asksaveasfilename(
            title="Save fitted curves",
            initialfile=initialfile,
            filetypes=[("CSV file", "*.csv")],
            defaultextension=".csv",
        )
        data = self.titration.lastFittedCurves
        rowTitles = np.atleast_2d(self.titration.additionTitles).T
        columnTitles = np.append("", self.titration.processedSignalTitles)
        output = np.vstack((columnTitles, np.hstack((rowTitles, data))))
        try:
            np.savetxt(fileName, output, fmt="%s", delimiter=",", encoding="utf-8-sig")
        except Exception as e:
            mb.showerror(title="Could not save file", message=e, parent=self)

    def plot(self):
        self.ax.clear()

        titration = self.titration

        # xQuantity and xUnit for the fitted plot. Different from the xQuantity
        # and xUnit in the titration object, which are used for the input
        # spectra.
        xQuantity = self.xQuantity
        xUnit = titration.totalConcentrations.concsUnit
        xConcs = self.xConcs / totalConcentrations.prefixes[xUnit.strip("M")]

        if self.normalisation:
            curves = self.curves.T
            fittedCurves = self.fittedCurves.T
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
            try:
                spl = make_interp_spline(
                    xConcs[filter], fittedCurve[filter], bc_type="natural"
                )
                smoothY = spl(smoothX)
                self.ax.plot(smoothX, smoothY, label=name)
            except ValueError:
                # spline interpolation failed
                self.ax.plot(xConcs, fittedCurve, label=name)
                continue

        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.ax.set_xlabel(f"[{xQuantity}] / {xUnit}")
        self.ax.legend()

        self.canvas.draw()


class DiscreteFittedFrame(FittedFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curves = self.titration.processedData.T.copy()
        self.fittedCurves = self.titration.lastFittedCurves.T.copy()
        self.names = self.titration.processedSignalTitlesStrings
        self.populate()
        self.plot()


class DiscreteFromContinuousFittedFrame(FittedFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        peakIndices = self.titration.getPeakIndices()
        self.curves = self.titration.processedData.T[peakIndices].copy()
        self.fittedCurves = self.titration.lastFittedCurves.T[peakIndices].copy()
        peakTitles = self.titration.processedSignalTitlesStrings[peakIndices]
        self.names = [f"{title} {self.titration.xUnit}" for title in peakTitles]
        self.populate()
        self.plot()


class SpeciationFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.xQuantity = titration.speciation.freeNames[-1]
        self.xConcs = titration.lastTotalConcs.T[-1]
        self.speciesVar = tk.StringVar(self)
        self.logScale = False
        self.smooth = True
        self.populate()
        self.plot()

    def populate(self):
        titration = self.titration
        self.fig = Figure(layout="constrained")
        self.ax = self.fig.add_subplot()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=1, sticky="nw")

        self.toolbar = NavigationToolbarVertical(self.canvas, self, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=1, column=0, sticky="ne")

        self.optionsFrame = ttk.Frame(self)
        self.optionsFrame.grid(row=1, column=2, sticky="w")
        self.speciesLabel = ttk.Label(
            self.optionsFrame, anchor="center", justify="center", text="Select species:"
        )
        self.speciesLabel.pack(pady=padding, fill="x")

        self.speciesDropdown = ttk.OptionMenu(
            self.optionsFrame,
            self.speciesVar,
            titration.speciation.freeNames[0],
            command=lambda *args: self.plot(),
            *titration.speciation.freeNames,
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

        self.columnconfigure(
            0,
            weight=1000,
            uniform="column",
            minsize=max(w.winfo_reqwidth() for w in self.toolbar.children.values()),
        )
        self.columnconfigure(1, weight=1, minsize=0)
        self.columnconfigure(
            2,
            weight=1000,
            uniform="column",
            minsize=max(
                w.winfo_reqwidth() for w in self.optionsFrame.children.values()
            ),
        )
        self.rowconfigure(0, weight=1000, uniform="row")
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1000, uniform="row")
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
        return np.where(self.titration.speciation.freeNames == self.speciesVar.get())[
            0
        ][0]

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
        xUnit = titration.totalConcentrations.concsUnit
        xConcs = (
            self.xConcs[additionsFilter]
            / totalConcentrations.prefixes[xUnit.strip("M")]
        )

        freeConcs = titration.lastFreeConcs[additionsFilter, :][:, self.freeIndex]
        freeName = self.speciesVar.get()

        factor = abs(titration.speciation.stoichiometries[:, self.freeIndex])
        boundFilter = factor.astype(bool)

        boundConcs = titration.lastBoundConcs * factor
        boundConcs = boundConcs[additionsFilter, :][:, boundFilter]
        # TODO: make this work with polymers
        boundNames = titration.speciation.boundNames[boundFilter]

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
            try:
                spl = make_interp_spline(
                    xConcs[filter], curve[filter], bc_type="natural"
                )
                smoothY = spl(smoothX)
                self.ax.plot(smoothX, smoothY, label=name)
            except ValueError:
                # spline interpolation failed
                self.ax.plot(xConcs, curve, label=name)
                continue

        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.ax.set_xlabel(f"[{xQuantity}] / {xUnit}")
        self.ax.legend()

        self.canvas.draw()


class ResultsFrame(ttk.Frame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.sigfigs = 3
        self.showResults()

    # TODO: add spinbox for sigfigs
    def formatK(self, k):
        return f"{float(f'{k:.{self.sigfigs}g}'):.{max(self.sigfigs, 6)}g}"

    @property
    def bic(self):
        # Bayesian Information Criterion
        numParameters = (
            self.titration.equilibriumConstants.variableCount
            + self.titration.totalConcentrations.variableCount
            + self.titration.contributors.contributorsMatrix.shape[0]
        )
        numDataPoints = self.titration.numAdditions
        chiSquared = np.sum(
            (self.titration.lastFittedCurves - self.titration.processedData) ** 2
            / np.abs(self.titration.lastFittedCurves)
        )

        return numDataPoints * np.log(
            chiSquared / numDataPoints
        ) + numParameters * np.log(numDataPoints)

    def showResults(self):
        titration = self.titration
        bicLabel = ttk.Label(
            self,
            text=f"Bayesian information criterion (lower is better): {self.bic:.3g}",
        )
        bicLabel.pack(side="top", pady=15)

        kTable = Table(
            self,
            0,
            0,
            ["K (M⁻ⁿ)"],
            rowOptions=("readonlyTitles",),
            columnOptions=("readonlyTitles",),
        )

        ks = titration.lastKVars

        for (
            name,
            value,
        ) in zip(titration.equilibriumConstants.variableNames, ks):
            kTable.addRow(name, [self.formatK(value)])
        kTable.pack(side="top", pady=15)

        if titration.totalConcentrations.variableCount > 0:
            concsTable = Table(
                self,
                0,
                0,
                [f"c ({titration.totalConcentrations.concsUnit})"],
                rowOptions=["readonlyTitles"],
                columnOptions=["readonlyTitles"],
            )
            concNames = self.titration.totalConcentrations.variableNames
            concs = titration.lastTotalConcVars
            for concName, conc in zip(concNames, concs):
                concsTable.addRow(
                    concName,
                    [
                        totalConcentrations.convertConc(
                            conc, "M", titration.totalConcentrations.concsUnit
                        )
                    ],
                )
            concsTable.pack(side="top", pady=15)

        sheet = tksheet.Sheet(
            self,
            data=list(np.around(titration.lastFittedSpectra, 2)),
            headers=list(titration.processedSignalTitlesStrings),
            row_index=list(titration.contributors.contributorNames),
            set_all_heights_and_widths=True,
        )
        sheet.enable_bindings()
        sheet.pack(side="top", pady=15, fill="x")

        saveButton = ttk.Button(
            self,
            text="Save fitted spectra to CSV",
            command=self.saveCSV,
            style="success.TButton",
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
        data = self.titration.lastFittedSpectra
        rowTitles = np.atleast_2d(self.titration.contributors.contributorNames).T
        columnTitles = np.append("", self.titration.processedSignalTitles)
        output = np.vstack((columnTitles, np.hstack((rowTitles, data))))
        try:
            np.savetxt(fileName, output, fmt="%s", delimiter=",", encoding="utf-8-sig")
        except Exception as e:
            mb.showerror(title="Could not save file", message=e, parent=self)
