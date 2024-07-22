=======
Helpers
=======

In addition to the fully-functional :doc:`built-in tasks <builtins>` provided by ``jogger``, it also includes some helpers to assist in writing custom tasks.


``DjangoTask``
==============

A replacement for the default :class:`~jogger.tasks.base.Task` parent for a :doc:`class-based task <class_tasks>`, :class:`~jogger.tasks.django.DjangoTask` is designed for tasks that require a configured Django environment in order to run. For example, tasks that need to import and query Django models.

In order to configure the Django environment, :class:`~jogger.tasks.django.DjangoTask` needs to know the path to the Django settings module. This can be provided using the :attr:`~jogger.tasks.django.DjangoTask.django_settings_module` class attribute, which should be set to the dotted path of the settings module, relative to the project directory, e.g. ``'my_project.settings'``.

:class:`~jogger.tasks.django.DjangoTask` will automatically import the configured settings module and make it available as the :attr:`~jogger.tasks.django.DjangoTask.django_settings` instance attribute. This avoids the need to manually import the settings module, as a standard module-level import will not work. Note that any additional imports from the Django project should be made within the task's methods, not at the module level.

.. code-block:: python
    
    from jogger.tasks import DjangoTask
    
    
    class MyTask(DjangoTask):
        
        django_settings_module = 'myproject.settings'
        
        def handle(self, *args, **options):
            
            from myproject.myapp.models import MyModel
            
            if not self.django_settings.DEBUG:
                raise TaskError('Can only be run in DEBUG mode.')
            
            # Do something with MyModel


``configure_django``
====================

A function that can be called by tasks that require a configured Django environment in order to run. For example, tasks that need to import and query Django models. While :class:`~jogger.tasks.django.DjangoTask` handles this requirement for class-based tasks, :func:`~jogger.tasks.django.configure_django` can be used by function-based tasks or any other scripts.

In order to configure the Django environment, :func:`~jogger.tasks.django.configure_django` needs to know the path to both the project directory and the Django settings module, which it takes as arguments. It returns the configured Django settings object, so that Django settings can be accessed without needing to subsequently import ``django.conf.settings``.

Note that any imports from the Django project should be made after calling this function, not at the module level.

.. code-block:: python
    
    import os
    
    from jogger.tasks import configure_django
    
    
    def my_task(settings, stdout, stderr):
        
        project_dir = os.path.dirname(os.path.abspath(__file__))
        django_settings = configure_django(project_dir, 'myproject.settings')
        
        from myproject.myapp.models import MyModel
        
        if not django_settings.DEBUG:
            raise TaskError('Can only be run in DEBUG mode.')
        
        # Do something with MyModel
