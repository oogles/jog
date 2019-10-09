import argparse
import os
import re
import sys
from inspect import cleandoc

from jogger import __version__ as version
from jogger.exceptions import TaskDefinitionError
from jogger.tasks.base import Task, TaskError
from jogger.utils.input import JOG_FILE_NAME, get_task_settings, get_tasks
from jogger.utils.output import OutputWrapper

TASK_NAME_RE = re.compile(r'^\w+$')


class TaskProxy:
    """
    A helper for identifying and executing tasks of different types. It will
    identify and execute the following:
    
    - Strings: Executed as-is on the command line.
    - Callables (e.g. functions): Called with ``stdout`` and ``stderr`` as
        keyword arguments, allowing the task to use separate output streams
        if necessary.
    - ``Task`` class objects: Instantiated with the remainder of the argument
        string (that not consumed by the ``jog`` program itself) and executed.
    """
    
    def __init__(self, name, task, stdout, stderr, argv=None):
        
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
            self.help_text = cleandoc(task.__doc__)
            self.has_own_args = False
        else:
            raise TaskDefinitionError(f'Unrecognised task format for "{name}".')
        
        prog = os.path.basename(sys.argv[0])
        self.prog = f'{prog} {name}'
        self.name = name
        
        self.task = task
        self.argv = argv
        
        self.stdout = stdout
        self.stderr = stderr
    
    def parse_simple_args(self, help_text):
        
        parser = argparse.ArgumentParser(
            prog=self.prog,
            description=help_text,
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        return parser.parse_args(self.argv)
    
    def execute(self):
        
        # Proxy to the appropriate method
        self.executor()
    
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


def parse_args(argv=None):
    
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Execute common, project-specific tasks.',
        epilog=(
            'Any additional arguments are passed through to the executed tasks.'
            '\n\n'
            'Run without arguments from within a target project to output all '
            f'tasks configured in that project\'s {JOG_FILE_NAME} file.'
        )
    )
    
    parser.add_argument(
        'task_name',
        nargs='?',
        metavar='task',
        help='The name of the task'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {version}',
        help='Display the version number and exit'
    )
    
    parser.add_argument('extra', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    
    return parser.parse_args(argv)


def main(argv=None):
    
    arguments = parse_args(argv)
    stdout = OutputWrapper(sys.stdout)
    stderr = OutputWrapper(sys.stderr, default_style='error')
    
    try:
        tasks = get_tasks()
        for name, task in tasks.items():
            tasks[name] = TaskProxy(name, task, stdout, stderr, arguments.extra)
    except (FileNotFoundError, TaskDefinitionError) as e:
        stderr.write(str(e))
        sys.exit(1)
    
    task_name = arguments.task_name
    if task_name:
        try:
            task = tasks[task_name]
            task.execute()
        except KeyError:
            stderr.write(f'Unknown task "{task_name}".')
            sys.exit(1)
        except TaskError as e:
            stderr.write(f'{e.__class__.__name__}: {e}')
            sys.exit(1)
    elif not tasks:
        stdout.write(f'No tasks defined.')
    else:
        stdout.write('Available tasks:\n', 'label')
        styler = stdout.styler
        for task_name, task in tasks.items():
            task_name = styler.heading(task_name)
            help_text = task.help_text
            if task.exec_mode == 'cli':
                help_text = styler.apply(help_text, fg='green')
            else:
                help_text = styler.apply(help_text, fg='blue')
            
            stdout.write(f'{task_name}: {help_text}')
            if task.has_own_args:
                stdout.write(f'    See "{task.prog} --help" for usage details')


if __name__ == '__main__':
    main()
