import sys

import musketeer
from cx_Freeze import Executable, setup

build_options = {
    "packages": [],
    "excludes": [],
    "include_files": [] if sys.platform == "win32" else ["logo 512px.png"],
}
msi_options = {
    "install_icon": "logo 48px.ico",
    "upgrade_code": "{C327C15B-6058-313C-AADF-E979233602A5}",
    "summary_data": {"author": "Daniil Soloviev"},
}


base = "Win32GUI" if sys.platform == "win32" else None

executables = [
    Executable(
        "musketeer_loader.py",
        base=base,
        target_name="Musketeer",
        shortcut_name="Musketeer",
        shortcut_dir="ProgramMenuFolder",
        icon="logo 48px.ico" if sys.platform == "win32" else "logo 512px.png",
    )
]

setup(
    name="Musketeer",
    version=musketeer.__version__,
    description="Musketeer",
    options={"build_exe": build_options, "bdist_msi": msi_options},
    executables=executables,
)
