import setuptools

with open("README.md") as readmeFile:
    long_description = readmeFile.read()

setuptools.setup(
    name="musketeer",
    version="0.1.6",
    author="Daniil Soloviev",
    author_email="dos23@cam.ac.uk",
    description="A tool for fitting data from titration experiments.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
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
        "numpy",
        "scipy",
        "matplotlib",
        "ttkbootstrap >=0.5.2, <1.0",
        "ttkwidgets",
        "tksheet",
    ],
    python_requires=">=3.7",
)
