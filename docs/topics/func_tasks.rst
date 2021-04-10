==================
Tasks as Functions
==================

Usage
=====

If a task needs to execute something on the command line, but the command itself isn't suited to being defined :doc:`as a string <string_tasks>`, it can instead be defined as a function that *returns* the command. Tasks defined in this way might be useful if:

* The command is dynamic, and may differ depending on certain aspects of the environment, e.g. whether a particular package is installed
* The command is complex and it is useful for various aspects of it to be commented
* The command is simply too long to be easily maintained as a single string
* It is a shared task that may require per-project configuration (see :ref:`func_tasks_settings`) below.

In ``jog.py``, these tasks might look like:

.. code-block:: python

    def run_tests(settings, stdout, stderr):
        """
        Run the Django test suite, with coverage.py if installed.
        """

        try:
            import coverage
        except ImportError:
            stdout.write('Warning: coverage.py not installed.', style='warning')
            return 'python manage.py test'
        else:
            return 'coverage run python manage.py test'

    tasks = {
        'test': run_tests
    }

Task functions accept the following arguments:

* ``settings``: A dictionary-like collection of the settings defined for the task in a config file, as :ref:`explained below <func_tasks_settings>`.
* ``stdout``: A proxy for the standard output stream, offering more control over output from the task. See :doc:`output`.
* ``stderr``: A proxy for the standard error stream, offering more control over output from the task. See :doc:`output`.

Like tasks :doc:`defined as strings <string_tasks>`, tasks defined as functions cannot accept additional command line arguments. While the executed command can be dynamically constructed, and :ref:`configurable via settings <func_tasks_settings>`, the string returned by the function cannot be further altered by runtime arguments. For example, considering the ``test`` task defined above::

    jog test  # good
    jog test myproject.tests.test_module  # bad

Halting execution
-----------------

If an error occurs and the execution of the task should be interrupted, simply raise :exc:`~jogger.exceptions.TaskError`. Any message passed to the exception will be written to the configured ``stderr`` stream and the task will be halted.


.. _func_tasks_settings:

Using settings
==============

As noted above, task functions accept a ``settings`` argument. Your project can define a config file, as explained further in the :doc:`config` documentation. If that config file contains a section for the task being executed, the settings within that section will be passed through to the task using the ``settings`` argument. This allows common tasks to be shared among multiple projects, while still allowing them to be configured as necessary for each one.

.. important::

    The argument itself is a *dictionary-like* collection of the settings listed in the config file, but it is **not** a true dictionary. See an explanation of the differences in the :ref:`config file documentation <config_task_settings>`.

Re-working the above example so that the use of `coverage.py <https://coverage.readthedocs.io/>`_ is based on a project-level setting might look like:

.. code-block:: ini

    # setup.cfg
    [jogger:test]
    coverage = true

.. code-block:: python

    # jog.py
    def run_tests(settings, stdout, stderr):
        """
        Run the Django test suite, optionally with coverage.py.
        """

        if settings.getboolean('coverage', True):
            return 'coverage run python manage.py test'
        else:
            return 'python manage.py test'

    tasks = {
        'test': run_tests
    }


Getting help
============

The only command line argument accepted by tasks defined as functions is ``-h``/``--help``, which displays help text for the task. The help text will be pulled from the function's docstring. For example, the help text for the ``test`` task defined above would be: "Run the Django test suite, optionally with coverage.py." If the function does not have a docstring, ``-h``/``--help`` will display the task's signature, but not include any other help text.
