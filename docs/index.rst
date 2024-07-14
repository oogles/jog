========================
``jogger`` Documentation
========================

The ``jogger`` command line utility is a simple Python program that isn't quite a fully-fledged task *runner*. In addition to supporting arbitrary tasks, run either directly on the command line or as Python scripts, it ships with some common, useful, Django-aware tasks that can adapt their behaviour based on which packages are available in the system.

A ``jog.py`` file is all that is necessary to use ``jogger``, and it can be as simple or as complex as any given project requires.

.. toctree::
    :maxdepth: 2
    :caption: Contents

    topics/intro
    topics/string_tasks
    topics/func_tasks
    topics/class_tasks
    topics/config
    topics/output
    topics/builtins
    topics/helpers

.. toctree::
    :maxdepth: 2
    :caption: API Reference

    ref/tasks
    ref/output
    ref/exceptions
