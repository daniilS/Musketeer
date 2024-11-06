# Musketeer
A software tool for fitting data from titration experiments.
## Installation
### Windows & MacOS:
You can install the latest .msi or .dmg installer [here](https://github.com/daniilS/Musketeer/releases/latest).
### Any platform (requires Python)
Install the latest release of python from [the official website](https://www.python.org/downloads/). Then, in a terminal window or command prompt, type:
- Mac: `python3 -m pip install musketeer`
- Windows: `python -m pip install musketeer`

You can now run Musketeer any time by typing:
- Mac: `python3 -m musketeer`
- Windows: `python -m musketeer`
## Usage Instructions
### Example files
Five example `.fit` files are provided in [examples/](examples/), together with the `.csv` files they were created from. For detailed descriptions of the data and models used in each file, please see [the paper on Musketeer](https://doi.org/10.1039/D4SC03354J), where the same files are also provided as part of the Supplementary Information.

### Loading titration data
When starting Musketeer, you will see the option to either **Create a new fit file** or **Open an existing file**. Musketeer can directly open the following files:

- `.fit` files created using Musketeer
- `.csv` files obtained using Cary UV/Vis spectrometers
- `.csv` files exported from Mnova as "NMR 1D Peak List"

For other data sources, select **Create a new fit file**, and click **Enter/edit spectroscopic data**. This will open a spreadsheet interface where you can type or paste titration data. If you would like to request support for a new file format, please describe it by [submitting a feature request](https://github.com/daniilS/Musketeer/issues/new)!
### Model specification 
Once a file is loaded, the left side of the window will show a series of dropdown menus. Going from top to bottom, each of these can be adjusted to describe some part of the model:

- The _Experiment_ section allows you to edit the signals to fit, specify the concentrations or cumulative addition volumes for each data point, and whether the system is under fast or slow exchange.
- The _Equilibria_ section allows you to define the complexes formed in your system, and specify known values for equilibrium constants or relationships between them (such as the absence of cooperativity).
-  The _Spectra_ section allows you to define which compounds contribute to the observed signal, limit the number of variables by defining specific states that contribute to the signals (e.g. spectroscopically active groups), fix known spectra, or constrain the fitted spectra (e.g. force UV-Vis spectra to be non-negative).
-  The _Fitting_ section controls how the fit from different signals is weighted, which is currently only recommended for backwards compatibility.

If a dropdown requires you to input more data, it will show more information at the top of a popup window.
### Fitting
When you have selected the appropriate option in each dropdown, press **Fit** to fit the data. Several tabs will appear, showing the fit to the data points, the calculated speciation, and the fitted equilibrium constants and spectra. The save button to the bottom left of each plot allows you to save it as an image file.

To compare the fit to a different model, **Copy fit** can create a new tab with the same options, some of which can then be modified. If you change any options, it may be necessary to re-enter the dropdowns below it as well: for example, if you add a new complex, you may need to re-enter which equilibrium constants are fixed.

Finally, the **File->Save** at the top of the screen allows you to save your work as a `.fit` file, which you can reopen at another time, or share with others.

