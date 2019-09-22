import argparse

from jog_cmd import __version__ as version


def parse_args(argv=None):
    
    parser = argparse.ArgumentParser(
        description='Execute shortcuts to common, project-specific tasks.',
        epilog='Any additional arguments are passed through to the executed shortcut command.'
    )
    
    parser.add_argument(
        'command',
        help='The name of the shortcut command'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s {}'.format(version),
        help='Display the version number and exit'
    )
    
    parser.add_argument('extra', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    
    return parser.parse_args(argv)


def main(argv=None):
    
    arguments = parse_args(argv)
    
    print('execute:', arguments.command)


if __name__ == '__main__':
    main()
