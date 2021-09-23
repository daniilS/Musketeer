import tkinter as tk
import tkinter.ttk as ttk

import numpy as np

from .style import padding, cellWidth


class Table(ttk.Frame):
    width = cellWidth

    # TODO: add ability to add columns, and link rows to data

    def __init__(self, master, headerRows, dataColumns, *,
                 readonlyTitles=False, allowBlanks=False, **kwargs):
        self.headerRows = headerRows
        self.dataColumns = dataColumns
        self.readonlyTitles = readonlyTitles
        self.allowBlanks = allowBlanks
        super().__init__(master, padding=padding, **kwargs)

        self.addRowButton = self.button(
            self.headerRows - 1, 0, "New row", self.addRow
        )

        self.initEmptyCells()

    def initEmptyCells(self):
        self.cells = np.empty((0, 2 + self.dataColumns))

    def entry(self, row, column, text="", align="left", columnspan=1,
              **kwargs):
        entry = ttk.Entry(
            self, width=self.width * columnspan, justify=align, **kwargs
        )

        def set(text=""):
            oldState = self.state()
            self.state(["!disabled"])
            entry.delete(0, "end")
            entry.insert(0, text)
            self.state(oldState)
        entry.set = set

        entry.set(text)
        entry.grid(
            row=row, column=column, sticky="nesw", columnspan=columnspan,
        )
        return entry

    def readonlyEntry(self, *args, **kwargs):
        entry = self.entry(*args, **kwargs)
        entry.state(["readonly"])
        entry.configure(takefocus=False)
        return entry

    def label(self, row, column, text="", columnspan=1, **kwargs):
        frame = ttk.Frame(self, width=self.width * columnspan, borderwidth=5)
        frame.grid(
            row=row, column=column, sticky="nesw", columnspan=columnspan
        )
        label = ttk.Label(frame, text=text, **kwargs)
        label.pack()
        return frame

    def button(self, row, column, text="", command=None, columnspan=1,
               **kwargs):
        button = ttk.Button(
            self, text=text, command=command, style="Outline.TButton",
            takefocus=False, **kwargs
        )
        button.grid(
            row=row, column=column, sticky="nesw", columnspan=columnspan,
            padx=1, pady=1
        )
        return button

    def dropdown(self, row, column, choices=[], default=None, columnspan=1):
        stringVar = tk.StringVar()
        if default is None:
            default = choices[0]
        optionMenu = ttk.OptionMenu(
            self, stringVar, default, *choices,
            style="Outline.TMenubutton"
        )
        optionMenu.configure(takefocus=0)
        optionMenu.grid(row=row, column=column, sticky="nesw", padx=1, pady=1)
        return optionMenu, stringVar

    def addRow(self, firstEntry="", data=None):
        row = self.cells.shape[0]
        gridRow = row + self.headerRows
        newRow = []
        newRow.append(
            self.button(
                gridRow, 0, "Delete", lambda row=row: self.deleteRow(row)
            )
        )
        if self.readonlyTitles:
            entry = self.readonlyEntry(gridRow, 1, firstEntry)
        else:
            entry = self.entry(gridRow, 1, firstEntry)
        newRow.append(entry)
        for column in range(self.dataColumns):
            entry = self.entry(gridRow, 2 + column, align="right")
            if data is not None:
                entry.set(data[column])
            newRow.append(entry)

        self.cells = np.vstack((self.cells, newRow))

    def deleteRow(self, row):
        for element in self.cells[row]:
            element.destroy()
        self.cells[row] = np.full(self.cells.shape[1], None)

    def resetData(self):
        for row in self.cells:
            for element in row:
                if element is not None:
                    element.destroy()
        self.initEmptyCells()

    def float(self, number):
        if self.allowBlanks and number == "":
            return np.nan
        return float(number)

    @property
    def data(self):
        data = np.empty((0, self.dataColumns))
        for row in self.cells:
            if row[0] is None:
                continue
            rowData = [self.float(cell.get()) for cell in row[2:]]
            data = np.vstack([data, rowData])
        return data

    @data.setter
    def data(self, data):
        for widget in np.nditer(self.cells):
            widget.destroy()

        self.dataColumns = data.shape[1]
        self.initEmptyCells()
        for row in data:
            self.addRow("", row)

    @property
    def fullData(self):
        data = np.empty((0, 1 + self.dataColumns))
        for row in self.cells:
            if row[0] is None:
                continue
            rowData = [self.float(cell.get()) for cell in row[2:]]
            rowData.insert(0, row[1].get())
            data = np.vstack([data, rowData])
        return data

    @fullData.setter
    def fullData(self, fullData):
        for widget in np.nditer(self.cells):
            widget.destroy()

        self.dataColumns = fullData.shape[1] - 1
        self.initEmptyCells()
        for row in fullData:
            self.addRow(row[0], row[1:])

    @property
    def rowTitles(self):
        return np.array(
            [title.get() for title in self.cells[:, 1] if title is not None]
        )

    @rowTitles.setter
    def rowTitle(self, titles):
        titleCells = self.cells[:, 1]
        titleCells = titleCells[titleCells != None]
        for cell, title in zip(titleCells, titles):
            cell.set(title)
