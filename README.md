# abba-python

[![License](https://img.shields.io/pypi/l/abba-python.svg?color=green)](https://github.com/BIOP/abba_python/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/abba-python.svg?color=green)](https://pypi.org/project/abba-python)
[![Python Version](https://img.shields.io/pypi/pyversions/abba-python.svg?color=green)](https://python.org)
[![CI](https://github.com/BIOP/abba_python/actions/workflows/ci.yml/badge.svg)](https://github.com/BIOP/abba_python/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/BIOP/abba_python/branch/main/graph/badge.svg)](https://codecov.io/gh/BIOP/abba_python)

Aligning Big Brains and Atlases (ABBA), controlled from python.

* Documentation: https://abba-documentation.readthedocs.io

# ABBA in brief

Aligning Big Brains & Atlases, abbreviated as ABBA, allows you to register thin serial sections to multiple atlases in coronal, sagittal, and horizontal orientations. It is mainly a Java application, but this repo makes all of its API accessible in Python.

With ABBA Python, you can control the ABBA API from Python.

> [!WARNING]
> Due to some threading issues, the GUI does not work with macOS. On macOS, use the regular [Fiji](https://fiji.sc) installation of ABBA instead — it already includes access to all BrainGlobe atlases.

# Requirements

`abba-python` is a thin Python wrapper around the Java ABBA application. The only thing you need on your machine is **Python 3.10 or later** (tested up to 3.14).

You do **not** need to install Java or Maven: on the first run, [PyImageJ](https://pyimagej.readthedocs.io)/scyjava downloads a Java 21 runtime and the ABBA jars (a few hundred MB) by itself, and caches them for the next runs.

The automated registration tools (elastix/transformix, local DeepSlice) and BrainGlobe atlas downloads are handled by ABBA itself: it provisions its own isolated Python environments on demand (via [Appose](https://github.com/apposed/appose)). You do **not** need to install elastix, DeepSlice or `brainglobe-atlasapi` yourself.

# Installation

## With pixi (recommended)

[pixi](https://pixi.sh) is a modern, lockfile-based package manager:

```
pixi init abba-project
cd abba-project
pixi add python=3.13
pixi add --pypi abba-python
```

Run Python inside the project with `pixi run python` (or `pixi shell` to activate the environment).

## With conda / mamba

Using [miniforge](https://github.com/conda-forge/miniforge):

```
mamba create -c conda-forge -n abba-env python=3.13 pip
mamba activate abba-env
pip install abba-python
```

## With uv or pip

Since no Java or Maven installation is needed, a plain virtual environment works too, e.g. with [uv](https://docs.astral.sh/uv):

```
uv venv --python 3.13
uv pip install abba-python
```

# Getting started

## Graphical user interface (GUI)

In your environment, launch Python and run:

```python
from abba_python import abba
ij = abba.start_imagej()
```

You can then use ABBA within Fiji. ABBA is typically used together with [QuPath](https://qupath.github.io/): a QuPath project can serve as input for ABBA, and the registration results can be imported back into QuPath for further processing.

## Python API

The `Abba` object drives a registration session programmatically. Any [BrainGlobe atlas](https://brainglobe.info/documentation/brainglobe-atlasapi/usage/atlas-details.html) name works, as well as the built-in Java atlases (`'Adult Mouse Brain - Allen Brain Atlas V3p1'`, `'Rat - Waxholm Sprague Dawley V4p2'`):

```python
from abba_python.abba import Abba

# 'example_mouse_100um' is the small BrainGlobe demo atlas — quick to download.
# BrainGlobe atlases are named with their version: versions change the region ids.
abba = Abba('example_mouse_100um@3.0')
abba.show_bdv_ui()  # opens a BigDataViewer window
```

Every ABBA command is a method of `Abba`, with keyword arguments: for example
`abba.import_slices_from_files(...)`, `abba.distribute_slices()`, `abba.register_slices_deepslice_appose(...)`,
`abba.undo()` or `abba.get_state()`. The parameters and their defaults are those of the ABBA command, and each
method's docstring describes them (`help(Abba.distribute_slices)`). A parameter without default must be given:
otherwise ABBA asks for it in a dialog.

See the [`examples/`](examples) folder for runnable scripts (`demo_brainglobe.py`, `demo_api.py`, `demo_bench.py`, `demo_gui.py`).

## Extra Java dependencies

`start_imagej()` and `Abba()` take `extra_dependencies`: more jars, as Maven coordinates, put on the
classpath next to ABBA's. For example, [fiji-llm](https://github.com/fiji/fiji-llm) (the LLM assistant
and MCP server of Fiji) and [fiji-modules](https://github.com/unige-biochem/fiji-modules):

```python
from abba_python import abba

JETTY_11 = [f'org.eclipse.jetty:jetty-{module}:11.0.20'
            for module in ('server', 'servlet', 'util', 'http', 'io', 'security')]
ij = abba.start_imagej(extra_dependencies=['sc.fiji:fiji-llm:0.1.0',
                                           'ch.unige.biochem:fiji-modules:0.1.2', *JETTY_11])
```

The libraries they share with ABBA get the versions ABBA is built with, so that ABBA keeps working.
A jar that needs another version of one of them has to pin it, as above: fiji-llm 0.1.0 needs
Jetty 11, and ABBA's versions would give it Jetty 9 (`NoClassDefFoundError: jakarta/servlet/Servlet`).
The first run downloads the extra jars; ABBA without `extra_dependencies` is not affected.

## Jupyter lab

```
pixi add jupyterlab ipywidgets   # or: pip install jupyterlab ipywidgets
```

You can then run `jupyter lab` and use notebooks.

# Note on versions

Java 21 is required: ABBA's jars are compiled for Java 21 and fail to load on older versions (`UnsupportedClassVersionError`). `abba-python` asks scyjava for Java 21 before starting the JVM (see `JAVA_VERSION` in `abba.py`), and scyjava downloads it (a Zulu JRE) on the first run, whatever Java is installed on the system.

This requires `pyimagej>=1.8.0`, which pulls `scyjava>=1.12.4` and `jgo>=2.1`: older versions cannot fetch Java by themselves and need a JDK on the system.
