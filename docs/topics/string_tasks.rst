================
Tasks as Strings
================

Usage
=====

The simplest way to define a task for ``jogger`` to execute is simply a string containing the command to execute on the command line. In ``jog.py``, that might look like:

.. code-block:: python

    tasks = {
        'hello': 'echo "Hello, World!"',
        'test': 'coverage run python manage.py test'
    }

The advantage of adding tasks like this is to provide shortcuts to common commands, perhaps ones that take a series of arguments and thus lend themselves to using a shortcut.

However, there are disadvantages as well. Tasks defined as strings are executed as-is, they cannot be customised by passing arguments when running the task. For example, considering the ``test`` task defined above::

    jog test  # good
    jog test myproject.tests.test_module  # bad


.. _string_tasks_default_args:

Default arguments
=================

String-based tasks accept a minimal set of default arguments:

* ``-h``/``--help``: Display the task's help output. For string-based tasks, this is very minimal, and cannot be customised. It simply states what the task does (i.e. it outputs the command string itself).
* ``--stderr``: The output stream to use for error messages. Defaults to the system's ``stderr`` stream. Can be redirected, e.g. to a file: ``jog test --stderr /home/myuser/logs/test/err.log``.
* ``--stdout``: The output stream to use for general messages. Defaults to the system's ``stdout`` stream. Can be redirected, e.g. to a file: ``jog test --stdout /home/myuser/logs/test/out.log``.
