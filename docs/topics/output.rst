==================
Controlling Output
==================

.. currentmodule:: jogger.utils.output

Tasks that are defined as either :doc:`functions <func_tasks>` or :doc:`classes <class_tasks>` have access to ``stdout`` and ``stderr`` objects that they can use to display output from the task. For example:

.. code-block:: python

    # Function-based task
    def my_task(settings, stdout, stderr):

        stdout.write('Hello, World!')

    # Class-based task
    class MyTask(Task):

        def handle(self, *args, **options):

            self.stdout.write('Hello, World!')

Using these objects is preferred over more direct methods - such as ``print()`` - for several reasons.

The first is consistency. By default, these ``stdout``/``stderr`` objects are light wrappers around the system's standard output and error streams, respectively. But they can represent other output streams as well - such as a log file. By using the provided proxy objects, a task can write its output without concerning itself over the nature of the stream it is writing to, and with the knowledge that the output will be redirected if and when it is appropriate.

Another reason is the helpers they provide for *styling* the output, to improve readability or highlight important messages. This is discussed in depth below.


.. _output_styling:

Styling
=======

Applying styles to whole messages
---------------------------------

The simplest way to style the output from a task is to use the ``style`` argument to the ``write()`` method of the ``stdout`` and ``stderr`` output proxies:

.. code-block:: python

    # Function-based task
    def my_task(settings, stdout, stderr):

        stdout.write('Hello, World!', style='success')

    # Class-based task
    class MyTask(Task):

        def handle(self, *args, **options):

            self.stderr.write('Uh-oh', style='warning')

The value provided to the ``style`` argument must match a supported style "role". The following roles are supported:

* ``'normal'``: plain text, no specific styles applied
* ``'success'``: bold green text
* ``'error'``: bold red text
* ``'warning'``: bold yellow text
* ``'info'``: bold text
* ``'debug'``: bold magenta text
* ``'heading'``: bold cyan text
* ``'label'``: bold text

While simple to use, the ``style`` argument has some downsides: it styles the *entire* string passed to ``write()``, and the styles it uses for each role are fixed. What if you would prefer your error messages to be purple, and blink?

.. note::

    Unless the ``style`` argument is explicitly used, calls to ``write()`` on the ``stderr`` proxy will *assume* the ``'error'`` role.

Applying styles to portions of messages
---------------------------------------

Sometimes you just want a segment of an output message to have a particular style, e.g. be bold or use a particular colour. This is possible through the :class:`Styler` class. An instance of :class:`Styler` exists on the ``stdout`` and ``stderr`` proxy objects, and it is what powers the ``style`` argument of the ``write()`` method. It can be accessed directly for more flexibility. For tasks :doc:`defined as classes <class_tasks>`, there is even a shortcut to it: the :attr:`~jogger.tasks.base.Task.styler` attribute.

.. code-block:: python

    # Function-based task
    def my_task(settings, stdout, stderr):

        name = stdout.styler.label('World')
        stdout.write(f'Hello, {name}!')

    # Class-based task
    class MyTask(Task):

        def handle(self, *args, **options):

            name = self.styler.label('World')
            self.stdout.write(f'Hello, {name}!')

These instances of the :class:`Styler` class have methods corresponding to each of the default roles described above: ``success()``, ``error()``, ``warning()``, ``info()``, ``debug()``, ``heading()``, and ``label()``.

While this provides much more flexibility in applying styles, it is still limited to the default style roles.

Customising styles
------------------

Using the default roles are convenient, but they may not always be suitable. To customise the available styles, there are two options: style messages manually, or create a custom style palette.

For simple, one-off styles, it's easy to just apply the style manually. This can be done using the :meth:`~Styler.apply` method of the default :class:`Styler` instances already available:

.. code-block:: python

    # Function-based task
    def my_task(settings, stdout, stderr):

        name = stdout.styler.apply('World', fg='blue', options=('bold', ))
        stdout.write(f'Hello, {name}!')

    # Class-based task
    class MyTask(Task):

        def handle(self, *args, **options):

            error = self.styler.apply('Uh-oh', fg='magenta', options=('bold', 'blink'))
            self.stderr.write(error)

See the :meth:`~Styler.apply` method for details on its accepted arguments and the supported options for each.

If you have a range of commonly-used styles that are repeated throughout your tasks, you might want to create a custom ``Styler`` subclass that uses its own style palette:

.. code-block:: python

    from jogger.utils.output import Styler


    class MyStyler(Styler):

        PALETTE = {
            'success': {'fg': 'green', 'options': ('bold', )},
            'error': {'fg': 'magenta', 'options': ('bold', 'blink')},
            'label': {'fg': 'blue'},
        }

A custom styler can then be used in a similar fashion to the default ones:

.. code-block:: python

    # Function-based task
    def my_task(settings, stdout, stderr):

        my_styler = MyStyler()

        name = my_styler.label('World')
        stdout.write(f'Hello, {name}!')

    # Class-based task
    class MyTask(Task):

        def handle(self, *args, **options):

            my_styler = MyStyler(no_color=options['no_color'])

            error = my_styler.error('Uh-oh')
            self.stderr.write(error)

``no-color`` environments
-------------------------

:class:`Styler` instances, whether the default ones or when using a custom subclass, will automatically detect when the output stream doesn't support styling and silently ignore it. This allows a common API to be used regardless of the nature of the output stream being written to. Examples of such streams include command line environments that don't support ANSI graphics codes, or when redirecting output to a file.

However, the ``--no-color`` default command line argument available to function-based and class-based tasks can be used to *force* styling to be ignored and all output be in plain text. The default ``Styler`` instances respect this argument automatically, but if creating an instance manually (e.g. when using a custom subclass), you have the responsibility of making the styler aware of this preference. This is done using the ``no_color`` argument to the :class:`Styler` constructor. You may have noticed it used in the above example of using a custom styler in a class-based task:

.. code-block:: python

    class MyTask(Task):

        def handle(self, *args, **options):

            my_styler = MyStyler(no_color=options['no_color'])
