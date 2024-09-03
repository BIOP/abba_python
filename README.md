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

With ABBA Python, you can control ABBA API from python, and get some additional perks. In particular, you get access to all [BrainGlobe atlases](https://brainglobe.info/documentation/bg-atlasapi/usage/atlas-details.html).

> [!WARNING]
> Due to some threading issues, the GUI does not work with MacOSX

# Getting started

1. Install [miniforge](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html) or [miniforge](https://github.com/conda-forge/miniforge).
2. Create a conda environment with Python 3.10, pyimagej, OpenJDK 11 and maven and activate it
3. Install abba_python
```
conda create -c conda-forge -n abba-env python=3.10 openjdk=11 pip maven pyimagej

conda activate abba-env

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

# Installing extra modules

## Elastix/Transformix

ABBA's automated in-plane registration relies on [elastix 5.0.1](https://github.com/SuperElastix/elastix). To utilize all of ABBA's functionalities, you need to separately install elastix and transformix on your operating system. During the initial run of ABBA, you will be prompted to specify their executable locations. Alternatively, you can set their paths using the API (refer to the [first example notebook](example_notebooks/0.%20Register%20And%20Save%20State.ipynb)).

## DeepSlice

ABBA can leverage the deep-learning registration tool [DeepSlice](https://github.com/PolarBean/DeepSlice), either through the web interface (in the GUI) or by running it locally. To use DeepSlice locally, you must install it in a separate conda environment and specify its path to ABBA, either through the GUI or the API (as explained in the [first example notebook](example_notebooks/0.%20Register%20And%20Save%20State.ipynb)).

Note that DeepSlice can also be used locally with the pure Java version thanks to this (new) design.

To install DeepSlice, please refer to the documentation.

In Sept 2023, this was working:

```
conda create -n deepslice python=3.7
conda activate deepslice
conda install pip
pip install DeepSlice==1.1.5
pip install urllib3==1.26.6 # see https://github.com/PolarBean/DeepSlice/issues/46
```

You also need to make conda available at the system level:
You need to follow this two steps procedure to enable Windows to use conda from cmd.exe:
* Into the environment variable, edit PATH, add path to your ..\Anaconda3\condabin default would be C:\ProgramData\Anaconda3\condabin
* Open a new PowerShell (and/or PowerShell (x86) ), run the following command once to initialize conda:  `conda init`

# Note on versions

OpenJDK versions above 8 can work, but they have been less tested, so there may be unexpected bugs. To avoid [certificate issues](https://pyimagej.readthedocs.io/en/latest/Troubleshooting.html#unable-to-find-valid-certification-path), it is recommended to have openjdk installed from conda-forge.

