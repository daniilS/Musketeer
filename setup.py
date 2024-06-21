import warnings
from pathlib import Path

import setuptools

with open("README.md") as readmeFile:
    long_description = readmeFile.read()


def get_version():
    filePath = Path("./musketeer/__init__.py")
    if not filePath.exists():
        warnings.warn(
            "Could not locate __init__.py to read the version number from",
            RuntimeWarning,
        )
        return "0.0.1.unknown.version"
    with Path("./musketeer/__init__.py").open() as file:
        for line in file:
            if line.startswith("__version__"):
                return line.split('"')[1]
        else:
            warnings.warn(
                "Could not find version string in __init__.py", RuntimeWarning
            )
            return "0.0.1.unknown.version"


setuptools.setup(
    name="musketeer",
    version=get_version(),
    author="Daniil Soloviev",
    author_email="dos23@cam.ac.uk",
    description="A tool for fitting data from titration experiments.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Chemistry",
    ],
    url="https://github.com/daniilS/Musketeer",
    packages=["musketeer"],
    include_package_data=True,
    install_requires=[
        "matplotlib >= 3.9.0",
        "numpy",
        "packaging",
        "scipy",
        "ttkbootstrap >=0.5.2, <1.0",
        "ttkwidgets",
        "tksheet >= 7.0.5",
    ],
    python_requires=">=3.9",
)
