================
Tasks as Classes
================

.. currentmodule:: jogger.tasks.base

Usage
=====

The most versatile way to define tasks is using a class, inheriting from :class:`Task`. Tasks defined this way have all the features of :doc:`tasks defined as functions <func_tasks>` (such as :ref:`task-specific settings <class_tasks_settings>`) but also support defining and accepting :ref:`custom arguments <class_tasks_args>`.

The only required method of a class-based task is :meth:`~Task.handle`, which contains the task's logic. If the task needs to execute something on the command line, it can simply pass the command string to the :meth:`~Task.cli` method.

In ``jog.py``, a class-based task might look like:

.. code-block:: python

    from jogger.tasks import Task


    class TestTask(Task):

        help = 'Run the Django test suite, with coverage.py if installed.'

        def handle(self, *args, **options):

            command = 'python manage.py test'

            try:
                import coverage
            except ImportError:
                self.stdout.write('Warning: coverage.py not installed.', style='warning')
            else:
                command = f'coverage run {command}'

            self.cli(command)

    tasks = {
        'test': TestTask
    }

Similarly to :doc:`function-based tasks <func_tasks>`, any output from the task can be printed using the :attr:`~Task.stdout` and :attr:`~Task.stderr` attributes, which offer additional control over the output. See :doc:`output`.

Executing commands
------------------

As noted above, commands can be executed on the command line via the :meth:`~Task.cli` method. This method uses the Python `subprocess module <https://docs.python.org/3/library/subprocess.html>`_ and returns ``CompletedProcess`` `result object <https://docs.python.org/3/library/subprocess.html#subprocess.CompletedProcess>`_. Among other things, this object contains the following useful attributes:

* ``returncode``: The integer exit status of the command. Typically, an exit status of ``0`` indicates success.
* ``stdout``: The complete standard output from the command, if any.
* ``stderr``: The complete error output from the command, if any.

Sometimes it is useful to suppress the output a command would typically generate. This may be because it is never relevant, or in order to support a low-verbosity mode for the task, or because the task wishes to process the output before displaying or otherwise acting on it. This is supported by passing the optional ``no_output=True`` flag when calling the method:

.. code-block:: python

    self.cli('echo "hello"', no_output=True)

Executing other tasks
---------------------

Sometimes it is useful for one task to be able to directly execute another. Class-based tasks support this through the :meth:`~Task.get_task_proxy` method. This method returns a proxy object that can be used to execute a task in a common way, regardless of whether it was defined as a string, function, or class.

If the given task hasn't been defined in ``jog.py``, or it is improperly defined, the method will raise :exc:`~jogger.exceptions.TaskDefinitionError`.

The following example attempts to execute the ``build`` task if it has been defined, otherwise proceeds uninterrupted:

.. code-block:: python

    from jogger.exceptions import TaskDefinitionError
    from jogger.tasks import Task


    class UpdateTask(Task):

        help = (
            'Update the application to the latest version, including '
            'building any necessary assets if configured.'
        )

        def handle(self, *args, **options):

            # ...

            # Update assets if a task exists to do so
            try:
                build_proxy = self.get_task_proxy('build', '--all')
            except TaskDefinitionError:
                pass
            else:
                self.stdout.write('Building all assets', style='label')
                build_proxy.execute()

            # ...

Halting execution
-----------------

If an error occurs and the execution of the task should be interrupted, simply raise :exc:`~jogger.exceptions.TaskError`. Any message passed to the exception will be written to the configured ``stderr`` stream and the task will be halted.


.. _class_tasks_settings:

Using settings
==============

If your project :doc:`defines a config file <config>`, and it contains a section for the task being executed, the settings within that section are available to a class-based task via the :attr:`~Task.settings` attribute. This allows common tasks to be shared among multiple projects, while still allowing them to be configured as necessary for each one.

.. important::

    The attribute itself is a *dictionary-like* collection of the settings listed in the config file, but it is **not** a true dictionary. See an explanation of the differences in the :ref:`config file documentation <config_task_settings>`.

Re-working the above example of the ``test`` task so that the use of `coverage.py <https://coverage.readthedocs.io/>`_ is based on a project-level setting might look like:

.. code-block:: ini

    # setup.cfg
    [jogger:test]
    coverage = true

.. code-block:: python

    # jog.py
    from jogger.tasks import Task


    class TestTask(Task):

        help = 'Run the Django test suite, optionally with coverage.py.'

        def handle(self, *args, **options):

            command = 'python manage.py test'

            if self.settings.getboolean('coverage', True):
                command = f'coverage run {command}'

            self.cli(command)

    tasks = {
        'test': TestTask
    }


.. _class_tasks_args:

Using arguments
===============

Arguments are defined using the :meth:`~Task.add_arguments` method, and are made available to the :meth:`~Task.handle` method as keyword arguments. Re-working the above example again so that the use of `coverage.py <https://coverage.readthedocs.io/>`_ is based on a runtime argument might look like:

.. code-block:: python

    # jog.py
    from jogger.tasks import Task


    class TestTask(Task):

        help = 'Run the Django test suite, optionally with coverage.py.'

        def add_arguments(self, parser):

            parser.add_argument(
                '--coverage',
                action='store_true',
                help='Apply code coverage analysis to the executed test suite.'
            )

        def handle(self, *args, **options):

            command = 'python manage.py test'

            if options['coverage']:
                command = f'coverage run {command}'

            self.cli(command)

    tasks = {
        'test': TestTask
    }

This task can then be invoked as such::

    jog test             # without coverage
    jog test --coverage  # with coverage

See Python's `argparse <https://docs.python.org/3/library/argparse.html#module-argparse>`_ documentation for details on defining command line arguments.

.. _class_tasks_default_args:

Default arguments
-----------------

In addition to supporting custom arguments, all :class:`Task` subclasses accept the following default arguments:

* ``-h``/``--help``: Display the task's :ref:`help output <class_tasks_help>`.
* ``--no-color``: Prevents colourisation of command output (e.g. if the task makes use of :ref:`styled output <output_styling>`).
* ``stderr``: The output stream to use for error messages. Defaults to the system's ``stderr`` stream. Can be redirected, e.g. to a file: ``jog test --stderr /home/myuser/logs/test/err.log``.
* ``stdout``: The output stream to use for general messages. Defaults to the system's ``stdout`` stream. Can be redirected, e.g. to a file: ``jog test --stdout /home/myuser/logs/test/out.log``.
* ``-v``/``--verbosity``: An integer between ``0`` and ``3`` (inclusive). Defaults to ``1``. A generic verbosity level, available to be used (or not) by individual tasks as they see fit.


.. _class_tasks_help:

Getting help
============

As with both :doc:`string-based <string_tasks>` and :doc:`function-based <func_tasks>` tasks, class-based tasks accept a ``-h``/``--help`` argument which displays help text for the task. Unlike the other task types, tasks defined as classes also include their accepted arguments in the help output.

The descriptive portion of the task's help text comes from the :attr:`~Task.help` attribute. If the task does not define a :attr:`~Task.help` attribute, no task description will be included in the help text.

Also included will be a listing of all the task's accepted command line arguments - both the default ones described above and any custom ones added using :meth:`~Task.add_arguments`. Custom arguments can use the ``help`` `argument <https://docs.python.org/3/library/argparse.html#help>`_ of ``parser.add_argument()`` to provide a useful description.
