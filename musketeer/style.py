from tkinter import font

padding = 5
cellWidth = 17


def __getattr__(name):
    if name in ["boldFont", "italicFont"]:
        initFonts()
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def initFonts():
    global boldFont, italicFont

    boldFont = font.nametofont("TkTextFont").copy()
    boldFont["weight"] = "bold"

    italicFont = font.nametofont("TkTextFont").copy()
    italicFont["slant"] = "italic"
