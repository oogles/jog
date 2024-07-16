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

As noted above, commands can be executed on the command line via the :meth:`~Task.cli` method. This method uses the Python `subprocess module <https://docs.python.org/3/library/subprocess.html>`_ and returns a ``CompletedProcess`` `result object <https://docs.python.org/3/library/subprocess.html#subprocess.CompletedProcess>`_. Among other things, this object contains the following useful attributes:

* ``returncode``: The integer exit status of the command. Typically, an exit status of ``0`` indicates success.
* ``stdout``: The complete standard output from the command, if any. This attribute will only be populated if capturing output, as described below.
* ``stderr``: The complete error output from the command, if any. This attribute will only be populated if capturing output, as described below.

Sometimes it is useful to capture the output a command would typically generate. This may be because it is never relevant to display it, or in order to support a low-verbosity mode for the task, or so the task can process the output before displaying or otherwise acting on it. This is supported by passing the optional ``capture=True`` flag when calling the method:

.. code-block:: python

    result = self.cli('echo "hello"', capture=True)
    do_something_with_output(result.stdout)

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

            # Build assets if a task exists to do so
            try:
                build_proxy = self.get_task_proxy('build', '--all')
            except TaskDefinitionError:
                pass
            else:
                self.stdout.write('Building all assets', style='label')
                build_proxy.execute()

            # ...

As shown in the example above, arguments to the other task should be passed as individual strings. Another example is:

.. code-block:: python

    proxy = self.get_task_proxy('test', '-v', '2', 'myapp.tests', '--keepdb')

Depending on the type of task being called (string, function, or class based), common arguments of the source task will be propagated automatically, including (where relevant): ``--stdout``, ``--stderr``, ``--no-color``, and ``-v/--verbosity``.

Requesting user input
---------------------

Tasks often need to ask the user for input, for a variety of reasons. If they only require a short string, such as a name or a yes/no confirmation, Python's ``input()`` builtin works nicely. But if long-form text is required, class-based tasks offer the :meth:`~Task.long_input` method, which opens the system's default editor to request user input. The method returns the content the user enters into the editor.

Using :meth:`~Task.long_input` also allows a default value to be provided, using the ``default`` argument. The editor will open with the default value already entered, and the user can accept it, modify it, or completely replace it as necessary.

If the system's default editor is not desired, a specific editor can be specified using the ``editor`` argument. The value should be the name of the command line program used to launch the editor, e.g. ``'nano'`` or ``'vi'``. The given program must be able to accept a filename as a command line argument to open/edit a provided file.

If the ``editor`` argument is not given, and a system default editor cannot be determined (after checking the environment variables ``VISUAL`` and ``EDITOR``), the editor specified by :attr:`~Task.default_long_input_editor` is used. This defaults to ``'nano'``, but can be overridden on subclasses.

Halting execution
-----------------

If an error occurs and the execution of the task should be interrupted, simply raise :exc:`~jogger.exceptions.TaskError`. Any message passed to the exception will be written to the configured ``stderr`` stream and the task will be halted.


.. _class_tasks_settings:

Using settings
==============

If your project :doc:`defines a config file <config>`, and it contains a section for the task being executed, the settings within that section are available to a class-based task via the :attr:`~Task.settings` attribute. This allows common tasks to be shared among multiple projects, while still allowing them to be configured as necessary for each one.

Re-working the above example of the ``test`` task so that the use of `coverage.py <https://coverage.readthedocs.io/>`_ is based on a project-level setting might look like:

.. tab:: pyproject.toml
    
    .. code-block:: toml
        
        [tool.jogger.test]
        coverage = true

.. tab:: setup.cfg
    
    .. code-block:: ini
        
        [jogger:test]
        coverage = true

.. code-block:: python
    
    # jog.py
    from jogger.tasks import Task
    
    
    class TestTask(Task):
        
        help = 'Run the Django test suite, optionally with coverage.py.'
        
        def handle(self, *args, **options):
            
            command = 'python manage.py test'
            
            if self.settings.get('coverage', True):
                command = f'coverage run {command}'
            
            self.cli(command)
    
    tasks = {
        'test': TestTask
    }


.. _class_tasks_args:

Custom arguments
================

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
=================

In addition to supporting custom arguments, all :class:`Task` subclasses accept the following default arguments:

* ``-h``/``--help``: Display the task's help output. The description will be pulled from the class's :attr:`~Task.help` attribute. If the class does not provide a description, the task's signature and argument list will be displayed, but it will not include any descriptive text. Custom arguments can use the ``help`` `argument <https://docs.python.org/3/library/argparse.html#help>`_ of ``parser.add_argument()`` to provide a useful description.
* ``--no-color``: Prevents colourisation of output (e.g. if the task makes use of :ref:`styled output <output_styling>`).
* ``--stderr``: The output stream to use for error messages. Defaults to the system's ``stderr`` stream. Can be redirected, e.g. to a file: ``jog test --stderr /home/myuser/logs/test/err.log``.
* ``--stdout``: The output stream to use for general messages. Defaults to the system's ``stdout`` stream. Can be redirected, e.g. to a file: ``jog test --stdout /home/myuser/logs/test/out.log``.
* ``-v``/``--verbosity``: An integer between ``0`` and ``3`` (inclusive). Defaults to ``1``. A generic verbosity level, available to be used (or not) by individual tasks as they see fit.

.. note::

    Only output generated by the :attr:`~Task.stdout` and :attr:`~Task.stderr` attributes is affected by the ``--no-color`` option. Any output generated by a command executed via :meth:`~Task.cli` will NOT be affected. If the command accepts its own argument for suppressing coloured output, it should be incorporated into the provided command string if necessary.
