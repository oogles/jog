import argparse
import os
import sys
from importlib.util import spec_from_file_location, module_from_spec

from jog_cmd import __version__ as version

JOG_FILE_NAME = 'jog.py'
MAX_CONFIG_FILE_SEARCH_DEPTH = 10


class CommandDefinitionError(Exception):
    """
    Raised when there is an error in the definition of the command list used
    by ``jog``.
    """
    
    pass


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
    
    try:
        commands = get_commands()
    except (FileNotFoundError, CommandDefinitionError) as e:
        print(e)
        sys.exit(1)
    
    target = arguments.target
    try:
        command = commands[target]
    except KeyError:
        print(f'Unknown command "{target}".')
        sys.exit(1)
    
    # TODO: Handle function being callable
    # TODO: Parse extra args per command?
    # TODO: Get settings from setup.cfg
    
    # TODO: Use something more robust?
    os.system(command)


if __name__ == '__main__':
    main()
