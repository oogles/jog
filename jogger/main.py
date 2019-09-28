import argparse
import os
import sys
from importlib.util import spec_from_file_location, module_from_spec

from jogger import __version__ as version
from jogger.commands.base import Command, CommandError, OutputWrapper

JOG_FILE_NAME = 'jog.py'
MAX_CONFIG_FILE_SEARCH_DEPTH = 10


class CommandDefinitionError(Exception):
    """
    Raised when there is an error in the definition of the command list used
    by ``jog``.
    """
    
    pass


class CommandProxy:
    """
    A helper for identifying and executing commands of different types. It will
    identify and execute the following:
    
    - Strings: Executed as-is on the command line.
    - Callables (e.g. functions): Called with ``stdout`` and ``stderr`` as
        keyword arguments, allowing the command to use separate output streams
        if necessary.
    - ``Command`` class objects: Instantiated with the remainder of the argument
        string (that not consumed by the ``jog`` program itself) and executed.
    """
    
    def __init__(self, name, command, stdout, stderr, argv=None):
        
        prog = os.path.basename(sys.argv[0])
        self.prog = f'{prog} {name}'
        self.name = name
        
        self.command = command
        self.argv = argv
        
        self.stdout = stdout
        self.stderr = stderr
    
    def identify(self):
        
        cmd = self.command
        
        # TODO: Handle complex definition (dictionary)?
        
        if isinstance(cmd, str):
            executor = self.execute_string
            help_text = cmd
        elif isinstance(cmd, type) and issubclass(cmd, Command):
            executor = self.execute_command
            help_text = cmd.help
        elif callable(cmd):
            executor = self.execute_callable
            help_text = cmd.__doc__
        else:
            self.stderr.write(f'Unrecognised command format for "{self.name}".')
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
            if not isinstance(e, CommandError):
                raise
            
            self.stderr.write(f'{e.__class__.__name__}: {e}')
            sys.exit(1)
    
    def execute_string(self, help_text):
        
        help_text = f'Executes the following command on the command line: {help_text}'
        self.parse_simple_args(help_text)
        
        os.system(self.command)
    
    def execute_callable(self, help_text):
        
        self.parse_simple_args(help_text)
        
        # TODO: Get settings from setup.cfg
        self.command(stdout=self.stdout, stderr=self.stderr)
    
    def execute_command(self, help_text):
        
        # TODO: Get settings from setup.cfg
        cmd = self.command(self.prog, self.argv)
        cmd.execute()


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


def get_commands():
    
    jog_file = find_config_file(JOG_FILE_NAME)
    
    spec = spec_from_file_location('jog', jog_file)
    jog_file = module_from_spec(spec)
    spec.loader.exec_module(jog_file)
    
    try:
        return jog_file.commands
    except AttributeError:
        raise CommandDefinitionError(f'No commands dictionary defined in {JOG_FILE_NAME}.')


def parse_args(argv=None):
    
    parser = argparse.ArgumentParser(
        description='Execute shortcuts to common, project-specific tasks.',
        epilog='Any additional arguments are passed through to the executed shortcut command.'
    )
    
    parser.add_argument(
        'target',
        metavar='command',
        help='The name of the shortcut command'
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
        commands = get_commands()
    except (FileNotFoundError, CommandDefinitionError) as e:
        stderr.write(e)
        sys.exit(1)
    
    target = arguments.target
    try:
        command = commands[target]
    except KeyError:
        stderr.write(f'Unknown command "{target}".')
        sys.exit(1)
    
    proxy = CommandProxy(target, command, stdout, stderr, arguments.extra)
    proxy.execute()


if __name__ == '__main__':
    main()
