import os
import sys

from .base import Task, TaskError


def configure_django(project_dir, settings_module):
    """
    Configure the Django environment for the current process.
    
    This function is intended for use in scripts that need to run Django
    code outside of a normal Django context, e.g. function-based or class-based
    jogger tasks.
    
    :param project_dir: The absolute path to the project directory.
    :param settings_module: The dotted path to the Django settings module to
        use, relative to ``project_dir``.
    :return: The configured and imported Django settings object.
    """
    
    #
    # 1) Ensure the project directory is present on Python's path,
    #    so that imports of project modules are supported
    # 2) Tell Django which settings module to use via the relevant
    #    environment variable
    # 3) Manually set up the Django environment
    #
    
    sys.path.insert(0, project_dir)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    
    import django
    django.setup()
    
    from django.conf import settings
    
    return settings


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
        
        # `jogger` tasks are executed outside a normal Django context, so
        # manually configure Django before running the task handler
        self.django_settings = configure_django(self.conf.project_dir, self.django_settings_module)
        
        return super().execute()
