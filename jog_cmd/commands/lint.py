from .base import Command


import configparser
import os

from django.core.management import call_command


class LintCommand(Command):
    
    help = (
        'Lint the project using isort, flake8, and fable (Find All Bad Line '
        'Endings). Also perform a dry-run of makemigrations to ensure no '
        'migrations are missed. Configuration of fable is possible via a '
        'setup.cfg file in the project root directory. Configuration of isort '
        'and flake8 is possible via their normal means.'
    )
    
    def add_arguments(self, parser):
        
        parser.add_argument(
            '--no-migrations', action='store_true', dest='no_migrations',
            help='Disable the dry-run of makemigrations.'
        )
    
    def build_fable_command(self):
        """
        Build up a command to identify and print all relevant files within the
        project that contain non-unix line endings (i.e. CRLF).
        Based on: https://stackoverflow.com/a/37846265/405174
        """
        
        config_file = configparser.ConfigParser()
        config_file.read('setup.cfg')
        
        paths = ''
        try:
            config = config_file['fable']
        except KeyError:
            pass
        else:
            try:
                excludes = config['exclude']
            except KeyError:
                pass
            else:
                # Split the multiline string into a list, stripping whitespace
                # and filtering out empty values
                excludes = filter(None, [p.strip() for p in excludes.splitlines()])
                paths = ' '.join([f'! -path "./{p}"' for p in excludes])
        
        return f"find . -type f {paths} -exec file {{}} \\; | grep \"CRLF\" | awk -F ':' '{{ print $1 }}'"
    
    def handle(self, *args, **options):
        
        commands = [
            ('Running isort...', 'isort -rc --diff .'),
            ('\nRunning flake8...', 'flake8 . || true'),
            ('\nRunning fable...', self.build_fable_command())
        ]
        
        for intro, command in commands:
            self.stdout.write(self.style.MIGRATE_LABEL(intro))
            os.system(command)
        
        if not options['no_migrations']:
            self.stdout.write(self.style.MIGRATE_LABEL('\nChecking for missing migrations...'))
            call_command('makemigrations', dry_run=True, check=True)
        
        self.stdout.write(self.style.MIGRATE_LABEL('\nDone'))
