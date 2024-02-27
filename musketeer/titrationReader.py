import csv
import tkinter as tk
import tkinter.ttk as ttk

import matplotlib as mpl
import numpy as np
from matplotlib.backend_bases import _Mode
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from numpy import ma

from .style import padding


def fillPredefinedParams(titration, params):
    for k, v in params._asdict().items():
        setattr(titration, k, v)


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]


# TODO: convert to classes, register using ABC
def readUV(filePath, master):
    with open(filePath, "r", newline="", encoding="utf-8-sig") as inFile:
        reader = csv.reader(inFile)

        titleRow = next(reader)[::2]
        # the title row can contain an extra blank entry, this gets rid of it
        if not titleRow[-1]:
            titleRow.pop(-1)

        wavelengths = []
        absorbances = []
        # skip the column name row
        next(reader)
        for row in reader:
            if not row or not row[0]:
                break
            wavelengths.append(row[0])
            absorbances.append(row[1::2])

    additionTitles = np.array(titleRow)
    signalTitles = np.array(wavelengths)

    # transpose data so that the column is the wavelength
    data = np.array(absorbances, dtype=float).T

    return data, additionTitles, signalTitles, "UV-Vis"


def readGeneric(filePath, master):
    with open(filePath, encoding="utf-8-sig") as file:
        d = csv.Sniffer().sniff(file.readline() + file.readline())
        file.seek(0)
        data = np.array(list(csv.reader(file, dialect=d)))

    return data, None, None, None


class NavigationToolbarHorizontal(NavigationToolbar2Tk):
    def __init__(self, pickPeak, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pickPeak = pickPeak
        self.callback = callback

    def _update_view(self):
        super()._update_view()
        self.callback()

    def press_pan(self, event):
        event.key = "x"
        return super().press_pan(event)

    def drag_pan(self, event):
        event.key = "x"
        return super().drag_pan(event)

    def release_pan(self, event):
        event.key = "x"
        super().release_pan(event)
        self.callback()

    def press_zoom(self, event):
        event.key = "x"
        return super().press_zoom(event)

    def drag_zoom(self, event):
        event.key = "x"
        return super().drag_zoom(event)

    def release_zoom(self, event):
        # check if user clicked without dragging
        shouldPickPeak = not hasattr(self, "lastrect")
        event.key = "x"
        super().release_zoom(event)
        if shouldPickPeak:
            event.zoomClick = True
            self.pickPeak(event)
        self.callback()

    def draw_rubberband(self, event, x0, y0, x1, y1):
        axes = self.canvas.figure.get_axes()
        y0 = axes[-1].bbox.intervaly[0]
        y1 = axes[0].bbox.intervaly[1]
        return super().draw_rubberband(event, x0, y0, x1, y1)


def readNMR(filePath, master):
    # reads an MNova 1D peaks list
    additionTitles = []
    frequencies = []
    intensities = []
    plotFrequencies = []
    plotIntensities = []

    with open(filePath, "r", newline="", encoding="utf-8-sig") as inFile:
        reader = csv.reader(inFile, delimiter="\t")
        for row in reader:
            if not row or not row[0]:
                break
            additionTitles.append(row[1])
            currentFrequencies = [float(f) for f in row[2::2]]
            currentIntensities = [float(i) for i in row[3::2]]
            numSignals = len(currentFrequencies)
            # TODO: check that file is valid

            frequencies.append(currentFrequencies)
            intensities.append(currentIntensities)
            currentPlotFrequencies = [0]
            currentPlotFrequencies.extend(
                # append each frequency three times to create peak
                f
                for f in currentFrequencies
                for _ in range(3)
            )
            currentPlotFrequencies.append(0)
            plotFrequencies.append(currentPlotFrequencies)

            currentPlotIntensities = [0] * (numSignals * 3 + 2)
            # link the intensity to the middle of the three times it's present
            currentPlotIntensities[2::3] = currentIntensities
            plotIntensities.append(currentPlotIntensities)

        maxF = max(max(f) for f in frequencies)
        minF = min(min(f) for f in frequencies)

        numRows = len(frequencies)
        fig = Figure()
        axList = fig.subplots(
            numRows, 1, sharex=True, sharey=True, gridspec_kw={"hspace": 0, "wspace": 0}
        )
        axList = np.flip(axList)
        axList[0].invert_xaxis()
        for ax, x, y in zip(axList, plotFrequencies, plotIntensities):
            x[0] = maxF + (0.1 * (maxF - minF))
            x[-1] = minF - (0.1 * (maxF - minF))
            ax.plot(x, y, color="black")
            ax.axes.yaxis.set_visible(False)
            ax.set_xlim(x[0], x[-1])
        fig.tight_layout()

        signals = []
        titles = []
        currentSignal = np.full(numRows, None)
        plottedPoints = np.copy(currentSignal)
        cycler = mpl.rcParams["axes.prop_cycle"].by_key()["color"]

        data = None
        additionTitles = np.array(additionTitles)
        signalTitles = None

        popup = tk.Toplevel()
        popup.title("Pick signals")
        popup.transient(master)
        popup.geometry(f"+{master.winfo_x()+100}+{master.winfo_y()+100}")
        popup.grab_set()

        frame = ttk.Frame(popup)
        frame.pack()

        entry = ttk.Entry(frame)
        entry.insert(0, "Signal title")

        flatI = np.concatenate(intensities)
        flatF = np.concatenate(frequencies)

        def rescale():
            maxF, minF = axList[0].get_xlim()
            filteredI = flatI[(minF <= flatF) & (flatF <= maxF)]
            if len(filteredI) > 0:
                ax.set_ylim(0, 1.2 * np.max(filteredI))

        rescale()

        def onClick(e):
            # click outside of plot area
            if e.inaxes is None:
                return
            # zoom/pan click
            if toolbar.mode != _Mode.NONE and not hasattr(e, "zoomClick"):
                return
            i = np.where(axList == e.inaxes)[0][0]

            if e.button == 3:
                # left click
                if plottedPoints[i] is None:
                    return
                plottedPoints[i].remove()
                currentSignal[i] = None
                plottedPoints[i] = None
                canvas.draw()
                canvas.flush_events()
                return

            x = find_nearest(frequencies[i], e.xdata)
            y = intensities[i][frequencies[i].index(x)]
            currentSignal[i] = x
            if plottedPoints[i] is not None:
                # remove previous point
                plottedPoints[i].remove()
                pass

            plottedPoints[i] = e.inaxes.plot(x, y, "o", color=cycler[0])[0]
            canvas.draw()
            canvas.flush_events()

        def next():
            signals.append(np.copy(currentSignal))
            titles.append(entry.get())

            currentSignal.fill(None)
            plottedPoints.fill(None)

            entry.delete(0, "end")
            entry.insert(0, "Signal title")
            cycler.pop(0)

        def save():
            nonlocal data, signalTitles
            data = ma.masked_invalid(np.array(signals, dtype=float).T)
            signalTitles = np.array(titles)
            popup.destroy()

        btn1 = ttk.Button(frame, text="Save signal", command=next)
        btn2 = ttk.Button(frame, text="Submit", style="success.TButton", command=save)
        for widget in (entry, btn1, btn2):
            widget.pack(side="left", padx=2, pady=5)

        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.draw()
        canvas.mpl_connect("button_press_event", onClick)
        canvas.get_tk_widget().pack(side="bottom", fill="both", expand=True)

        toolbar = NavigationToolbarHorizontal(
            onClick, rescale, canvas, popup, pack_toolbar=False
        )
        toolbar.update()
        toolbar.pack(side="left", padx=padding)

        for ax in axList:
            # prevent zoom reset when adding points
            ax.autoscale(False)

        popup.wait_window(popup)

        return data, additionTitles, signalTitles, "NMR"


fileReaders = np.array(
    [
        ["Generic csv file", "*.csv", readGeneric],
        ["Cary UV-Vis csv file", "*.csv", readUV],
        ["Mnova NMR peak list", "*.csv", readNMR],
    ]
)
