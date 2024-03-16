============
Config Files
============

Task-specific settings can be defined in several supported config files. These settings can be accessed by individual tasks so they may adapt their behaviour accordingly. This allows common tasks to be shared among multiple projects, while still allowing each project a certain level of control over the tasks' behaviour.

``jogger`` supports two "levels" of config files: project and environment. The project-level config file is intended to be committed to source control, and contains settings that are common to all environments. The environment-level config file is intended to be kept out of source control, and contains settings that are specific to a particular environment. Settings in an environment-level config file will override any settings of the same name in the project-level config file.

By default, ``jogger`` will look for the following config files, in the listed order. For each level, the first file containing settings for a given task will be used, and ``jogger`` will stop looking for further files at that level. In all cases, the files must reside in the same directory as the ``jog.py`` file.

* Project level: ``pyproject.toml``, ``setup.cfg``
* Environment level: ``joggerenv.toml``, ``joggerenv.cfg``

.. note::

    The project-level config files supported by ``jogger`` are commonly used to configure other Python tools, so any given project may already have one. Settings tables for ``jogger`` tasks can simply be included among any existing ones.


Defining task settings
======================

The syntax for defining task settings varies slightly between ``*.toml`` and ``*.cfg`` config files, which use TOML and INI file structures, respectively. But in both cases, the settings for any ``jogger`` task that requires configuration are listed in a table/section named for that task. The settings are then defined as key-value pairs below that.

The specific table/section name depends on the file, in line with its respective convention. Below, the same sample config file (using an example configuration of a couple of the ``jogger`` :doc:`built-in tasks <builtins>`) is shown in each of the supported config files.

``pyproject.toml``
------------------

In line with the `PEP 518 <https://peps.python.org/pep-0518/>`_ specification, the ``[tool.jogger]`` table is used to encapsulate any ``jogger``-related settings, with task-specific tables nested below that.

.. code-block:: toml

    [tool.jogger.lint]
    migrations = false
    fable_exclude = [
        "./docs/_build"
    ]

    [tool.jogger.test]
    quick_parallel = false

``joggerenv.toml``
------------------

Being a ``jogger``-specific file, the task name alone is used as the table name.

.. code-block:: toml

    [lint]
    migrations = false
    fable_exclude = [
        "./docs/_build"
    ]

    [test]
    quick_parallel = false

``setup.cfg`` / ``joggerenv.cfg``
---------------------------------

Both ``*.cfg`` files use the same section naming convention.

.. code-block:: ini

    [jogger:lint]
    migrations = false
    fable_exclude =
        ./docs/_build

    [jogger:test]
    quick_parallel = false


.. _config_task_settings:

Accessing task settings
=======================

Only tasks defined as either :doc:`functions <func_tasks>` or :doc:`classes <class_tasks>` can access settings from a config file. Tasks defined as functions receive a ``settings`` dictionary as the :ref:`first argument to the function <func_tasks_settings>`, while tasks defined as classes :ref:`have an attribute <class_tasks_settings>` containing the same ``settings`` dictionary.

.. versionchanged:: 2.0
    Previous versions of ``jogger`` provided the ``settings`` object as a ``SectionProxy`` object as returned by Python's ``ConfigParser`` class. After the introduction of TOML support for config files, this was changed to provide ``settings`` as a dictionary. This provides a consistent interface to the settings regardless of a user's chosen config file format. Some ``jogger`` tasks written for previous versions may experience compatibility issues if they use ``SectionProxy``-specific methods, such as ``getint()``, ``getfloat()``, or ``getboolean()``.

Data types within the ``settings`` object may differ depending on which config file format a user has chosen. TOML files are type-aware, but INI files are not. Thus, settings read from a TOML file will be returned in native data types such as integers, floats, booleans, and lists. Meanwhile, settings read from an INI file will all be returned as strings.

In an effort to bring some consistency to the ``settings`` interface, ``jogger`` does some basic type casting on settings read from INI files, including:

* Booleans defined as ``true`` or ``false`` will be cast to the Python ``bool`` type.
* Multiline values will be cast to Python ``list`` objects, with each line of the value becoming an element in the list. Items are not type cast, so all elements will be strings.

No attempt is made to cast numbers.

These inconsistencies are important to keep in mind when accessing settings from the ``settings`` object. For instance, numbers should always be cast with ``int()`` or ``float()`` in the event that they are read from an INI file. E.g.:

.. code-block:: python
    
    max_count = int(settings['max_count'])
