===========
ABBA Python
===========


.. image:: https://img.shields.io/pypi/v/abba_python.svg
        :target: https://pypi.python.org/pypi/abba_python

.. image:: https://img.shields.io/travis/nicoKiaru/abba_python.svg
        :target: https://travis-ci.com/nicoKiaru/abba_python




Aligning Big Brains and Atlases, controlled from Python.


* Free software: GNU General Public License v3
* Documentation: https://biop.github.io/ijp-imagetoatlas/


ABBA in short
-------------

Aligning Big Brains & Atlases or ABBA for short, allows to register thin serial sections to several atlases, in coronal, sagittal and horizontal orientations.

With ABBA Python, you have access to the 3D mouse Allen Brain atlas, and the Waxholm Space Atlas of the Sprague Dawley Rat Brain and all other BrainGlobe (https://docs.brainglobe.info/) atlases.

ABBA Python allows to use DeepSlice (https://pypi.org/project/DeepSlice/) for automated registration of mouse coronal sections (rat not implemented yet).

To get started with a GUI:
- install miniconda
- create a conda env with python 3.7 and openjdk 8:

conda create -n myenv python=3.8 openjdk=8

conda activate myenv

python

>> from abba_python import abba

>> abba.start_imagej()

You can then use ABBA in Fiji, see https://biop.github.io/ijp-imagetoatlas/

ABBA is typically used in conjunction with QuPath (https://qupath.github.io/): a QuPath project can serve as an input for ABBA, and the registration results can be imported back into QuPath for downstream processing.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
