import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as mb
from tkinter import font

import numpy as np

from .style import padding, cellWidth


class Table(ttk.Frame):
    width = cellWidth

    titleFont = None
    fitToText = "New column"

    def __init__(
        self,
        master,
        headerGridRows,
        headerCells,
        columnTitles=[],
        *,
        allowBlanks=False,
        rowOptions=[],
        columnOptions=[],
        boldTitles=False,
        callback="",
        **kwargs,
    ):
        self.rowOptions = rowOptions
        self.columnOptions = columnOptions
        self.allowBlanks = allowBlanks
        super().__init__(master, padding=padding, **kwargs)
        if callback != "":
            callback = self.register(callback)
        self.callback = callback

        if Table.titleFont is None:
            Table.titleFont = font.nametofont("TkTextFont").copy()
            Table.titleFont["weight"] = "bold"
        if not boldTitles:
            self.titleFont = "TkTextFont"

        # Grid rows at the top that will be left empty for a subclass to fill
        # in with other widgets.
        self.headerGridRows = headerGridRows
        # Rows at the top of the table that won't be used for data, for the
        # subclass to fill in with widgets that should be treated as cells.
        # Two rows are reserved for column titles and delete buttons.
        self.headerCells = headerCells + 2

        if "new" in rowOptions:
            self.newRowButton = self.button(
                self.headerCells - 1,
                0,
                "New row",
                self.newRow,
                style="success.Outline.TButton",
            )
        if "new" in columnOptions:
            self.newColumnButton = self.button(
                self.headerCells - 2,
                1,
                "New column",
                self.newColumn,
                style="success.Outline.TButton",
            )

        self.initEmptyCells()
        self.columnTitles = columnTitles

    def initEmptyCells(self):
        self.cells = np.full((self.headerCells, 2), None)

    # all widget creation methods use cell rows, not grid rows, as arguments

    def entry(self, row, column, text="", align="left", columnspan=1, **kwargs):
        entry = ttk.Entry(
            self,
            width=self.width * columnspan,
            justify=align,
            **kwargs,
        )

        entry.stringVar = tk.StringVar(entry)
        entry.configure(textvariable=entry.stringVar)
        if self.callback != "":
            # Callback is registered once for the entire table, but StringVar.trace_add
            # only supports python functions.
            self.tk.eval(
                f"trace add variable {entry.stringVar._name} write {self.callback}"
            )
        entry.set = entry.stringVar.set

        entry.set(text)
        entry.grid(
            row=self.headerGridRows + row,
            column=column,
            sticky="nesw",
            columnspan=columnspan,
        )

        entry.bind("<<Paste>>", lambda *args: self.paste(entry))
        entry.bind("<Tab>", lambda *args: self.tab(entry))
        entry.bind("<Shift-Tab>", lambda *args: self.shiftTab(entry))

        return entry

    def readonlyEntry(self, *args, **kwargs):
        entry = self.entry(*args, style="TLabel", **kwargs)
        entry.state(["readonly"])
        entry.grid(padx=5, pady=5)
        entry.configure(takefocus=False)
        return entry

    def label(self, row, column, text="", columnspan=1, **kwargs):
        frame = ttk.Frame(self, width=self.width * columnspan, borderwidth=5)
        frame.grid(
            row=self.headerGridRows + row,
            column=column,
            sticky="nesw",
            columnspan=columnspan,
        )
        label = ttk.Label(frame, text=text, **kwargs)
        label.pack()
        return frame

    def button(
        self,
        row,
        column,
        text="",
        command=None,
        columnspan=1,
        style="Outline.TButton",
        **kwargs,
    ):
        button = ttk.Button(
            self, text=text, command=command, style=style, takefocus=False, **kwargs
        )
        button.grid(
            row=self.headerGridRows + row,
            column=column,
            sticky="nesw",
            columnspan=columnspan,
            padx=1,
            pady=1,
        )
        return button

    def deleteRowButton(self, *args, **kwargs):
        button = self.button(*args, **kwargs)
        button.configure(
            command=lambda: self.deleteRow(
                button.grid_info()["row"] - self.headerGridRows
            )
        )
        return button

    def deleteColumnButton(self, *args, **kwargs):
        button = self.button(*args, **kwargs)
        button.configure(
            command=lambda button=button: self.deleteColumn(
                button.grid_info()["column"]
            )
        )
        return button

    def dropdown(self, row, column, choices=[], default=None, columnspan=1):
        stringVar = tk.StringVar()
        if default is None:
            default = choices[0]
        optionMenu = ttk.OptionMenu(
            self, stringVar, default, *choices, style="Outline.TMenubutton"
        )
        optionMenu.configure(takefocus=0)
        optionMenu.grid(
            row=self.headerGridRows + row, column=column, sticky="nesw", padx=1, pady=1
        )
        return optionMenu, stringVar

    def redraw(self):
        for (row, column), cell in np.ndenumerate(self.cells):
            if cell is not None:
                cell.grid(row=self.headerGridRows + row, column=column)

    def addRow(self, firstEntry="", data=None):
        row = self.cells.shape[0]
        newRow = np.full(self.cells.shape[1], None)
        if "delete" in self.rowOptions:
            newRow[0] = self.deleteRowButton(row, 0, "Delete")
        if "readonlyTitles" in self.rowOptions:
            newRow[1] = self.readonlyEntry(row, 1, firstEntry, font=self.titleFont)
        elif "titles" in self.rowOptions:
            newRow[1] = self.entry(row, 1, firstEntry, font=self.titleFont)
        for column in range(self.cells.shape[1] - 2):
            entry = self.entry(row, 2 + column, align="right")
            if data is not None:
                entry.set(data[column])
            newRow[2 + column] = entry

        self.cells = np.vstack((self.cells, newRow))

    def addColumn(self, firstEntry="", data=None):
        column = self.cells.shape[1]
        newColumn = np.full(self.cells.shape[0], None)
        if "delete" in self.columnOptions:
            newColumn[self.headerCells - 2] = self.deleteColumnButton(
                self.headerCells - 2, column, "Delete"
            )
        if "readonlyTitles" in self.columnOptions:
            newColumn[self.headerCells - 1] = self.readonlyEntry(
                self.headerCells - 1,
                column,
                firstEntry,
                align="center",
                font=self.titleFont,
            )
        elif "titles" in self.columnOptions:
            newColumn[self.headerCells - 1] = self.entry(
                self.headerCells - 1, column, firstEntry, font=self.titleFont
            )
        for row in range(self.headerCells, self.cells.shape[0]):
            entry = self.entry(row, column, align="right")
            if data is not None:
                entry.set(data[row - self.headerCells])
            newColumn[row] = entry

        self.cells = np.hstack((self.cells, newColumn[:, None]))

    # So that subclasses can specify default values when new rows/columns are added
    # by a button press.
    def newColumn(self):
        self.addColumn()

    def newRow(self):
        self.addRow()

    def deleteRow(self, row):
        for element in self.cells[row]:
            if element is not None:
                element.destroy()
        self.cells = np.delete(self.cells, row, 0)
        self.redraw()

    def deleteColumn(self, column):
        for element in self.cells[:, column]:
            if element is not None:
                element.destroy()
        self.cells = np.delete(self.cells, column, 1)
        self.redraw()

    def resetData(self):
        for row in self.cells:
            for element in row:
                if element is not None:
                    element.destroy()
        self.initEmptyCells()

    def convertData(self, number):
        if self.allowBlanks and number == "":
            return np.nan
        return float(number)

    def setFocus(self, widget):
        widget.tk.eval(f"tk::TabToWindow {widget._w}")

    def tab(self, entry):
        info = entry.grid_info()
        row, column = info["row"] - self.headerGridRows, info["column"]
        rows, columns = self.cells.shape
        while not (row == rows - 1 and column == columns - 1):
            column += 1
            if column >= columns:
                column = 0
                row += 1
            nextCell = self.cells[row, column]
            if isinstance(nextCell, tk.Widget) and nextCell.tk.call(
                "::tk::FocusOK", nextCell
            ):
                self.setFocus(nextCell)
                return "break"

    def shiftTab(self, entry):
        info = entry.grid_info()
        row, column = info["row"] - self.headerGridRows, info["column"]
        rows, columns = self.cells.shape
        while not ((row == 0 and column == 0)):
            column -= 1
            if column < 0:
                column = columns - 1
                row -= 1
            prevCell = self.cells[row, column]
            if isinstance(prevCell, tk.Widget) and prevCell.tk.call(
                "::tk::FocusOK", prevCell
            ):
                self.setFocus(prevCell)
                return "break"

    def paste(self, entry):
        info = entry.grid_info()
        row, column = info["row"] - self.headerGridRows, info["column"]
        rows, columns = self.cells[row:, column:].shape
        pasteContent = self.clipboard_get()
        if "\n" not in pasteContent and "\r" not in pasteContent:
            # Handle as a regular paste. Copying a single cell or row from Excel should
            # still end the string with a newline.
            return
        lines = pasteContent.splitlines()
        if len(lines) > rows:
            mb.showerror(
                title="Paste error",
                message=f"Cannot paste {len(lines)} lines into {rows} rows.",
                parent=self,
            )
            return "break"
        for rowOffset, line in enumerate(lines):
            for columnOffset, value in enumerate(line.split("\t", columns - 1)):
                self.cells[row + rowOffset, column + columnOffset].set(value)
        self.setFocus(self.cells[row + rowOffset, column + columnOffset])
        return "break"

    @property
    def dataCells(self):
        return self.cells[self.headerCells :, 2:]

    @property
    def data(self):
        data = np.full(self.dataCells.shape, self.convertData("0"))
        for (row, column), cell in np.ndenumerate(self.dataCells):
            data[row, column] = self.convertData(cell.get())
        return data

    @data.setter
    def data(self, data):
        if self.dataCells.shape != data.shape:
            raise ValueError(
                "Requested data shape {data.shape} does not match table shape"
                " {cells.shape}."
            )
        for cell, datum in zip(self.dataCells.flat, data.flat):
            cell.set(datum)

    @property
    def rowTitles(self):
        return np.array([title.get() for title in self.cells[self.headerCells :, 1]])

    @rowTitles.setter
    def rowTitles(self, titles):
        for cell, title in zip(self.cells[self.headerCells :, 1], titles):
            cell.set(title)

    @property
    def columnTitles(self):
        return np.array([title.get() for title in self.cells[self.headerCells - 1, 2:]])

    @columnTitles.setter
    def columnTitles(self, titles):
        # make sure the number of columns matches the number of titles
        difference = len(titles) - (self.cells.shape[1] - 2)
        if difference > 0:
            for _ in range(difference):
                self.addColumn()
        elif difference < 0:
            for _ in range(difference):
                self.deleteColumn(self.cells.shape[1])
        if "titles" in self.columnOptions or "readonlyTitles" in self.columnOptions:
            for cell, title in zip(self.cells[self.headerCells - 1, 2:], titles):
                cell.set(title)


class ButtonFrame(ttk.Frame):
    def __init__(self, master, reset, save, cancel, *args, **kwargs):
        super().__init__(master, borderwidth=padding, *args, **kwargs)
        self.resetButton = ttk.Button(
            self, text="Reset", command=reset, style="danger.TButton"
        )
        self.resetButton.pack(side="left", padx=padding)
        self.saveButton = ttk.Button(
            self, text="OK", command=save, style="success.TButton"
        )
        self.saveButton.pack(side="right", padx=padding)
        self.cancelButton = ttk.Button(
            self, text="Cancel", command=cancel, style="secondary.TButton"
        )
        self.cancelButton.pack(side="right", padx=padding)


class WrappedLabel(ttk.Frame):
    # A label that automatically wraps text to its allocated width, and only propagates
    # its height.
    def __init__(self, master, *args, **kwargs):
        super().__init__(master)
        self.pack_propagate(False)
        self.label = ttk.Label(self, *args, **kwargs)
        self.label.pack(expand=True, fill="both")
        self.label.bind("<Configure>", self.callback)

    def callback(self, event):
        self.label.configure(wraplength=event.width - 4)
        self.configure(height=self.label.winfo_reqheight())
