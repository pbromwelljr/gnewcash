Overview
********

What is gnewcash?
-----------------

GNewCash is a Python package built for reading, writing, and interacting with `GnuCash <http://gnucash.org>`_ files.
It is an alternative to using the `GnuCash Python bindings <https://wiki.gnucash.org/wiki/Python_Bindings>`_.
If you find issues using GNewCash, please add it to our `issue tracker <https://github.com/pbromwelljr/gnewcash/issues>`_.

Compatibility
-------------

Python
~~~~~~
GNewCash is developed on Python 3.12, and unit tests run on the following versions:

- 3.9
- 3.10
- 3.11
- 3.12

If you find your Python version listed above but are running into issues, please submit an issue to our `issue tracker <https://github.com/pbromwelljr/gnewcash/issues>`_.

GNewCash
~~~~~~~~

This package only relies on the Python standard library, so it should be compatible with Windows, Mac OSX, and Linux.

All code and tests are designed for GnuCash version 2 files. Versions 3+ are also supported.

Liability
---------

GNewCash is released under the `MIT license <https://opensource.org/licenses/MIT>`_, and as such you are allowed to perform all actions listed in the license.

As expressed in the license, I hold no liability in the event that GnuCash corrupts or incorrectly modifies your data. I highly recommend backing up GnuCash files before operating on them with GNewCash.

Installing GNewCash
-------------------

To install GNewCash, simply run:

::

    pip install gnewcash

