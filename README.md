# abba-python

[![License](https://img.shields.io/pypi/l/abba-python.svg?color=green)](https://github.com/BIOP/abba-python/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/abba-python.svg?color=green)](https://pypi.org/project/abba-python)
[![Python Version](https://img.shields.io/pypi/pyversions/abba-python.svg?color=green)](https://python.org)
[![CI](https://github.com/BIOP/abba_python/actions/workflows/ci.yml/badge.svg)](https://github.com/BIOP/abba-python/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/BIOP/abba-python/branch/main/graph/badge.svg)](https://codecov.io/gh/BIOP/abba-python)

Aligning Big Brains and Atlases (ABBA), controlled from python.

* Documentation: https://abba-documentation.readthedocs.io

# ABBA in brief

Aligning Big Brains & Atlases, abbreviated as ABBA, allows you to register thin serial sections to multiple atlases in coronal, sagittal, and horizontal orientations. It is mainly a Java application, but this repo makes all of its API accessible in Python.

With ABBA Python, you can control ABBA API from python, and get some additional perks. In particular, you get access to all [BrainGlobe atlases](https://brainglobe.info/documentation/brainglobe-atlasapi/usage/atlas-details.html).

> [!WARNING]
> Due to some threading issues, the GUI does not work with MacOSX

# Getting started

1. Install [miniforge](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html) or [miniforge](https://github.com/conda-forge/miniforge).
2. Create a conda environment with Python 3.10, pyimagej, OpenJDK 11 and maven and activate it
3. Install abba_python
```
mamba create -c conda-forge -n abba-env python=3.10 openjdk=11 pip maven pyimagej

mamba activate abba-env

pip install abba_python
```


## To begin using ABBA with a graphical user interface (GUI):

In the created environment, launch Python and run the following commands:

```
from abba_python import abba
abba.start_imagej()
```

You can then use ABBA within Fiji.
ABBA is typically used in conjunction with [QuPath](https://qupath.github.io/): a QuPath project can serve as input for ABBA, and the registration results can be imported back into QuPath for further processing.

## To begin with ABBA with jupyter lab

In the created environment, install `jupyterlab` and `ipywidgets`:

```
pip install jupyterlab
pip install ipywidgets
```

You can now run `jupyter lab` and start using notebooks, like the ones provided in examples in the gitHub repo.

# Extra registration tools

## Elastix/Transformix

ABBA's automated in-plane registration relies on [elastix](https://github.com/SuperElastix/elastix). You no longer need to install elastix and transformix yourself: ABBA manages its own Python environment (via Appose) and provisions them automatically, so no path configuration is required.

## DeepSlice

ABBA can leverage the deep-learning registration tool [DeepSlice](https://github.com/PolarBean/DeepSlice), either through the web interface or by running it locally. Local DeepSlice is now bundled on the Java side: ABBA manages its own Python environment (via Appose) and installs DeepSlice automatically the first time you run a local DeepSlice registration. No separate conda environment or path configuration is required anymore.

# Note on versions

OpenJDK versions above 8 can work, but they have been less tested, so there may be unexpected bugs. To avoid [certificate issues](https://pyimagej.readthedocs.io/en/latest/Troubleshooting.html#unable-to-find-valid-certification-path), it is mandatory to have openjdk installed from conda-forge.

