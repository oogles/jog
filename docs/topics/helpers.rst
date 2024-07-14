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
