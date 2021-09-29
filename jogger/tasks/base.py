import argparse
import os
import re
import subprocess
import sys
import tempfile

from jogger.exceptions import TaskDefinitionError, TaskError
from jogger.utils.output import OutputWrapper, clean_description

TASK_NAME_RE = re.compile(r'^\w+$')
DEFAULT_DESCRIPTION = 'No task description provided. Just guess?'

#
# The class-based "task" interface is heavily based on Django's management
# command infrastructure, found in ``django.core.management.base``, though
# greatly simplified and without any of the Django machinery.
#


class BaseTask:
    """
    A base class for controlling configuration and execution of ``jogger`` tasks.
    """
    
    help = ''
    
    def __init__(self, prog, name, conf, default_stdout, default_stderr, argv=None):
        
        self.prog = prog
        self.name = name
        self.conf = conf
        self._settings = None
        
        parser = self.create_parser(prog, default_stdout, default_stderr)
        
        # If no explicit args are provided, use an empty string. This prevents
        # parse_args() from using `sys.argv` as a default value, which is
        # especially problematic if calling one task from within another (e.g.
        # using Task.get_task_proxy()).
        argv = argv or ''
        options = parser.parse_args(argv)
        
        kwargs = vars(options)
        
        stdout = kwargs['stdout']
        stderr = kwargs['stderr']
        
        # If the two streams are redirected to the same location, use the same
        # handle for each so they don't write over the top of each other.
        # Nested tasks may have already performed this step, so also ensure
        # the handles aren't already the same.
        if stdout.name == stderr.name and stdout is not stderr:
            stderr.close()
            kwargs['stderr'] = stderr = stdout
        
        no_color = kwargs['no_color']
        self.stdout = OutputWrapper(stdout, no_color=no_color)
        self.stderr = OutputWrapper(stderr, no_color=no_color, default_style='error')
        self.styler = self.stdout.styler
        
        self.using_system_out = stdout is sys.stdout
        self.using_system_err = stderr is sys.stderr
        
        self.args = kwargs.pop('args', ())
        self.kwargs = kwargs
    
    def create_parser(self, prog, default_stdout, default_stderr):
        """
        Create and return the ``ArgumentParser`` which will be used to parse
        the arguments to this task.
        """
        
        parser = argparse.ArgumentParser(
            prog=prog,
            description=self.help or None,
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        # Use line buffering. Might not be the best for performance, but
        # important when redirecting output to a file so that output from the
        # task itself (i.e. self.stdout.write()) and output from any executed
        # commands (e.g. self.cli()) is written to the file in the correct order.
        parser.add_argument(
            '--stdout',
            nargs='?',
            type=argparse.FileType('w', bufsize=1),
            default=default_stdout
        )
        
        # Use line buffering. See comment on --stdout for details.
        parser.add_argument(
            '--stderr',
            nargs='?',
            type=argparse.FileType('w', bufsize=1),
            default=default_stderr
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
    
    @property
    def settings(self):
        
        if not self._settings:
            self._settings = self.conf.get_task_settings(self.name)
        
        return self._settings
    
    def cli(self, cmd, capture=False):
        """
        Run a command on the system's command line, in the context of the task's
        :attr:`~Task.stdout` and :attr:`~Task.stderr` output streams. Output
        can be captured rather than displayed using ``capture=True``.
        
        :param cmd: The command string to execute.
        :param capture: ``True`` to capture all output from the command rather
            than writing it to the configured output streams.
        :return: The command result object.
        """
        
        kwargs = {}
        if capture:
            kwargs['capture_output'] = True
        else:
            # Pass redirected output streams if necessary
            if not self.using_system_out:
                kwargs['stdout'] = self.kwargs['stdout']
            
            if not self.using_system_err:
                kwargs['stderr'] = self.kwargs['stderr']
        
        return subprocess.run(cmd, shell=True, **kwargs)
    
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
        
        raise NotImplementedError('Subclasses must provide a handle() method.')


class SimpleTask(BaseTask):
    """
    A helper class for executing string- and function-based tasks.
    """
    
    def __init__(self, task, prog, name, conf, default_stdout, default_stderr, argv=None):
        
        self.task = task
        if isinstance(task, str):
            self.help = f'Executes the following task on the command line:\n{task}'
            self._is_callable = False
        elif callable(task):
            self.help = clean_description(task.__doc__, collapse_paragraphs=False)
            self._is_callable = True
        else:
            raise TaskDefinitionError(f'Unrecognised task format for "{name}".')
        
        super().__init__(prog, name, conf, default_stdout, default_stderr, argv)
    
    def handle(self, *args, **kwargs):
        
        if self._is_callable:
            cmd = self.task(settings=self.settings, stdout=self.stdout, stderr=self.stderr)
        else:
            cmd = self.task
        
        if cmd:
            self.cli(cmd)


class Task(BaseTask):
    """
    An advanced ``jogger`` task capable of defining its own arguments, calling
    nested tasks, and other more advanced features.
    """
    
    default_long_input_editor = 'nano'
    
    def create_parser(self, *args, **kwargs):
        
        parser = super().create_parser(*args, **kwargs)
        
        parser.add_argument(
            '-v', '--verbosity',
            default=1,
            type=int,
            choices=[0, 1, 2, 3],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output'
        )
        
        return parser
    
    @property
    def project_dir(self):
        
        return self.conf.project_dir
    
    def long_input(self, default=None, editor=None):
        """
        Replacement for Python's ``input()`` builtin that uses the system's
        default editor to ask for user input.
        
        :param default: Default text to populate the editor with.
        :param editor: The editor to use. The system default will be used if
            this is not provided.
        :return: The text entered by the user.
        """
        
        # This is adapted from code by Chase Seibert, see:
        # https://chase-seibert.github.io/blog/2012/10/31/python-fork-exec-vim-raw-input.html
        
        if not editor:
            editor = os.environ.get('VISUAL') or os.environ.get('EDITOR') or self.default_long_input_editor
        
        with tempfile.NamedTemporaryFile(mode='r+') as tmpfile:
            if default:
                tmpfile.write(default)
                tmpfile.flush()
            
            subprocess.run([editor, tmpfile.name])
            
            tmpfile.seek(0)
            content = tmpfile.read().strip()
        
        return content
    
    def get_task_proxy(self, task_name, *args):
        """
        Return an object representing the task matching the given name,
        configured with the given arguments, if any. This proxy object can be
        used to execute the task, regardless of whether it is defined as a
        string, function, or class::
        
            proxy = self.get_task_proxy('test')
            proxy.execute()
        
        Arguments should be provided as individual strings, e.g.::
        
            proxy = get_task_proxy('test', '-v', '2', 'myapp.tests', '--keepdb')
        
        Depending on the type of task (string, function, or class based),
        common arguments of the source task will be propagated automatically,
        including (where relevant):
        ``--stdout``, ``--stderr``, ``--no-color``, and ``-v``/``--verbosity``.
        
        :param task_name: The task name as a string.
        :param args: Extra task arguments, as individual strings.
        :return: The task proxy instance.
        """
        
        try:
            task = self.conf.get_tasks()[task_name]
        except FileNotFoundError as e:
            raise TaskDefinitionError(e)
        except KeyError:
            raise TaskDefinitionError(f'Unknown task "{task_name}".')
        
        # Don't pass through the OutputWrapper instances themselves, just the
        # stream they wrap. The nested task instance will create its own
        # OutputWrapper around it, potentially with a different configuration
        # (depending on arguments such as --no-color). But passing through the
        # underlying streams allows reusing them, which is important for streams
        # redirected to files so they append to the same file rather than
        # overwriting each other.
        stdout = self.stdout._out
        stderr = self.stderr._out
        
        # Get the proxy instance, allow raising TaskDefinitionError if necessary
        proxy = TaskProxy('proxy.execute', task_name, task, self.conf, stdout, stderr)
        
        # Propagate common arguments of the source task, if not provided explicitly
        args = list(args)
        
        if '--no-color' not in args and self.kwargs['no_color']:
            args.append('--no-color')
        
        if not proxy.simple:
            if '-v' not in args and '--verbosity' not in args:
                args.extend(('--verbosity', str(self.kwargs['verbosity'])))
        
        proxy.argv = args
        
        return proxy


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
    
    def __init__(self, prog, name, task, conf, stdout=None, stderr=None, argv=None):
        
        try:
            valid_name = TASK_NAME_RE.match(name)
        except TypeError:  # not a string
            valid_name = False
        
        if not valid_name:
            raise TaskDefinitionError(
                f'Task name "{name}" is not valid - must be a string '
                'containing alphanumeric characters and the underscore only.'
            )
        
        if isinstance(task, type) and issubclass(task, Task):
            self.description = clean_description(task.help)
            self.description_fg = 'blue'
            self.simple = False
        elif callable(task):
            self.description = clean_description(task.__doc__)
            self.description_fg = 'blue'
            self.simple = True
        elif isinstance(task, str):
            self.description = task
            self.description_fg = 'green'
            self.simple = True
        else:
            raise TaskDefinitionError(f'Unrecognised task format for "{name}".')
        
        if stdout is None:
            stdout = sys.stdout
        
        if stderr is None:
            stderr = sys.stderr
        
        self.prog = f'{prog} {name}'
        self.name = name
        self.task = task
        self.conf = conf
        self.stdout = stdout
        self.stderr = stderr
        self.argv = argv
    
    def get_description(self, styler):
        """
        Return a description of this task, suitable for display in a listing
        of available tasks.
        """
        
        name = styler.heading(self.name)
        description = styler.apply(self.description or DEFAULT_DESCRIPTION, fg=self.description_fg)
        
        return f'{name}: {description}\n    See "{self.prog} --help" for usage details'
    
    def execute(self, passive=True):
        
        common_args = (self.prog, self.name, self.conf, self.stdout, self.stderr, self.argv)
        
        if self.simple:
            task = SimpleTask(self.task, *common_args)
        else:
            task = self.task(*common_args)
        
        # Invoke handle() instead of execute() when in "passive" mode. This
        # is typically for when calling from within another task, as execute()
        # catches TaskError and calls sys.exit(), which may not be desirable
        # for a nested task. Passive mode leaves the calling task the option
        # of manually handling such exceptions if necessary, and its own
        # execute() method will deal with them if left uncaught.
        if passive:
            task.handle(*task.args, **task.kwargs)
        else:
            task.execute()
