import sys
from argparse import ArgumentParser, FileType

from ..output import OutputWrapper, Styler

#
# The classes herein are heavily based on Django's management command
# infrastructure, found in ``django.core.management.base``, though greatly
# simplified and without any of the Django machinery.
#


class TaskError(Exception):
    """
    Used to indicate problem during the execution of a task, yielding a nicely
    printed error message in the appropriate output stream (e.g. ``stderr``).
    """
    
    pass


class Task:
    """
    An advanced ``jogger`` task capable of defining its own arguments and
    redirecting the ``stdout`` and ``stderr`` output streams.
    """
    
    help = ''
    
    def __init__(self, name, argv):
        
        parser = self.create_parser(name)
        options = parser.parse_args(argv)
        
        kwargs = vars(options)
        
        no_color = kwargs['no_color']
        self.stdout = OutputWrapper(kwargs['stdout'], no_color=no_color)
        self.stderr = OutputWrapper(kwargs['stderr'], no_color=no_color, default_style='error')
        self.styler = self.stdout.styler
        
        self.args = kwargs.pop('args', ())
        self.kwargs = kwargs
    
    def create_parser(self, name):
        """
        Create and return the ``ArgumentParser`` which will be used to parse
        the arguments to this task.
        """
        
        parser = ArgumentParser(
            prog=name,
            description=self.help or None
        )
        
        parser.add_argument(
            '-v', '--verbosity',
            default=1,
            type=int,
            choices=[0, 1, 2, 3],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output'
        )
        
        parser.add_argument(
            '--stdout',
            nargs='?',
            type=FileType('w'),
            default=sys.stdout
        )
        
        parser.add_argument(
            '--stderr',
            nargs='?',
            type=FileType('w'),
            default=sys.stderr
        )
        
        parser.add_argument(
            '--no-color',
            action='store_true',
            help="Don't colourise the command output.",
        )
        
        self.add_arguments(parser)
        
        return parser
    
    def add_arguments(self, parser):
        """
        Hook for subclassed tasks to add custom arguments.
        """
        
        pass
    
    def execute(self):
        """
        Execute this task. Intercept any raised ``TaskError`` and print it
        sensibly to ``stderr``. Allow all other exceptions to raise as per usual.
        """
        
        try:
            self.handle(*self.args, **self.kwargs)
        except Exception as e:
            if not isinstance(e, TaskError):
                raise
            
            self.stderr.write(f'{e.__class__.__name__}: {e}')
            sys.exit(1)
    
    def handle(self, *args, **kwargs):
        """
        The actual logic of the task. Subclasses must implement this method.
        """
        
        raise NotImplementedError('Subclasses of Task must provide a handle() method.')
