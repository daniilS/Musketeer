import ctypes
from tkinter import ttk

# From Windows 10, version 1607 onwards, it's possible to set the high DPI
# scaling mode to "System (Enhanced)" using this function. This makes the
# GUI look less blurry on displays using a scaling factor above 100%.
#
# The other options for DPI awareness contexts don't work well when moving
# windows between monitors with different DPIs, and require manual scaling
# for some elements, so GDI scaling seems like the best option for now.
#
# Information on the syscall:
# https://docs.microsoft.com/en-us/windows/win32/hidpi/dpi-awareness-context
# https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext


def setEnhancedDpiScaling():
    # see if we are on a version of Windows that supports this syscall
    try:
        setThreadDpiAwarenessContext = \
            ctypes.windll.user32.SetThreadDpiAwarenessContext
    except:  # noqa
        return

    DPI_AWARENESS_CONTEXT_UNAWARE = -1
    DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED = -5
    setThreadDpiAwarenessContext.argtypes = (ctypes.c_void_p,)
    setThreadDpiAwarenessContext.restype = ctypes.c_void_p

    def disableGdiScaling():
        setThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_UNAWARE)

    def enableGdiScaling():
        setThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED)

    enableGdiScaling()

    # If the DPI awareness context is set to System (Enhance) as above, and a
    # tkinter window is created on one monitor and then dragged to another with
    # a high DPI, then menu widgets from OptionMenus will first briefly
    # flash on the original monitor, then appear on the correct monitor, then
    # be resized to the correct size. To avoid this graphical glitch, we
    # temporarily disable GDI scaling while a menu is being shown.
    def processMenuSelectEvent(event):
        if event.x == 0:
            # menu has been closed
            enableGdiScaling()

    oldInit = ttk.OptionMenu.__init__

    def newInit(self, *args, **kwargs):
        oldInit(self, *args, **kwargs)
        menu = self["menu"]
        menu.configure(postcommand=disableGdiScaling)
        menu.bind("<<MenuSelect>>", processMenuSelectEvent)

    ttk.OptionMenu.__init__ = newInit
