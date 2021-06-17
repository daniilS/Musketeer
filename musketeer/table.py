import tkinter as tk
import tkinter.ttk as ttk

import numpy as np

from .style import padding, cellWidth


class Table(ttk.Frame):
    width = cellWidth

    # TODO: add ability to add columns, and link rows to data

    def __init__(self, master):
        super().__init__(master, padding=padding)

        self.addRowButton = self.button(
            self.headerRows-1, 0, "New row", self.addRow
        )

        self.data = np.empty((0, 2+self.dataColumns), float)

    def entry(self, row, column, text="", align="left", columnspan=1):
        entry = ttk.Entry(self, width=self.width*columnspan, justify=align)

        def set(text=""):
            entry.delete(0, "end")
            entry.insert(0, text)
        entry.set = set

        entry.set(text)
        entry.grid(
            row=row, column=column, sticky="nesw", columnspan=columnspan,
        )
        return entry

    def label(self, row, column, text="", columnspan=1):
        frame = ttk.Frame(self, width=self.width*columnspan, borderwidth=5)
        frame.grid(
            row=row, column=column, sticky="nesw", columnspan=columnspan
        )
        label = ttk.Label(frame, text=text)
        label.pack()
        return frame

    def button(self, row, column, text="", command=None, columnspan=1):
        button = ttk.Button(
            self, text=text, command=command, style="Outline.TButton",
            takefocus=False
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

    def addRow(self, firstEntry=""):
        row = self.data.shape[0]
        gridRow = row + self.headerRows
        rowData = []
        rowData.append(
            self.button(
                gridRow, 0, "Delete", lambda row=row: self.deleteRow(row)
            )
        )
        rowData.append(self.entry(gridRow, 1, firstEntry))
        for column in range(self.dataColumns):
            rowData.append(self.entry(gridRow, 2 + column, align="right"))

        self.data = np.vstack((self.data, rowData))

    def deleteRow(self, row):
        for element in self.data[row]:
            element.destroy()
        self.data[row] = np.full(self.data.shape[1], None)
