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

With ABBA Python, you can control the ABBA API from Python.

> [!WARNING]
> Due to some threading issues, the GUI does not work with macOS. On macOS, use the regular [Fiji](https://fiji.sc) installation of ABBA instead — it already includes access to all BrainGlobe atlases.

# Requirements

`abba-python` is a thin Python wrapper around the Java ABBA application. At runtime the Java dependencies are fetched from Maven, so you need three things on your machine:

- **Python** 3.9–3.12
- **OpenJDK 11** — ideally from conda-forge, to avoid [certificate issues](https://pyimagej.readthedocs.io/en/latest/Troubleshooting.html#unable-to-find-valid-certification-path) when downloading jars and atlases
- **Maven** — used by [PyImageJ](https://pyimagej.readthedocs.io)/scyjava to resolve the ABBA jars on the first run

The automated registration tools (elastix/transformix, local DeepSlice) and BrainGlobe atlas downloads are handled by ABBA itself: it provisions its own isolated Python environments on demand (via [Appose](https://github.com/apposed/appose)). You do **not** need to install elastix, DeepSlice or `brainglobe-atlasapi` yourself.

# Installation

## With pixi (recommended)

[pixi](https://pixi.sh) is a modern, lockfile-based package manager that can pull `openjdk` and `maven` from conda-forge alongside the Python dependencies:

```
pixi init abba-project
cd abba-project
pixi add python=3.10 openjdk=11 maven pyimagej
pixi add --pypi abba-python
```

Run Python inside the project with `pixi run python` (or `pixi shell` to activate the environment).

## With conda / mamba

Using [miniforge](https://github.com/conda-forge/miniforge):

```
mamba create -c conda-forge -n abba-env python=3.10 openjdk=11 pip maven pyimagej
mamba activate abba-env
pip install abba-python
```

## A note on uv

[uv](https://docs.astral.sh/uv) only manages Python and PyPI packages — it cannot provide the JDK and Maven that ABBA needs, and a non-conda-forge JDK is prone to the certificate issues mentioned above. If you really want to use uv, you must install OpenJDK 11 and Maven yourself (and make them available on `PATH`) before `uv pip install abba-python`. For most users `pixi` is the simpler choice.

# Getting started

## Graphical user interface (GUI)

In your environment, launch Python and run:

```python
from abba_python import abba
abba.start_imagej()
```

You can then use ABBA within Fiji. ABBA is typically used together with [QuPath](https://qupath.github.io/): a QuPath project can serve as input for ABBA, and the registration results can be imported back into QuPath for further processing.

## Python API

The `Abba` object drives a registration session programmatically. Any [BrainGlobe atlas](https://brainglobe.info/documentation/brainglobe-atlasapi/usage/atlas-details.html) name works, as well as the built-in Java atlases (`'Adult Mouse Brain - Allen Brain Atlas V3p1'`, `'Rat - Waxholm Sprague Dawley V4p2'`):

```python
from abba_python.abba import Abba

# 'example_mouse_100um' is the small BrainGlobe demo atlas — quick to download
abba = Abba('example_mouse_100um')
abba.show_bdv_ui()  # opens a BigDataViewer window
```

See the [`examples/`](examples) folder for runnable scripts (`demo_brainglobe.py`, `demo_api.py`, `demo_bench.py`, `demo_gui.py`).

## Jupyter lab

```
pixi add jupyterlab ipywidgets   # or: pip install jupyterlab ipywidgets
```

You can then run `jupyter lab` and use notebooks.

# Note on versions

OpenJDK 11 is recommended. Versions above 11 may work but are less tested, so there may be unexpected bugs. To avoid [certificate issues](https://pyimagej.readthedocs.io/en/latest/Troubleshooting.html#unable-to-find-valid-certification-path), install OpenJDK from conda-forge (pixi and mamba both do this).
