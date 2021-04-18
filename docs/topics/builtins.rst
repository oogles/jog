==============
Built-in Tasks
==============

``jogger`` ships with a handful of common commands. They are opinionated and geared toward Django projects, but do afford some level of configurability and will adapt their behaviour to a certain extent based on the presence (or lack thereof) of certain libraries. They may not be useful to all projects, but could provide an out-of-the-box solution to others.

The available tasks are described in detail below.


Using the built-ins
===================

All built-in tasks are :doc:`defined as classes <class_tasks>`. To use them, simply import the class into a ``jog.py`` file and assign them a name:

.. code-block:: python

    # jog.py
    from jogger.tasks import DocsTask, LintTask, TestTask


    tasks = {
        'test': TestTask,
        'lint': LintTask,
        'docs': DocsTask
    }

They can then be invoked via the ``jog`` command using the specified name, e.g. ``jog test``.


``LintTask``
============

Performs a number of "linting" operations to flag potential errors and style guide violations.

``LintTask`` makes use of the ``-v``/``--verbosity`` :ref:`default command line argument <class_tasks_default_args>` accepted by all class-based tasks, where specified below.

It includes the following steps:

1. Lint Python code using `flake8 <https://github.com/PyCQA/flake8>`_ and `isort <https://github.com/PyCQA/isort>`_. Both programs will obey their respective configuration files if they are located in standard locations, e.g. in a ``setup.cfg`` file. Specifically, the following commands are executed in the project root directory (determined as the directory containing ``jog.py``):

    * ``flake8 .``
    * ``isort --check-only --diff .``

  This step can be skipped by default by using the ``python = false`` setting. It will also be skipped automatically if neither ``flake8`` or ``isort`` are installed.

2. Run FABLE (Find All Bad Line Endings), a custom script to ensure all relevant project files use consistent line endings. By default, it:

    * Flags files not using ``LF`` line endings. This is configurable via the ``fable_good_endings`` setting.
    * Ignores files larger than 1MB. This is configurable (in bytes) via the ``fable_max_filesize`` setting.
    * Ignores a variety of irrelevant files, including ``.pyc`` files, PDFs, images, and everything in ``.git`` and ``__pycache__`` directories. Additional files can be ignored using the ``fable_exclude`` setting.

  This step can be skipped by default by using the ``fable = false`` setting.

3. Check Python code for potential security issues using the static analysis tool `bandit <https://github.com/PyCQA/bandit>`_. Specifically, one of the following commands is executed in the project root directory (determined as the directory containing ``jog.py``):

    * ``bandit . -r -q`` (default - use "quiet" mode, only generating output if an issue is found)
    * ``bandit . -r`` (at verbosity level ``2``)
    * ``bandit . -r -v`` (at verbosity level ``3`` - use "verbose" mode)

  The program will obey a ``.bandit`` configuration file if found, but excludes can also be added via the task setting ``bandit_exclude``.

  This step can be skipped by default by using the ``bandit = false`` setting. It will also be skipped automatically if ``bandit`` is not installed.

4. Perform a "dry run" of Django's ``makemigrations`` management command, ensuring no migrations get missed.

  This step can be skipped by default by using the ``migrations = false`` setting. It will also be skipped automatically if Django is not installed.

Arguments
---------

``LintTask`` accepts the following arguments:

* ``-p``/``--python``: Only run the Python linting step.
* ``-f``/``--fable``: Only run the FABLE step.
* ``-b``/``--bandit``: Only run the ``bandit`` security scan step.
* ``-m``/``--migrations``: Only run the migration check step.

These arguments can be chained to specify any subset of these options, e.g.::

    jog lint -pf

Settings
--------

The following is an example config file section containing all available config options and examples of their use. It assumes ``LintTask`` has been given the name "lint" in the ``jog.py`` file.

.. code-block:: ini

    [jogger:lint]
    python = false      # exclude the Python linting step by default
    fable = false       # exclude the FABLE step by default
    bandit = false      # exclude the bandit step by default
    migrations = false  # exclude the migration check step by default

    fable_good_endings = CRLF  # one of: LF, CR, CRLF (default: LF)
    fable_max_filesize = 5242880  # 5MB, in bytes (default: 1MB)
    fable_exclude =
        ./docs/_build

    bandit_exclude =
        tests


``TestTask``
============

Runs the Django ``manage.py test`` command. Additionally, if `coverage.py <https://coverage.readthedocs.io/en/stable/>`_ is detected, it will perform code coverage analysis, print an on-screen summary, and generate a fully detailed HTML report.

``TestTask`` makes use of the ``-v``/``--verbosity`` :ref:`default command line argument <class_tasks_default_args>` accepted by all class-based tasks, as outlined below.

It uses the following coverage.py commands:

* ``coverage run --branch`` to execute the test suite with code coverage. Some additional arguments may be passed based on arguments passed to ``TestTask`` itself. See below for details on accepted arguments.
* ``coverage report --skip-covered`` to generate the on-screen summary report if the verbosity level is ``1`` (the default).
* ``coverage report`` to generate the on-screen summary report if the verbosity level is ``2`` or more.
* ``coverage html`` to generate the detailed HTML report.

.. note::

    The on-screen summary report will be skipped entirely if the verbosity level is less than ``1``.

``TestTask`` accepts several of its own arguments, detailed below, but also passes any additional arguments through to the underlying ``manage.py test`` command. Assuming the task has been given the name "test" in ``jog.py``, this means you can do any of the following::

    jog test
    jog test myapp
    jog test myapp.tests.MyTestCase.test_my_thing
    jog test myapp --settings=test_settings
    jog test myapp --keepdb

.. _builtins-test-quick:

Quick tests
-----------

The task can be run in a "quick" mode by passing the ``--quick`` or ``-q`` flags::

    jog test -q

This mode skips any code coverage analysis and reporting, just running the test suite. By default, it also passes the ``--parallel`` argument to the ``manage.py test`` command. Since this argument is not always desirable, this behaviour can be disabled using the ``quick_parallel`` setting. Assuming a task name of "test":

.. code-block:: ini

    [jogger:test]
    quick_parallel = false

See the `Django documentation <https://docs.djangoproject.com/en/stable/ref/django-admin/#cmdoption-test-parallel>`_ on the ``--parallel`` argument for more information.

.. _builtins-test-accumulating:

Accumulating results
--------------------

``TestTask`` allows running multiple commands to cover different areas of the test suite while accumulating code coverage data and generating cohesive reports. For example, the following tests two different apps, one using a custom settings file:

.. code-block:: bash

    jog test -a app1
    jog test -a app2 --settings=test_settings
    jog test --report

.. _builtins-test-noise:

Reducing coverage noise
-----------------------

Sometimes, especially when running a subset of the full test suite, the coverage reports can contain a lot of noise in the form of files with low coverage scores because they are outside the scope of the tests. The presence of these extra files can make it more difficult to spot the missing coverage you're actually looking for.

There are a number of ``coverage.py`` settings available to reduce this noise, as `covered in the documentation <https://coverage.readthedocs.io/en/stable/source.html>`_. ``TestTask`` supports the ``--source`` command-line argument via its own ``--src`` argument, but does not accept ``--include``/``--omit`` arguments. All options can still be set up via a suitable configuration file.

If running a subset of the test suite, i.e. passing an explicit test path or paths, ``TestTask`` will make a best-guess at an explicit ``--source`` value to use. It won't always be perfect, but can at least help limit the number of completely unrelated files included in the coverage reports. The following describes how the value is chosen:

.. list-table::
    :header-rows: 1

    * - Command
      - ``--source`` value
    * - ``jog test myproject``
      - ``myproject``
    * - ``jog test myproject.myapp``
      - ``myproject.myapp``
    * - ``jog test myproject.myapp.tests``
      - ``myproject.myapp``
    * - ``jog test myproject.myapp.tests.test_things.MyThingTestCase``
      - ``myproject.myapp``
    * - ``jog test myproject.myapp1 myproject.myapp2``
      - ``myproject.myapp1,myproject.myapp2``

If no explicit test paths are passed, no attempt is made to automatically include the ``--source`` argument. If the ``TestTask`` argument ``--src`` is provided, it takes precedence.

Use with virtual machines
-------------------------

If ``TestTask`` generates a HTML coverage report, it also prints a ``file://`` URL to the index page of that report, allowing it to be quickly and easily opened for immediate viewing. However, if the task is running in a virtual machine or other virtual environment with its own file system, the ``file://`` link displayed will likely not be openable on the host machine.

The ``report_path_swap`` setting can be used to correct this. As long as the generated document also exists on the host (i.e. it is generated on a path that is kept in sync between the host and guest file systems), this setting allows replacing the guest-specific portion of the ``file://`` URL with the equivalent host-specific value. It should use ``>`` as the delimiter to map the guest value to the host value:

.. code-block:: ini

    [jogger:test]
    report_path_swap = /opt/app/src/ > /home/username/projectname/

.. tip::

    If multiple developers are working on a project, this setting will rarely be the same for everyone. This makes it a good candidate for an :doc:`environment-specific config file <config>`.

Arguments
---------

``TestTask`` accepts the following arguments:

* ``-q``/``--quick``: Run a "quick" variant of the task: coverage analysis is skipped and the ``--parallel`` argument is passed to ``manage.py test``. See :ref:`builtins-test-quick`.
* ``-a``: Accumulate coverage data across multiple runs (passed as the ``-a`` argument to the ``coverage run`` command). No coverage reports will be run automatically. See :ref:`builtins-test-accumulating`.
* ``--src``: The source to measure the coverage of (passed as the ``--source`` argument to the ``coverage run`` command). See :ref:`builtins-test-noise`.
* ``--report``: Skip the test suite and just generate the coverage reports. Useful to review previous results or if using ``-a`` to accumulate results.
* ``--no-html``: Skip generating the detailed HTML code coverage report. The on-screen summary report will still be displayed.
* ``--no-cover``: Run the test suite only. Skip all code coverage analysis and do not generate any coverage reports.

.. note::

    All arguments to ``TestTask`` itself must be listed *before* any test paths or other arguments intended for the underlying ``manage.py test`` command.

Settings
--------

The following is an example config file section containing all available config options and examples of their use. It assumes ``TestTask`` has been given the name "test" in the ``jog.py`` file.

.. code-block:: ini

    [jogger:test]
    quick_parallel = false  # default: true
    report_path_swap = /opt/app/src/ > /home/username/projectname/


``DocsTask``
============

Builds project documentation using `Sphinx <https://www.sphinx-doc.org/>`_.

The task assumes a documentation directory configured via `sphinx-quickstart <https://www.sphinx-doc.org/en/master/usage/quickstart.html>`_. It looks for a ``docs/`` directory within the project root directory (determined by the location of ``jog.py``). Within that directory, it runs either:

* ``make html`` (default)
* ``make clean && make html`` if the ``-f``/``--full`` flag is provided

Use with virtual machines
-------------------------

``DocsTask`` prints a ``file://`` URL to the index page of the documentation it generates, allowing it to be quickly and easily opened for immediate viewing. However, if the task is running in a virtual machine or other virtual environment with its own file system, the ``file://`` link displayed will likely not be openable on the host machine.

The ``index_path_swap`` setting can be used to correct this. As long as the generated document also exists on the host (i.e. it is generated on a path that is kept in sync between the host and guest file systems), this setting allows replacing the guest-specific portion of the ``file://`` URL with the equivalent host-specific value. It should use ``>`` as the delimiter to map the guest value to the host value:

.. code-block:: ini

    [jogger:docs]
    index_path_swap = /opt/app/src/ > /home/username/projectname/

.. tip::

    If multiple developers are working on a project, this setting will rarely be the same for everyone. This makes it a good candidate for an :doc:`environment-specific config file <config>`.

Arguments
---------

``DocsTask`` accepts the following arguments:

* ``-f``/``--full``: Remove previously built documentation before rebuilding all pages from scratch.
* ``-l``/``--link``: Skip building the documentation and just output the link to the previously built ``index.html`` file (if any).

Settings
--------

The following is an example config file section containing all available config options and examples of their use. It assumes ``DocsTask`` has been given the name "docs" in the ``jog.py`` file.

.. code-block:: ini

    [jogger:docs]
    index_path_swap = /opt/app/src/ > /home/username/projectname/
