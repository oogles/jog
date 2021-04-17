===========
Config File
===========

Task-specific settings can be defined in one or both of two different config files. These settings can be accessed by individual tasks so they may adapt their behaviour accordingly. This allows common tasks to be shared among multiple projects, while still allowing each project a certain level of control over the tasks' behaviour.

By default, ``jogger`` will look for config files named ``setup.cfg`` and ``joggerenv.cfg``. Both must reside in the same directory as the ``jog.py`` file.

The ``setup.cfg`` file is the main project-based config file for ``jogger``. The ``joggerenv.cfg`` file is designed for environment-specific overrides to the settings in ``setup.cfg``, should such overrides be necessary. Unlike ``setup.cfg``, ``joggerenv.cfg`` would typically not be committed to source control, allowing individual environments to configure things specific to them.

.. note::

    The ``setup.cfg`` file is commonly used to configure programs per-project, so any given project may already have one. Settings sections for ``jogger`` can simply be included among any existing ones.

Defining task settings
======================

Both config files use the INI file structure, which breaks the file up into sections for each program. Each ``jogger`` task will have its own section. The following is a sample config file using an example configuration of a couple of the ``jogger`` :doc:`built-in tasks <builtins>`:

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

Only tasks defined as either :doc:`functions <func_tasks>` or :doc:`classes <class_tasks>` can access settings from the config file. Tasks defined as functions receive a ``settings`` object as the :ref:`first argument to the function <func_tasks_settings>`, while tasks defined as classes :ref:`have an attribute <class_tasks_settings>` containing the same ``settings`` object.

In both cases, the ``settings`` object is a *dictionary-like* collection of the settings listed in the config file for that task. Importantly though, it is **not** a true dictionary.

Specifically, it is a ``SectionProxy`` object as returned by Python's ``ConfigParser`` class (see the `configparser library documentation <https://docs.python.org/3/library/configparser.html>`_ for details). Importantly, all values are read from the config file *as strings*. Accessing them via normal dictionary-like means may give you an unexpected data type, e.g. using ``settings['max_count']`` or ``settings.get('enable_feature')``. However, helper methods exist for returning specific data types, e.g. ``settings.getint('max_count')`` or ``settings.getboolean('enable_feature')``. See `the documentation <https://docs.python.org/3/library/configparser.html#supported-datatypes>`_ for more details.

If both config files are used, and both contain an entry for the same setting, the entry in the environment-specific ``joggerenv.cfg`` will take precedence over the entry in ``setup.cfg``.
