
# ABBA Python

[![](https://img.shields.io/pypi/v/abba_python.svg)](https://pypi.python.org/pypi/abba_python)

[![](https://img.shields.io/travis/nicoKiaru/abba_python.svg)](https://travis-ci.com/nicoKiaru/abba_python)

Aligning Big Brains and Atlases, controlled from Python.

* Free software: GNU General Public License v3
* Documentation: https://biop.github.io/ijp-imagetoatlas/

# ABBA in short

Aligning Big Brains & Atlases or ABBA for short, allows to register thin serial sections to several atlases, in coronal, sagittal and horizontal orientations.

With ABBA Python, you have access to the 3D mouse Allen Brain atlas, and the Waxholm Space Atlas of the Sprague Dawley Rat Brain and all [other BrainGlobe atlases](https://brainglobe.info/documentation/bg-atlasapi/usage/atlas-details.html).

ABBA Python allows to use [DeepSlice](https://pypi.org/project/DeepSlice/) for automated registration of mouse coronal sections (rat not implemented yet).

# Getting started

To get started with a GUI:
- install miniconda
- create a conda env with python 3.7 and openjdk 8:

```
conda create -c conda-forge -n myenv python=3.7 openjdk=8

conda activate myenv

pip install abba_python

python

>> from abba_python import abba

>> abba.start_imagej()
```

You can then use ABBA in Fiji, see https://biop.github.io/ijp-imagetoatlas/

ABBA is typically used in conjunction with QuPath (https://qupath.github.io/): a QuPath project can serve as an input for ABBA, and the registration results can be imported back into QuPath for downstream processing.

# Note on versions

`abba_python` do not support python version above 3.7 because DeepSlice depends on tensorflow 1.15, which is not supported for later versions of python (https://github.com/PolarBean/DeepSlice/issues/41).

Openjdk version can work for version above 8, but it has been less used, so there may be unexpected bugs. You need to have openjdk installed from conda-forge, if you want to avoid [certificate issues](https://pyimagej.readthedocs.io/en/latest/Troubleshooting.html#unable-to-find-valid-certification-path).

# Credits

This package was created with Cookiecutter and the `audreyr/cookiecutter-pypackage` project template.

[Cookiecutter](https://github.com/audreyr/cookiecutter)

[audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage)
