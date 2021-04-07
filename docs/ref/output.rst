============
Output Utils
============

.. module:: jogger.utils.output

.. autoclass:: Styler

    .. attribute:: PALETTE

        A dictionary defining the name and attributes of each preconfigured role. Its entries are mapped into methods on the class that can be used as shortcuts to apply the corresponding set of style attributes to the given text. Subclasses can define their own palettes.

    .. automethod:: apply
    .. automethod:: reset
