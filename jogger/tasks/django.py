import os
import sys

from .base import Task, TaskError


class DjangoTask(Task):
    """
    A Task that requires a configured Django environment in order to run.
    Such task classes require that the ``django_settings_module`` attribute
    be specified, naming the Django settings module to use. E.g.::
    
        class MyDjangoTask(DjangoTask):
            
            django_settings_module = 'my_project.settings'
    
    The configured Django settings object is available as ``self.django_settings``,
    avoiding the need to import ``django.conf.settings`` manually (as a standard
    module-level import would not work).
    """
    
    #: The Django settings module to use when running the task.
    django_settings_module = None
    
    def __init__(self, *args, **kwargs):
        
        if not self.django_settings_module:
            raise TaskError(f'{self.__class__.__name__} must specify django_settings_module.')
        
        #: The configured and imported Django settings object.
        self.django_settings = None
        
        super().__init__(*args, **kwargs)
    
    def execute(self):
        
        #
        # `jogger` tasks are executed outside a normal Django context, so
        # before running the task handler:
        # 1) Ensure the project directory is present on Python's path,
        #    so that imports of project modules are supported
        # 2) Tell Django which settings module to use via the relevant
        #    environment variable
        # 3) Manually set up the Django environment
        #
        
        sys.path.insert(0, self.conf.project_dir)
        
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', self.django_settings_module)
        
        import django
        django.setup()
        
        from django.conf import settings
        
        self.django_settings = settings
        
        return super().execute()
