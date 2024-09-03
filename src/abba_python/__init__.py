"""Aligning Big Brains and Atlases (ABBA), controlled from python."""

from importlib.metadata import PackageNotFoundError, version

# Metadata
try:
    __version__ = version("abba-python")
except PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Nicolas Chiaruttini"
__email__ = "nicolas.chiaruttini@epfl.ch"

# Public API
from .abba import Abba

__all__ = ['Abba']
