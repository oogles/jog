import argparse
import os
import sys
from importlib.util import spec_from_file_location, module_from_spec

from jogger import __version__ as version
from jogger.tasks.base import Task, TaskError, OutputWrapper

JOG_FILE_NAME = 'jog.py'
MAX_CONFIG_FILE_SEARCH_DEPTH = 10


class TaskDefinitionError(Exception):
    """
    Raised when there is an error in the definition of the task list used by
    ``jogger``.
    """
    
    pass


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
        
        prog = os.path.basename(sys.argv[0])
        self.prog = f'{prog} {name}'
        self.name = name
        
        self.task = task
        self.argv = argv
        
        self.stdout = stdout
        self.stderr = stderr
    
    def identify(self):
        
        task = self.task
        
        # TODO: Handle complex definition (dictionary)?
        
        if isinstance(task, str):
            executor = self.execute_string
            help_text = task
        elif isinstance(task, type) and issubclass(task, Task):
            executor = self.execute_class
            help_text = task.help
        elif callable(task):
            executor = self.execute_callable
            help_text = task.__doc__
        else:
            self.stderr.write(f'Unrecognised task format for "{self.name}".')
            sys.exit(1)
        
        return executor, help_text
    
    def parse_simple_args(self, help_text):
        
        parser = argparse.ArgumentParser(
            prog=self.prog,
            description=help_text
        )
        
        return parser.parse_args(self.argv)
    
    def execute(self):
        
        executor, help_text = self.identify()
        
        try:
            executor(help_text)
        except Exception as e:
            if not isinstance(e, TaskError):
                raise
            
            self.stderr.write(f'{e.__class__.__name__}: {e}')
            sys.exit(1)
    
    def execute_string(self, help_text):
        
        help_text = f'Executes the following task on the command line: {help_text}'
        self.parse_simple_args(help_text)
        
        os.system(self.task)
    
    def execute_callable(self, help_text):
        
        self.parse_simple_args(help_text)
        
        # TODO: Get settings from setup.cfg
        self.task(stdout=self.stdout, stderr=self.stderr)
    
    def execute_class(self, help_text):
        
        # TODO: Get settings from setup.cfg
        t = self.task(self.prog, self.argv)
        t.execute()


def find_config_file(target_file_name):
    
    path = os.getcwd()
    matched_file = None
    depth = 0
    
    while path and depth < MAX_CONFIG_FILE_SEARCH_DEPTH:
        
        filename = os.path.join(path, JOG_FILE_NAME)  # target_file_name
        
        if os.path.exists(filename):
            matched_file = filename
            break
        
        new_path = os.path.dirname(path)
        if new_path == path:
            break
        
        path = new_path
        depth += 1
    
    if not matched_file:
        raise FileNotFoundError(f'Could not find {target_file_name}.')
    
    return matched_file


def get_tasks():
    
    jog_file = find_config_file(JOG_FILE_NAME)
    
    spec = spec_from_file_location('jog', jog_file)
    jog_file = module_from_spec(spec)
    spec.loader.exec_module(jog_file)
    
    try:
        return jog_file.tasks
    except AttributeError:
        raise TaskDefinitionError(f'No tasks dictionary defined in {JOG_FILE_NAME}.')


def parse_args(argv=None):
    
    parser = argparse.ArgumentParser(
        description='Execute common, project-specific tasks.',
        epilog='Any additional arguments are passed through to the executed tasks.'
    )
    
    parser.add_argument(
        'task_name',
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
    stderr = OutputWrapper(sys.stderr)
    
    try:
        tasks = get_tasks()
    except (FileNotFoundError, TaskDefinitionError) as e:
        stderr.write(str(e))
        sys.exit(1)
    
    task_name = arguments.task_name
    try:
        task = tasks[task_name]
    except KeyError:
        stderr.write(f'Unknown task "{task_name}".')
        sys.exit(1)
    
    proxy = TaskProxy(task_name, task, stdout, stderr, arguments.extra)
    proxy.execute()


if __name__ == '__main__':
    main()
