import os
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import tkinter.ttk as ttk
import warnings
from copy import deepcopy
from pathlib import PurePath

import matplotlib as mpl
import matplotlib.ticker as mtick
import numpy as np
import packaging.version
import tksheet
from cycler import cycler
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from numpy import ma
from scipy.interpolate import make_interp_spline
from ttkbootstrap.widgets import InteractiveNotebook
from ttkwidgets.autohidescrollbar import AutoHideScrollbar

from . import (
    __version__,
    contributingSpecies,
    contributors,
    editData,
    equilibriumConstants,
    fitSignals,
    knownSignals,
    proportionality,
    speciation,
    totalConcentrations,
)
from .moduleFrame import GroupFrame
from .patchMatplotlib import NavigationToolbarVertical
from .scrolledFrame import ScrolledFrame
from .style import defaultFigureParams, figureParams, padding
from .table import Table, ButtonFrame
from .titration import Titration, titrationAttributes

# Magic value indicating that the data in a .fit file should be copied from the original
# titration
COPY_ORIGINAL_ARRAY = "COPY_OGIRINAL_ARRAY"

titrationModules = [
    totalConcentrations,
    proportionality,
    speciation,
    equilibriumConstants,
    contributingSpecies,
    contributors,
    knownSignals,
    fitSignals,
]


class TitrationFrame(ttk.Frame):
    def __init__(self, parent, filePath=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.filePath = filePath
        self.numFits = 0

        # options bar on the left
        scrolledFrame = ScrolledFrame(self)
        scrolledFrame.grid(column=0, row=0, sticky="nesw")
        self.options = scrolledFrame.display_widget(
            ttk.Frame, stretch=True, padding=(0, 0, padding, 0)
        )

        self.options.groupFrames = {}
        experimentFrame = self.options.groupFrames["Experimental Data"] = GroupFrame(
            self.options, "Experimental Data"
        )
        experimentFrame.grid(sticky="nesw", pady=padding)

        editDataButton = ttk.Button(
            experimentFrame,
            text="Enter/edit spectroscopic data",
            command=self.editData,
            style="Outline.TButton",
        )
        editDataButton.pack(fill="x", padx=padding)

        self.moduleFrames = {}
        for mod in titrationModules:
            moduleFrame = mod.ModuleFrame(self.options)
            self.moduleFrames[mod.__name__] = moduleFrame
            moduleFrame.pack(fill="x", padx=padding)

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

        self.notebook.bind("<Button-3>", self.renameTab, True)

        self.notebook.grid(column=1, row=0, sticky="nesw")

    def renameTab(self, event):
        if self.notebook.identify(event.x, event.y) not in ("label", "padding"):
            return

        index = self.notebook.index(f"@{event.x},{event.y}")
        if index == self.notebook._last_tab and self.notebook._has_newtab_button:
            return

        entry = ttk.Entry(self)
        entry.insert(
            0, self.notebook.tab(index, "text")[: -self.notebook._padding_spaces]
        )
        entry.place(
            x=event.x,
            y=event.y,
            anchor="nw",
            in_=self.notebook,
        )
        entry.focus_set()
        entry.grab_set()

        def onEnter(event):
            self.notebook.tab(
                index, text=entry.get() + " " * self.notebook._padding_spaces
            )
            entry.destroy()

        def onClick(event):
            if entry.identify(event.x, event.y) == "":
                entry.destroy()
                return "break"

        entry.bind("<Return>", onEnter)
        entry.bind("<Button-1>", onClick)
        entry.bind("<Escape>", lambda event: entry.destroy())

        return "break"

    def loadTitration(self, titration):
        if type(titration) is Titration:
            self.originalTitration = titration
            self.newFit()
        elif type(titration) is np.lib.npyio.NpzFile:
            # TODO: move this to titrationReader.py
            self.originalTitration = Titration()
            fileVersion = packaging.version.parse(titration[".version"].item())
            for attribute in titrationAttributes:
                try:
                    data = titration[f".original.{attribute}"]
                except KeyError:
                    continue
                else:
                    if data.shape == ():
                        data = data.item()

                try:
                    mask = titration[f".original.{attribute}.mask"]
                except KeyError:
                    pass
                else:
                    if mask.shape == ():
                        mask = mask.item()
                    data = ma.masked_array(data, mask)
                setattr(self.originalTitration, attribute, data)

            for name in titration[".fits"]:
                fit = Titration()

                for attribute in titrationAttributes:
                    try:
                        data = titration[f"{name}.{attribute}"]
                    except KeyError:
                        # Backwards compatibility:
                        # Before version 1.4.0, last free and bound concs were stored
                        # separately.
                        if (
                            fileVersion < packaging.version.parse("1.4.0")
                            and attribute == "lastSpeciesConcs"
                        ):
                            try:
                                freeConcs = titration[f"{name}.lastFreeConcs"]
                                boundConcs = titration[f"{name}.lastBoundConcs"]
                            except KeyError:
                                continue
                            data = np.hstack([freeConcs, boundConcs])
                        else:
                            continue
                    else:
                        if data.shape == ():
                            data = data.item()

                    if (
                        type(data) is type(COPY_ORIGINAL_ARRAY)
                        and data == COPY_ORIGINAL_ARRAY
                    ):
                        data = deepcopy(getattr(self.originalTitration, attribute))
                    else:
                        try:
                            mask = titration[f"{name}.{attribute}.mask"]
                        except KeyError:
                            pass
                        else:
                            if mask.shape == ():
                                mask = mask.item()
                            data = ma.masked_array(data, mask)
                    setattr(fit, attribute, data)

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
                            data = titration[key]
                        except KeyError:
                            # backwards compatibility:
                            # version 1.2.0 moved freeNames from speciation to
                            # totalConcentrations
                            if (
                                fileVersion < packaging.version.parse("1.2.0")
                                and moduleFrame.attributeName == "totalConcentrations"
                                and popupAttributeName == "freeNames"
                            ):
                                if (key := f"{name}.speciation.freeNames") in titration:
                                    # freeNames set in custom speciation
                                    data = titration[key]
                                else:
                                    # could be ["Host"] or ["Host", "Guest"]
                                    if (
                                        key := f"{name}.totalConcentrations.stockConcs"
                                    ) in titration:
                                        freeCount = titration[key].shape[0]
                                    elif (
                                        key := f"{name}.totalConcentrations.totalConcs"
                                    ) in titration:
                                        freeCount = titration[key].shape[1]
                                    else:
                                        continue
                                    data = np.array(["Host", "Guest"][:freeCount])
                            # 1.4.1 added unknown total concentrations without volumes
                            elif (
                                fileVersion < packaging.version.parse("1.4.1")
                                and moduleFrame.attributeName == "totalConcentrations"
                                and popupAttributeName == "unknownTotalConcsLinked"
                            ):
                                data = True
                            # 1.6.0 added initial guesses for unknown concentrations
                            elif (
                                fileVersion < packaging.version.parse("1.6.0")
                                and moduleFrame.attributeName == "totalConcentrations"
                                and popupAttributeName == "stockConcsGuesses"
                            ):
                                if (
                                    key := f"{name}.totalConcentrations.stockConcs"
                                ) in titration:
                                    data = ma.masked_all_like(titration[key])
                            elif (
                                fileVersion < packaging.version.parse("1.6.0")
                                and moduleFrame.attributeName == "totalConcentrations"
                                and popupAttributeName == "totalConcsGuesses"
                            ):
                                if (
                                    key := f"{name}.totalConcentrations.totalConcs"
                                ) in titration:
                                    data = ma.masked_all_like(titration[key])

                            else:
                                continue
                        else:
                            if data.shape == ():
                                data = data.item()

                        try:
                            mask = titration[f"{key}.mask"]
                        except KeyError:
                            pass
                        else:
                            if mask.shape == ():
                                mask = mask.item()
                            data = ma.masked_array(data, mask)
                        setattr(selectedStrategy, popupAttributeName, data)

                    try:
                        selectedStrategy.checkAttributes()
                    except NotImplementedError:
                        # required attribute missing
                        continue
                    setattr(fit, moduleFrame.attributeName, selectedStrategy)

                self.newFit(fit, name, setDefault=False)

            self.numFits = titration[".numFits"].item()
            titration.close()

        self.notebook.bind("<<NotebookTabChanged>>", self.switchFit, add=True)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def editData(self):
        root = self.winfo_toplevel()
        popup = editData.EditDataPopup(self.currentTab.titration, master=root)
        popup.geometry(f"+{root.winfo_x()+100}+{root.winfo_y()+100}")
        popup.show()
        self.currentTab.inputSpectraFrame.updateData()
        if (
            len(self.currentTab.tabs()) == 1
            and self.currentTab.inputSpectraFrame.loaded
        ):
            self.currentTab.select(self.currentTab.inputSpectraFrame)

    def updateDpi(self):
        for tab in self.notebook.tabs():
            if isinstance(fitNotebook := self.nametowidget(tab), FitNotebook):
                fitNotebook.updateDpi()

    @property
    def currentTab(self):
        return self.notebook.nametowidget(self.notebook.select())

    def newFit(self, titration=None, name=None, setDefault=True):
        if titration is None:
            titration = deepcopy(self.originalTitration)
        for moduleFrame in self.moduleFrames.values():
            moduleFrame.update(titration, setDefault)
        self.numFits += 1

        fitNotebook = FitNotebook(self, titration)
        if name is None:
            name = f"Fit {self.numFits}"
            titration.title = name

        self.notebook.add(fitNotebook, text=name)
        self.notebook.select(str(fitNotebook))
        fitNotebook.loadTabs()

    def copyFit(self):
        self.newFit(deepcopy(self.currentTab.titration), setDefault=False)

    def switchFit(self, event):
        fitNotebook = self.currentTab
        for moduleFrame in self.moduleFrames.values():
            moduleFrame.update(fitNotebook.titration)

    def fitData(self):
        self.currentTab.fitData()

    def saveFile(self, saveAs=False):
        options = {}
        options[".version"] = __version__
        options[".numFits"] = self.numFits

        for titrationAttribute in titrationAttributes:
            try:
                data = getattr(self.originalTitration, titrationAttribute)
            except AttributeError:
                continue

            if isinstance(data, ma.MaskedArray):
                options[f".original.{titrationAttribute}"] = data.data
                options[f".original.{titrationAttribute}.mask"] = data.mask
            else:
                options[f".original.{titrationAttribute}"] = data

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
                    data = getattr(titration, titrationAttribute)
                except AttributeError:
                    continue

                if isinstance(data, ma.MaskedArray):
                    options[f"{fit}.{titrationAttribute}"] = data.data
                    options[f"{fit}.{titrationAttribute}.mask"] = data.mask
                else:
                    options[f"{fit}.{titrationAttribute}"] = data

            for module in titrationModules:
                moduleFrame = module.ModuleFrame
                strategy = getattr(titration, moduleFrame.attributeName)
                if strategy is None:
                    continue

                options[f"{fit}.{moduleFrame.attributeName}"] = list(
                    moduleFrame.dropdownOptions.keys()
                )[
                    [x.__name__ for x in moduleFrame.dropdownOptions.values()].index(
                        type(getattr(titration, moduleFrame.attributeName)).__name__
                    )
                ]

                for popupAttributeName in strategy.popupAttributes:
                    key = f"{fit}.{moduleFrame.attributeName}.{popupAttributeName}"
                    data = getattr(strategy, popupAttributeName)

                    if isinstance(data, ma.MaskedArray):
                        options[key] = data.data
                        options[f"{key}.mask"] = data.mask
                    else:
                        options[key] = data

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
            try:
                with open(filePath, "wb") as f:
                    np.savez_compressed(f, **options)
            except Exception as e:
                mb.showerror(title="Failed to save file", message=e, parent=self)
            else:
                if filePath != self.filePath:
                    self.filePath = filePath
                    self.master.tab(self, text=PurePath(self.filePath).name)


class FitNotebook(ttk.Notebook):
    def __init__(self, master, titration, *args, **kwargs):
        super().__init__(master, padding=padding, style="Flat.TNotebook")
        self.titration = titration

    def add(self, tab, *args, hidden=False, **kwargs):
        super().add(tab, *args, **kwargs)
        if hidden:
            self.hide(tab)
        self.update()

    def loadTabs(self):
        self.inputSpectraFrame = InputSpectraFrame(self, self.titration)
        self.add(self.inputSpectraFrame, text="Input Spectra", hidden=True)
        self.inputSpectraFrame.updateData()

        if hasattr(self.titration, "fitResult"):
            try:
                self.showFit()
            except Exception as e:
                print("Warning: failed to load previous fit result:", e)

    def fitData(self):
        self.tk.eval("tk busy .")
        self.update()
        try:
            self.titration.fitData(self.fitCallback)
        except Exception as e:
            mb.showerror(title="Failed to fit data", message=e, parent=self)
            return
        finally:
            self.tk.eval("tk busy forget .")
            self.update()
        self.showFit()

    def fitCallback(self, *args):
        self.update()

    def showFit(self):
        if hasattr(self.titration, "fitResult"):
            lastTabClass = type(self.nametowidget(self.select()))
            for tab in self.tabs():
                widget = self.nametowidget(tab)
                if isinstance(widget, InputSpectraFrame):
                    continue
                self.forget(widget)
                widget.destroy()
        else:
            lastTabClass = None

        if self.titration.continuous:
            self.continuousFittedFrame = ContinuousFittedFrame(self, self.titration)
            self.add(self.continuousFittedFrame, text="Fitted Spectra")
            self.discreteFittedFrame = DiscreteFromContinuousFittedFrame(
                self, self.titration
            )
            self.add(
                self.discreteFittedFrame,
                text=f"Fit at select {self.titration.xQuantity}",
            )
        else:
            self.discreteFittedFrame = DiscreteFittedFrame(self, self.titration)
            self.add(self.discreteFittedFrame, text="Fitted signals")

        self.speciationFrame = SpeciationFrame(self, self.titration)
        self.add(self.speciationFrame, text="Speciation")

        self.resultsFrame = ResultsFrame(self, self.titration)
        self.add(self.resultsFrame, text="Results")

        if lastTabClass is not None:
            for tab in self.tabs():
                widget = self.nametowidget(tab)
                if isinstance(widget, lastTabClass):
                    self.select(str(widget))
                    break
        else:
            self.select(str(self.discreteFittedFrame))

    def updateDpi(self):
        for tab in self.tabs():
            frame = self.nametowidget(tab)
            try:
                frame.updateLegend()
            except AttributeError:
                try:
                    frame.updateDpi()
                except AttributeError:
                    pass


class PlotFrame(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.legendWidth = 0

    @property
    def dpi(self):
        return self.desiredCanvasHeight / self.figHeight

    @property
    def figWidth(self):
        return (
            self.legendWidth / self.dpi
            + defaultFigureParams["x"] * 80 / figureParams["scale"] / 100
        )

    @property
    def figHeight(self):
        return defaultFigureParams["y"] * 80 / figureParams["scale"] / 100

    @property
    def desiredCanvasWidth(self):
        return self.legendWidth + figureParams["x"]

    @property
    def desiredCanvasHeight(self):
        return figureParams["y"]

    def updateDpi(self):
        # Called when a new size in px and/or scale is set through figureParams.
        # Recalculates and sets the required figure size, canvas size, and DPI.
        self.fig.set_size_inches(self.figWidth, self.figHeight)
        mpl.rcParams["savefig.dpi"] = self.dpi

        lastCanvasWidth, lastCanvasHeight = (
            self.fig.canvas.get_tk_widget().winfo_width(),
            self.fig.canvas.get_tk_widget().winfo_height(),
        )
        self.fig.canvas.get_tk_widget().configure(
            width=self.desiredCanvasWidth, height=self.desiredCanvasHeight
        )
        currentCanvasWidth, currentCanvasHeight = (
            self.fig.canvas.get_tk_widget().winfo_width(),
            self.fig.canvas.get_tk_widget().winfo_height(),
        )
        if (
            currentCanvasWidth == lastCanvasWidth
            and currentCanvasHeight == lastCanvasHeight
        ):
            # Generate an event to clear and redraw the figure with the new DPI
            self.canvas.get_tk_widget().event_generate(
                "<Configure>",
                x=self.fig.canvas.get_tk_widget().winfo_x(),
                y=self.fig.canvas.get_tk_widget().winfo_y(),
                width=currentCanvasWidth,
                height=currentCanvasHeight,
            )
        else:
            pass


class FigureCanvasTkAggFixedRatio(FigureCanvasTkAgg):
    def recalculateDpiAndCanvasSize(self, actualCanvasWidth, actualCanvasHeight):
        # Detects if the canvas width and/or height is compressed, calculates the
        # new canvas size to preserve the aspect ratio, and sets the figure DPI to
        # preserve its scale.
        master = self.get_tk_widget().master

        if actualCanvasWidth == 1 and actualCanvasHeight == 1:
            # Canvas not initialised yet, don't change anything
            return self.figure.dpi, actualCanvasWidth, actualCanvasHeight

        elif (
            actualCanvasWidth == master.desiredCanvasWidth
            and actualCanvasHeight == master.desiredCanvasHeight
        ):
            # Canvas not compressed
            return master.dpi, actualCanvasWidth, actualCanvasHeight
        else:
            # Canvas width and/or height compressed.
            # Update width or height to preserve aspect ratio, and recalculate dpi
            desiredRatio = master.desiredCanvasHeight / master.desiredCanvasWidth
            actualRatio = actualCanvasHeight / actualCanvasWidth
            if actualRatio > desiredRatio:
                actualCanvasHeight = actualCanvasWidth * desiredRatio
                newDpi = actualCanvasHeight / master.figHeight
            else:
                actualCanvasWidth = actualCanvasHeight / desiredRatio
                newDpi = actualCanvasWidth / master.figWidth

            return newDpi, actualCanvasWidth, actualCanvasHeight

    def resize(self, event):
        print("resize called")
        # Overrides the resize event handler, which resizes the canvas based on
        # figure.dpi, event.width, and event.height.
        # If the canvas width and/or height is compressed, edits these values to
        # preserve the figure's scale and aspect ratio.
        newDpi, newWidth, newHeight = self.recalculateDpiAndCanvasSize(
            event.width, event.height
        )
        self.figure.set_dpi(newDpi)
        event.width, event.height = newWidth, newHeight

        super().resize(event)


class InputSpectraFrame(PlotFrame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.populate()

        self.loaded = False

    def updateData(self):
        if self.titration.continuous:
            if not self.loaded:
                self.master.add(self, text="Input Spectra")
                self.loaded = True
            self.updateRangeSelection()
            self.plot()
        else:
            self.loaded = False
            self.master.hide(self)

    def populate(self):
        rangeSelection = ttk.Frame(self)
        rangeSelection.grid(row=0, column=1, sticky="s")

        self.rangeLabel = ttk.Label(rangeSelection)
        self.rangeLabel.pack(side="left")

        self.fromSpinbox = ttk.Spinbox(rangeSelection, width=5)
        self.fromSpinbox.pack(padx=padding, side="left")

        ttk.Label(rangeSelection, text="to").pack(side="left")

        self.toSpinbox = ttk.Spinbox(rangeSelection, width=5)
        self.toSpinbox.pack(padx=padding, side="left")

        self.fig = Figure(
            layout="constrained", figsize=(self.figWidth, self.figHeight), dpi=self.dpi
        )
        self.ax = self.fig.add_subplot()

        ttk.Button(rangeSelection, text="Update", command=self.updateWLRange).pack(
            side="left"
        )

        canvas = FigureCanvasTkAggFixedRatio(self.fig, master=self)
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

    def updateRangeSelection(self):
        self.rangeLabel.configure(text=f"Range of {self.titration.xQuantity} to fit:")

        signalMin = self.titration.signalTitles.min()
        signalMax = self.titration.signalTitles.max()

        currentMin, currentMax = self.titration.continuousRange
        currentMin = max(currentMin, signalMin)
        currentMax = min(currentMax, signalMax)

        decimals = self.titration.signalTitlesDecimals
        step = 1 / (10**decimals)

        self.fromSpinbox.configure(from_=signalMin, to=signalMax, increment=step)
        self.fromSpinbox.set(f"{currentMin:.{decimals}f}")
        self.toSpinbox.configure(from_=signalMin, to=signalMax, increment=step)
        self.toSpinbox.set(f"{currentMax:.{decimals}f}")

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


class ContinuousFittedFrame(PlotFrame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.showLegend = True
        self.populate()
        self.plot()

    def populate(self):
        self.fig = Figure(
            layout="constrained", figsize=(self.figWidth, self.figHeight), dpi=self.dpi
        )
        self.ax = self.fig.add_subplot()
        self.canvas = FigureCanvasTkAggFixedRatio(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=1, sticky="nw")

        toolbar = NavigationToolbarVertical(self.canvas, self, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=1, column=0, sticky="ne")

        self.optionsFrame = ttk.Frame(self)
        self.optionsFrame.grid(row=1, column=2, sticky="w")
        self.deconvolutionLabel = ttk.Label(
            self.optionsFrame, anchor="center", justify="center", text="Plot type:"
        )
        self.deconvolutionLabel.pack(pady=0, fill="x")

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
            *deconvolutionOptions,
            command=lambda *args: self.plot(),
            style="primary.Outline.TMenubutton",
        )
        self.deconvolutionDropdown.pack(pady=padding, fill="x")

        self.legendButton = ttk.Checkbutton(
            self.optionsFrame,
            text="Show legend",
            command=self.toggleLegend,
            style="Outline.Toolbutton",
        )
        self.legendButton.state(("selected",))
        self.legendButton.pack(pady=padding, fill="x")

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

    def toggleLegend(self):
        self.showLegend = not self.showLegend
        self.ax.get_legend().set_visible(self.showLegend)
        self.canvas.draw()

    def plot(self):
        self.ax.clear()

        titration = self.titration
        spectra = titration.lastFittedSpectra
        names = titration.contributors.outputNames
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
            else:
                raise ValueError(f"Unknown deconvolution option {deconvolution}")

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

        self.ax.legend(draggable=True).set_visible(self.showLegend)
        self.ax.set_xlabel(f"{titration.xQuantity} / {titration.xUnit}")
        self.canvas.draw()


class FittedFrame(PlotFrame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.xQuantity = titration.totalConcentrations.freeNames[-1]
        self.xConcs = titration.lastTotalConcs.T[-1]
        self.smooth = True
        self.showLegend = True
        self.logScale = False

    def populate(self):
        self.fig = Figure(
            layout="constrained", figsize=(self.figWidth, self.figHeight), dpi=self.dpi
        )
        self.ax = self.fig.add_subplot()

        self.canvas = FigureCanvasTkAggFixedRatio(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=1, sticky="nw")

        self.toolbar = NavigationToolbarVertical(self.canvas, self, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=1, column=0, sticky="ne")

        self.toggleButtonsFrame = ttk.Frame(self)
        self.toggleButtonsFrame.grid(row=1, column=2, sticky="w")

        self.plotTypeVar = tk.StringVar()
        self.plotTypes = {
            f"Absolute {self.titration.yQuantity}": "absolute",
            f"Change in {self.titration.yQuantity}": "relative",
            f"Normalised change in {self.titration.yQuantity}": "normalised",
        }
        self.plotTypeDropdown = ttk.OptionMenu(
            self.toggleButtonsFrame,
            self.plotTypeVar,
            [k for (k, v) in self.plotTypes.items() if v == "relative"][0],
            *self.plotTypes.keys(),
            command=lambda *args: self.plot(),
            style="primary.Outline.TMenubutton",
        )
        self.plotTypeDropdown.pack(pady=padding, fill="x")

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

        self.legendButton = ttk.Checkbutton(
            self.toggleButtonsFrame,
            text="Show legend",
            command=self.toggleLegend,
            style="Outline.Toolbutton",
        )
        self.legendButton.state(("selected",))
        self.legendButton.pack(pady=padding, fill="x")

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

    @property
    def plotType(self):
        return self.plotTypes[self.plotTypeVar.get()]

    def toggleLogScale(self):
        self.logScale = not self.logScale
        if self.logScale:
            self.ax.set_xscale("log")
        else:
            self.ax.set_xscale("linear")
        self.canvas.draw()

    def toggleLegend(self):
        self.showLegend = not self.showLegend
        self.ax.get_legend().set_visible(self.showLegend)
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

        if ma.is_masked(self.curves):
            firstUnmaskedIndices = [np.where(~row)[0][0] for row in self.curves.mask]
        else:
            firstUnmaskedIndices = [0] * self.curves.shape[0]
        firstUnmaskedElements = np.array(
            [curve[i] for curve, i in zip(self.curves, firstUnmaskedIndices)]
        )

        # fitted Curves should always be masked
        firstUnmaskedFittedIndices = [
            np.where(~row)[0][0] for row in self.fittedCurves.mask
        ]
        firstUnmaskedFittedElements = np.array(
            [
                fittedCurve[i]
                for fittedCurve, i in zip(self.fittedCurves, firstUnmaskedFittedIndices)
            ]
        )

        if self.plotType == "absolute":
            curves = self.curves
            fittedCurves = self.fittedCurves
            self.ax.set_ylabel(f"{titration.yQuantity} / {titration.yUnit}")
        elif self.plotType == "relative":
            fittedZeros = np.atleast_2d(firstUnmaskedFittedElements).T
            curves = self.curves - fittedZeros
            fittedCurves = self.fittedCurves - fittedZeros
            self.ax.set_ylabel(f"Δ{titration.yQuantity} / {titration.yUnit}")
        elif self.plotType == "normalised":
            curves = self.curves.T
            fittedCurves = self.fittedCurves.T
            # normalise so that all the fitted curves have the same amplitude
            fittedDiff = self.fittedCurves.T - firstUnmaskedFittedElements
            maxFittedDiff = np.max(abs(fittedDiff), axis=0)
            curves = curves / maxFittedDiff

            diff = curves - np.array(
                [curve[i] for curve, i in zip(curves.T, firstUnmaskedIndices)]
            )
            negatives = abs(np.amin(diff, axis=0)) > abs(np.amax(diff, axis=0))
            curves[:, negatives] *= -1
            curves = curves.T * 100

            fittedCurves = fittedCurves / maxFittedDiff
            fittedCurves[:, negatives] *= -1
            fittedCurves = fittedCurves.T * 100

            fittedZeros = np.atleast_2d(
                [
                    fittedCurve[i]
                    for fittedCurve, i in zip(fittedCurves, firstUnmaskedIndices)
                ]
            ).T
            curves = curves - fittedZeros
            fittedCurves = fittedCurves - fittedZeros
            self.ax.set_ylabel(f"Normalised Δ{titration.yQuantity} / %")
        else:
            raise ValueError(f"Unknown plot type: {self.plotType}")

        for curve, fittedCurve, name in zip(curves, fittedCurves, self.names):
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
        self.ax.legend(draggable=True).set_visible(self.showLegend)

        self.canvas.draw()


class DiscreteFittedFrame(FittedFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curves = self.titration.processedData.T.copy()
        self.fittedCurves = self.titration.lastFittedCurves.T.copy()
        self.names = self.titration.processedSignalTitlesStrings
        self.populate()
        self.plot()


class ChoosePeakIndicesPopup(tk.Toplevel):
    def __init__(self, master, titration, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.withdraw()

        self.titration = titration
        self.saved = False
        self.modified = False
        self.resetToDefaults = False
        self.peakIndices = None

    def show(self):
        self.geometry(f"+{self.master.winfo_x()+100}+{self.master.winfo_y()+100}")
        self.populate()

        self.deiconify()
        self.grab_set()
        self.transient(self.master)
        self.wait_window()
        return (
            self.saved and self.modified,
            None if self.resetToDefaults else self.peakIndices,
        )

    def populate(self):
        self.title(f"Select {self.titration.xQuantity} to display")
        self.signalsTreeview = ttk.Treeview(self, selectmode="extended")
        self.signalsTreeview.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.signalsTreeview.heading(
            "#0",
            text=(
                f"Available signals ({self.titration.xQuantity} / "
                f"{self.titration.xUnit})"
            ),
        )

        signalsScrollbar = AutoHideScrollbar(self, orient="vertical")
        signalsScrollbar.grid(row=0, column=1, rowspan=2, sticky="ns")
        self.signalsTreeview.configure(yscrollcommand=signalsScrollbar.set)
        signalsScrollbar.configure(command=self.signalsTreeview.yview)

        rightButton = ttk.Button(self, text="▶", command=self.moveRight)
        rightButton.grid(row=0, column=2, sticky="s", padx=5 * padding, pady=padding)
        leftButton = ttk.Button(self, text="◀", command=self.moveLeft)
        leftButton.grid(row=1, column=2, sticky="n", padx=5 * padding, pady=padding)

        self.selectedTreeview = ttk.Treeview(self, selectmode="extended")
        self.selectedTreeview.grid(row=0, column=3, rowspan=2, sticky="nsew")
        self.selectedTreeview.heading("#0", text="Selected signals")

        selectedScrollbar = AutoHideScrollbar(self, orient="vertical")
        selectedScrollbar.grid(row=0, column=4, rowspan=2, sticky="ns")
        self.selectedTreeview.configure(yscrollcommand=selectedScrollbar.set)
        selectedScrollbar.configure(command=self.selectedTreeview.yview)

        buttonFrame = ButtonFrame(self, self.reset, self.save, self.destroy)
        buttonFrame.resetButton.configure(text="Reset to default")
        buttonFrame.grid(row=2, column=0, columnspan=5, sticky="esw")

        self.fillTreeviews()

    def save(self):
        if len(self.selectedTreeview.get_children()) == 0:
            raise RuntimeError("Please select at least one signal.")
        self.saved = True
        self.peakIndices = [
            self.signalIds.index(selectedId)
            for selectedId in self.selectedTreeview.get_children()
        ]
        self.destroy()

    def reset(self):
        self.clearTreeviews()
        self.fillTreeviews(self.titration.getDefaultPeakIndices())
        self.resetToDefaults = True
        self.modified = True

    def clearTreeviews(self):
        self.signalsTreeview.delete(*self.signalIds)
        self.selectedTreeview.delete(*self.selectedIds)

    def fillTreeviews(self, peakIndices=None):
        if peakIndices is None:
            peakIndices = self.titration.peakIndices
        self.signalIds, self.selectedIds = [], []

        for i, signal in enumerate(self.titration.processedSignalTitlesStrings):
            self.signalIds.append(
                signalId := self.signalsTreeview.insert("", "end", text=signal)
            )
            self.selectedIds.append(
                selectedId := self.selectedTreeview.insert("", "end", text=signal)
            )

            if i in peakIndices:
                self.signalsTreeview.detach(signalId)
            else:
                self.selectedTreeview.detach(selectedId)

    def moveRight(self):
        if len(self.signalsTreeview.selection()) == 0:
            return

        self.selectedTreeview.selection_set("")

        for signalId in self.signalsTreeview.selection():
            self.signalsTreeview.detach(signalId)

            index = self.signalIds.index(signalId)
            selectedId = self.selectedIds[index]

            for existingId in self.selectedTreeview.get_children()[::-1]:
                if self.selectedIds.index(existingId) < index:
                    self.selectedTreeview.move(
                        selectedId, "", self.selectedTreeview.index(existingId) + 1
                    )
                    break
            else:
                self.selectedTreeview.move(selectedId, "", 0)

            self.selectedTreeview.selection_add(selectedId)
            self.selectedTreeview.see(selectedId)

        self.signalsTreeview.selection_set("")
        self.resetToDefaults = False
        self.modified = True

    def moveLeft(self):
        if len(self.selectedTreeview.selection()) == 0:
            return

        self.signalsTreeview.selection_set("")

        for signalId in self.selectedTreeview.selection():
            self.selectedTreeview.detach(signalId)

            index = self.selectedIds.index(signalId)
            signalId = self.signalIds[index]

            for existingId in self.signalsTreeview.get_children()[::-1]:
                if self.signalIds.index(existingId) < index:
                    self.signalsTreeview.move(
                        signalId, "", self.signalsTreeview.index(existingId) + 1
                    )
                    break
            else:
                self.signalsTreeview.move(signalId, "", 0)

            self.signalsTreeview.selection_add(signalId)
            self.signalsTreeview.see(signalId)

        self.selectedTreeview.selection_set("")
        self.resetToDefaults = False
        self.modified = True


class DiscreteFromContinuousFittedFrame(FittedFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCurves()
        self.populate()
        self.plot()

    def setCurves(self):
        peakIndices = self.titration.peakIndices
        self.curves = self.titration.processedData.T[peakIndices].copy()
        self.fittedCurves = self.titration.lastFittedCurves.T[peakIndices].copy()
        peakTitles = self.titration.processedSignalTitlesStrings[peakIndices]
        self.names = [f"{title} {self.titration.xUnit}" for title in peakTitles]

    def populate(self):
        super().populate()

        self.choosePeakIndicesButton = ttk.Button(
            self.toggleButtonsFrame,
            text=f"Select {self.titration.xQuantity} to display",
            command=self.choosePeakIndices,
            style="Outline.TButton",
        )
        self.choosePeakIndicesButton.pack(
            before=self.saveCurvesButton, pady=padding, fill="x"
        )

        separator = ttk.Separator(self.toggleButtonsFrame, orient="horizontal")
        separator.pack(before=self.saveCurvesButton, pady=padding, fill="x")

    def choosePeakIndices(self):
        popup = ChoosePeakIndicesPopup(self, self.titration)
        saved, peakIndices = popup.show()
        if not saved:
            return
        self.titration.peakIndices = peakIndices
        self.setCurves()
        self.plot()


class SpeciationFrame(PlotFrame):
    def __init__(self, parent, titration, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.titration = titration
        self.xQuantity = titration.totalConcentrations.freeNames[-1]
        self.xConcs = titration.lastTotalConcs.T[-1]
        self.speciesVar = tk.StringVar(self)
        self.legendVar = tk.StringVar(self)
        self.separatePolymers = False
        self.logScale = False
        self.smooth = True
        self.showLegend = True
        self.populate()
        self.plot()

    def populate(self):
        titration = self.titration
        self.fig = Figure(
            layout="constrained", figsize=(self.figWidth, self.figHeight), dpi=self.dpi
        )
        self.ax = self.fig.add_subplot()

        self.canvas = FigureCanvasTkAggFixedRatio(self.fig, master=self)
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
        self.speciesLabel.pack(pady=0, fill="x")

        self.speciesDropdown = ttk.OptionMenu(
            self.optionsFrame,
            self.speciesVar,
            titration.totalConcentrations.freeNames[0],
            command=lambda *args: self.plot(),
            *titration.totalConcentrations.freeNames,
            style="primary.Outline.TMenubutton",
        )
        self.speciesDropdown.pack(pady=padding, fill="x")

        self.legendLabel = ttk.Label(
            self.optionsFrame, anchor="center", justify="center", text="Show legend?"
        )
        self.legendLabel.pack(pady=0, fill="x")

        legendOptions = ["Inside plot", "Outside plot", "No"]
        self.legendDropdown = ttk.OptionMenu(
            self.optionsFrame,
            self.legendVar,
            legendOptions[1],
            command=lambda *args: self.updateLegend(),
            *legendOptions,
            style="primary.Outline.TMenubutton",
        )
        self.legendDropdown.pack(pady=padding, fill="x")

        self.separatePolymersButton = ttk.Checkbutton(
            self.optionsFrame,
            text="Separate terminal &\ninternal polymers",
            command=self.toggleSeparatePolymers,
            style="Outline.Toolbutton",
        )
        if titration.speciation.polymerCount == 0:
            self.separatePolymersButton.state(["disabled"])
        self.separatePolymersButton.pack(pady=padding, fill="x")

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

        self.legendButton = ttk.Checkbutton(
            self.optionsFrame,
            text="Show legend",
            command=self.toggleLegend,
            style="Outline.Toolbutton",
        )
        self.legendButton.state(("selected",))
        self.legendButton.pack(pady=padding, fill="x")

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

    def toggleSeparatePolymers(self):
        self.separatePolymers = not self.separatePolymers
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

    def toggleLegend(self):
        self.showLegend = not self.showLegend
        self.ax.get_legend().set_visible(self.showLegend)
        self.canvas.draw()

    def updateLegend(self):
        legendPosition = self.legendVar.get()
        lastLegendWidth = self.legendWidth

        if legendPosition == "Inside plot":
            self.legendWidth = 0
            self.legend.set_visible(True)
            self.legend.set_draggable(True)
            self.legend.set_bbox_to_anchor(None)
            self.legend.set_loc("best")
        elif legendPosition == "Outside plot":
            self.legendWidth = 0  # self.figWidth uses self.legendWidth
            self.legend.set_visible(False)
            self.fig.set_size_inches([self.figWidth, self.figHeight])
            self.fig.set_dpi(self.dpi)
            self.canvas.draw()
            widthBeforeLegend, _ = self.ax.bbox.size

            self.legend.set_visible(True)
            self.legend.set_draggable(False)
            self.legend.set_bbox_to_anchor([1, 1])
            self.legend.set_loc("upper left")
            self.canvas.draw()
            widthAfterLegend, _ = self.ax.bbox.size

            self.legendWidth = widthBeforeLegend - widthAfterLegend
        else:
            self.legendWidth = 0
            self.legend.set_visible(False)

        if lastLegendWidth != self.legendWidth:
            self.updateDpi()
        else:
            self.canvas.draw()

        # TODO: add to all frames, change to updateLegendAndDpi() so that it just calls
        # updateDpi() if self.legend does not exist.

    @property
    def freeIndex(self):
        return np.where(
            self.titration.totalConcentrations.freeNames == self.speciesVar.get()
        )[0][0]

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

        freeName = self.speciesVar.get()

        factor = abs(titration.speciation.outputStoichiometries[:, self.freeIndex])
        mask = factor.astype(bool)

        concs = titration.lastSpeciesConcs * factor
        concs = concs[additionsFilter, :][:, mask]
        names = titration.speciation.outputNames[mask]

        curves = 100 * concs.T / totalConcs
        self.ax.set_ylabel(f"% of {freeName}")
        self.ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100))
        self.ax.set_ylim(bottom=-5, top=105)

        if not self.separatePolymers:
            # Find the indices of terminal species which are followed by matching
            # internal species. Prepend [False] to instead get the list of the terminal
            # species, and make the list length match the array. Invert to get all
            # all indices we want to preserve.
            keepIndices = np.invert(
                [False]
                + [
                    first.endswith(" terminal")
                    and second.endswith(" internal")
                    and first.removesuffix(" terminal")
                    == second.removesuffix(" internal")
                    for first, second in zip(names[:-1], names[1:])
                ]
            )
            # Merge the names: keep only the terminal ones, and remove " terminal".
            names = [name.removesuffix(" terminal") for name in names[keepIndices]]
            # Merge the curves: add the concs of the internal elements to the terminal.
            curves = np.add.reduceat(curves, np.where(keepIndices)[0], axis=0)

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

        self.legend = self.ax.legend()
        self.updateLegend()


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
    def RMSE(self):
        return np.sqrt(
            np.mean(
                (self.titration.lastFittedCurves - self.titration.processedData) ** 2
            )
        )

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
        # bicLabel.pack(side="top", pady=15)

        rmselabel = ttk.Label(
            self,
            text=f"RMSE: {self.RMSE:.8g}",
        )
        rmselabel.pack(side="top", pady=15)

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

        # TODO: fix sheet becoming too small to be visible when there are a lot of
        # variables shown above it.

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

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sheet = tksheet.Sheet(
                self,
                empty_vertical=0,
                empty_horizontal=0,
                data=list(np.around(titration.lastFittedSpectra, 2)),
                headers=list(titration.processedSignalTitlesStrings),
                row_index=list(titration.contributors.outputNames),
                set_all_heights_and_widths=True,
            )
        sheet.MT.configure(height=0)
        sheet.RI.configure(height=0)

        sheet.enable_bindings()
        sheet.set_width_of_index_to_text()
        sheet.pack(side="top", pady=15, fill="both", expand=True)

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
        rowTitles = np.atleast_2d(self.titration.contributors.outputNames).T
        columnTitles = np.append("", self.titration.processedSignalTitlesStrings)
        output = np.vstack((columnTitles, np.hstack((rowTitles, data))))
        try:
            np.savetxt(fileName, output, fmt="%s", delimiter=",", encoding="utf-8-sig")
        except Exception as e:
            mb.showerror(title="Could not save file", message=e, parent=self)
