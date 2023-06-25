import sys

from cx_Freeze import Executable, setup

build_options = {
    "packages": [],
    "excludes": [],
    "include_files": [] if sys.platform == "win32" else ["logo 512px.png"],
}
msi_options = {"install_icon": "logo 48px.ico"}


base = "Win32GUI" if sys.platform == "win32" else None

executables = [
    Executable(
        "Musketeer_test.py",
        base=base,
        target_name="Musketeer",
        shortcut_name="Musketeer",
        shortcut_dir="StartMenuFolder",
        icon="logo 48px.ico" if sys.platform == "win32" else "logo 512px.png",
    )
]

setup(
    name="Musketeer",
    version="1.3.0",
    description="Musketeer",
    options={"build_exe": build_options, "bdist_mis": msi_options},
    executables=executables,
)
