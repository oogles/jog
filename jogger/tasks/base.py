import argparse
import os
import re
import subprocess
import sys
from inspect import cleandoc

from jogger.exceptions import TaskDefinitionError, TaskError
from jogger.utils.input import get_task_settings, get_tasks
from jogger.utils.output import OutputWrapper

TASK_NAME_RE = re.compile(r'^\w+$')

#
# The class-based "task" interface is heavily based on Django's management
# command infrastructure, found in ``django.core.management.base``, though
# greatly simplified and without any of the Django machinery.
#


class Task:
    """
    An advanced ``jogger`` task capable of defining its own arguments and
    redirecting the ``stdout`` and ``stderr`` output streams.
    """
    
    help = ''
    
    def __init__(self, name, settings, argv):
        
        self.settings = settings
        
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
        
        parser = argparse.ArgumentParser(
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
            type=argparse.FileType('w'),
            default=sys.stdout
        )
        
        parser.add_argument(
            '--stderr',
            nargs='?',
            type=argparse.FileType('w'),
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
        Custom tasks should override this method to add any custom command line
        arguments they require.
        """
        
        # Do nothing - just a hook for subclasses to add custom arguments
        pass
    
    def cli(self, cmd, no_output=False):
        """
        Run a command on the system's command line, in the context of the task's
        :attr:`~Task.stdout` and :attr:`~Task.stderr` output streams. If
        ``no_output`` is ``True``, suppress standard output (errors are still
        displayed).
        
        :param cmd: The command string to execute.
        :param no_output: ``True`` to suppress standard output from the command.
        :return: The command result object.
        """
        
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Display the output of the command unless instructed to suppress it
        if not no_output:
            self.stdout.write(result.stdout.decode('utf-8'), ending=None)
        
        # Display any errors regardless
        self.stderr.write(result.stderr.decode('utf-8'), ending=None)
        
        return result
    
    def _get_task_proxy_args(self, args):
        
        args = list(args)
        
        if '-v' not in args and '--verbosity' not in args:
            args.extend(('--verbosity', str(self.kwargs['verbosity'])))
        
        if '--stdout' not in args:
            stdout = self.kwargs['stdout'].name
            
            # Only pass the argument if not using the standard system output stream
            if stdout != '<stdout>':
                args.extend(('--stdout', stdout))
        
        if '--stderr' not in args:
            stderr = self.kwargs['stderr'].name
            
            # Only pass the argument if not using the standard system error stream
            if stderr != '<stderr>':
                args.extend(('--stderr', stderr))
        
        if '--no-color' not in args and self.kwargs['no_color']:
            args.append('--no-color')
        
        return args
    
    def get_task_proxy(self, task_name, *args):
        """
        Return an object representing the task matching the given name,
        configured with the given arguments, if any. This proxy object can be
        used to execute the task, regardless of whether it is defined as a
        string, function, or class::
        
            proxy = self.get_task_proxy('test')
            proxy.execute()
        
        Arguments only apply if the target task is defined as a class, and
        should be provided as individual strings, e.g.::
        
            proxy = get_task_proxy('test', '-v', '2', 'myapp.tests', '--keepdb')
        
        If the target task is defined as a class, common arguments of the
        source task will be propagated automatically, including:
        ``-v``/``--verbosity``, ``--stdout``, ``--stderr``, and ``--no-color``.
        
        :param task_name: The task name as a string.
        :param args: Extra task arguments, as individual strings.
        :return: The task proxy instance.
        """
        
        try:
            task = get_tasks()[task_name]
        except FileNotFoundError as e:
            raise TaskDefinitionError(e)
        except KeyError:
            raise TaskDefinitionError(f'Unknown task "{task_name}".')
        
        # Get the proxy instance, allow raising TaskDefinitionError if necessary
        proxy = TaskProxy('proxy.execute', task_name, task, self.stdout, self.stderr)
        
        if proxy.has_own_args:
            # The target task is also class-based, so common arguments of the
            # source task can be propagated, if not provided explicitly
            proxy.argv = self._get_task_proxy_args(args)
        elif args:
            raise TaskError('String- and function-based tasks do not accept arguments.')
        
        return proxy
    
    def execute(self):
        """
        Execute this task. Intercept any raised ``TaskError`` and print it
        sensibly to ``stderr``. Allow all other exceptions to raise as per usual.
        """
        
        try:
            self.handle(*self.args, **self.kwargs)
        except TaskError as e:
            self.stderr.write(str(e))
            sys.exit(1)
    
    def handle(self, *args, **kwargs):
        """
        The actual logic of the task. Subclasses must implement this method.
        """
        
        raise NotImplementedError('Subclasses of Task must provide a handle() method.')


class TaskProxy:
    """
    A helper for identifying and executing tasks of different types. It will
    identify and execute the following:
    
    - Strings: Executed as-is on the command line.
    - Callables (e.g. functions): Called with ``settings``, ``stdout``, and
        ``stderr`` as keyword arguments, allowing the task to alter its
        behaviour on a per-project basis and use separate output streams if
        necessary.
    - ``Task`` class objects: Instantiated with the remainder of the argument
        string (that not consumed by the ``jog`` program itself) and executed.
        Also has access to project-level settings and the ``stdout``/``stderr``
        output streams, in addition to accepting its own custom arguments.
    """
    
    def __init__(self, prog, name, task, stdout, stderr, argv=None):
        
        try:
            valid_name = TASK_NAME_RE.match(name)
        except TypeError:  # not a string
            valid_name = False
        
        if not valid_name:
            raise TaskDefinitionError(
                f'Task name "{name}" is not valid - must be a string '
                'containing alphanumeric characters and the underscore only.'
            )
        
        if isinstance(task, str):
            self.exec_mode = 'cli'
            self.executor = self.execute_string
            self.help_text = task
            self.has_own_args = False
        elif isinstance(task, type) and issubclass(task, Task):
            self.exec_mode = 'python'
            self.executor = self.execute_class
            self.help_text = task.help
            self.has_own_args = True
        elif callable(task):
            self.exec_mode = 'python'
            self.executor = self.execute_callable
            self.help_text = cleandoc(task.__doc__) if task.__doc__ else ''
            self.has_own_args = False
        else:
            raise TaskDefinitionError(f'Unrecognised task format for "{name}".')
        
        self.prog = f'{prog} {name}'
        self.name = name
        
        self.task = task
        self.argv = argv
        
        self.stdout = stdout
        self.stderr = stderr
    
    def output_help_line(self):
        
        stdout = self.stdout
        styler = stdout.styler
        
        name = styler.heading(self.name)
        help_text = self.help_text
        if self.exec_mode == 'cli':
            help_text = styler.apply(help_text, fg='green')
        else:
            help_text = styler.apply(help_text, fg='blue')
        
        stdout.write(f'{name}: {help_text}')
        if self.has_own_args:
            stdout.write(f'    See "{self.prog} --help" for usage details')
    
    def parse_simple_args(self, help_text):
        
        parser = argparse.ArgumentParser(
            prog=self.prog,
            description=help_text,
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        return parser.parse_args(self.argv)
    
    def execute(self):
        
        # Proxy to the appropriate method, sensibly handling any raised
        # TaskError (which will already be intercepted for class-based tasks,
        # but not for string or function-based ones)
        try:
            self.executor()
        except TaskError as e:
            self.stderr.write(str(e))
            sys.exit(1)
    
    def execute_string(self):
        
        help_text = f'Executes the following task on the command line:\n{self.help_text}'
        self.parse_simple_args(help_text)
        
        os.system(self.task)
    
    def execute_callable(self):
        
        self.parse_simple_args(self.help_text)
        
        settings = get_task_settings(self.name)
        self.task(settings=settings, stdout=self.stdout, stderr=self.stderr)
    
    def execute_class(self):
        
        settings = get_task_settings(self.name)
        t = self.task(self.prog, settings, self.argv)
        t.execute()
