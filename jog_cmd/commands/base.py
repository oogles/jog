import sys
from argparse import ArgumentParser, FileType
from io import TextIOBase


class CommandError(Exception):
    """
    Used to indicate problem during the execution of a command, yielding a
    nicely printed error message in the appropriate output stream (e.g. stderr).
    """
    
    pass


class OutputWrapper(TextIOBase):
    """
    Simple wrapper around stdout/stderr to normalise some behaviours.
    """
    
    def __init__(self, out, ending='\n'):
        
        self._out = out
        self.ending = ending

    def __getattr__(self, name):
        
        return getattr(self._out, name)

    def isatty(self):
        
        return hasattr(self._out, 'isatty') and self._out.isatty()

    def write(self, msg, ending=None):
        
        ending = self.ending if ending is None else ending
        if ending and not msg.endswith(ending):
            msg += ending
        
        self._out.write(msg)


class Command:
    """
    
    """
    
    help = ''
    
    def __init__(self, name, argv):
        
        parser = self.create_parser(name)
        options = parser.parse_args(argv)
        
        kwargs = vars(options)
        
        self.stdout = OutputWrapper(kwargs['stdout'])
        self.stderr = OutputWrapper(kwargs['stderr'])
        
        self.args = kwargs.pop('args', ())
        self.kwargs = kwargs
    
    def create_parser(self, name):
        """
        Create and return the ``ArgumentParser`` which will be used to parse
        the arguments to this command.
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
        
        self.add_arguments(parser)
        
        return parser
    
    def add_arguments(self, parser):
        """
        Entry point for subclassed commands to add custom arguments.
        """
        
        pass
    
    def execute(self):
        """
        Execute this command. Intercept any raised ``CommandError`` and print
        it sensibly to stderr. Allow all other exceptions to raise as per usual.
        """
        
        try:
            self.handle(*self.args, **self.kwargs)
        except Exception as e:
            if not isinstance(e, CommandError):
                raise
            
            self.stderr.write(f'{e.__class__.__name__}: {e}')
            sys.exit(1)
    
    def handle(self, *args, **kwargs):
        """
        The actual logic of the command. Subclasses must implement this method.
        """
        
        raise NotImplementedError('Subclasses of Command must provide a handle() method.')
