"""
Laser Setup
===========
A GUI for running PyMeasure procedures and controlling instruments.

This package is built on top of the PyMeasure package.
It provides a framework for creating custom procedures and
scripts. The package is designed to be easily extendable and
customizable.
"""
try:
    from . import patches  # noqa: F401, patches PyMeasure classes
except ModuleNotFoundError as exc:
    # Allow lightweight imports (e.g., utility tests) without PyMeasure installed.
    if exc.name != "pymeasure":
        raise
    patches = None

__version__ = '0.5.1-alpha'
