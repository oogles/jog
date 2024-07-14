=====
Tasks
=====

.. autoclass:: jogger.tasks.base.Task

    .. attribute:: help

        The help text for this task, output when the task is invoked with ``-h``/``--help``.

    .. attribute:: default_long_input_editor

        The editor program to launch when invoking the :meth:`~Task.long_input` method and no system default editor can be determined. Defaults to ``'nano'``.

    .. attribute:: settings

        The dictionary containing any settings for this task that were included in a supported :doc:`config file <../topics/config>`.

    .. attribute:: project_dir

        The absolute path to the project directory, as determined by the location of the ``jog.py`` file.

    .. attribute:: stdout

        A proxy for the stream to write general messages to, offering more control over output from the task. See :doc:`../topics/output` for details on writing to output proxies. Defaults to the system's ``stdout`` stream, but can be changed using the ``--stdout`` argument, e.g.:

        .. code-block:: bash

            jog test --stdout /home/myuser/logs/test/out.log

    .. attribute:: stderr

        A proxy for the stream to write error messages to, offering more control over output from the task. See :doc:`../topics/output` for details on writing to output proxies. Defaults to the system's ``stderr`` stream, but can be changed using the ``--stderr`` argument, e.g.:

        .. code-block:: bash

            jog test --stderr /home/myuser/logs/test/err.log

    .. attribute:: styler

        A default :class:`~jogger.utils.output.Styler` instance, available as a helper for styling task output.

    .. automethod:: add_arguments
    .. automethod:: handle
    .. automethod:: cli
    .. automethod:: get_task_proxy
    .. automethod:: long_input


.. autoclass:: jogger.tasks.django.DjangoTask
    
    .. autoattribute:: django_settings_module
    .. autoattribute:: django_settings
