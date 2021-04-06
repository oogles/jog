import os
from collections import OrderedDict

from jogger.utils.files import walk

from .base import Task, TaskError

try:
    import flake8  # noqa
    HAS_FLAKE8 = True
except ImportError:
    HAS_FLAKE8 = False

try:
    import isort  # noqa
    HAS_ISORT = True
except ImportError:
    HAS_ISORT = False

try:
    from django.core.management import call_command  # noqa
    HAS_DJANGO = True
except ImportError:
    HAS_DJANGO = False

ENDINGS = {
    'CRLF': b'\r\n',
    'CR': b'\r',
    'LF': b'\n'
}

DEFAULT_GOOD_ENDING = 'LF'
DEFAULT_MAX_FILESIZE = 1024 * 1024  # 1MB in bytes


class LintTask(Task):
    
    help = (
        'Lint the project. Automatically detects, and uses if found, isort and '
        'flake8 for linting Python code. Also runs fable (Find All Bad Line '
        'Endings) and performs a dry-run of makemigrations (if Django is detected).'
    )
    
    steps = [
        ('python', '-p', 'Perform linting of Python code.'),
        ('fable', '-f', 'Find all bad line endings.'),
        ('migrations', '-m', 'Perform makemigrations dry-run.')
    ]
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.outcomes = OrderedDict()
    
    def add_arguments(self, parser):
        
        for name, short_flag, help_text in self.steps:
            parser.add_argument(
                short_flag, f'--{name}',
                action='store_true',
                dest=f'do_{name}',
                help=help_text
            )
    
    def log_step(self, intro):
        
        self.stdout.write(self.styler.label(intro))
    
    def handle(self, **options):
        
        settings = self.settings
        
        explicit_steps = []
        implicit_steps = []
        for step, _, _ in self.steps:
            # Consider the step explicit if a command line flag is included for
            # it. Otherwise, consider the step implicit unless it has been
            # disabled via the project settings file
            if options[f'do_{step}']:
                explicit_steps.append(step)
            elif settings.getboolean(step, fallback=True):
                implicit_steps.append(step)
        
        if explicit_steps:
            run = explicit_steps
            explicit = True
        else:
            run = implicit_steps
            explicit = False
        
        for step in run:
            getattr(self, f'handle_{step}')(explicit)
        
        summary = []
        for label, result in self.outcomes.items():
            if result:
                styled_result = self.styler.success('OK')
            else:
                styled_result = self.styler.error('FAIL')
            
            summary.append(f'{label}: {styled_result}')
        
        if summary:
            self.log_step('Summary')
            self.stdout.write('\n'.join(summary))
    
    def handle_python(self, explicit):
        
        if explicit and not HAS_ISORT and not HAS_FLAKE8:
            self.stderr.write('Cannot lint python: Neither isort nor flake8 are available.')
            return
        
        if HAS_ISORT:
            self.log_step('Running isort...')
            result = self.cli('isort --check-only --diff .')
            self.outcomes['isort'] = result.returncode == 0
            self.stdout.write('')  # newline
        
        if HAS_FLAKE8:
            self.log_step('Running flake8...')
            result = self.cli('flake8 .')
            self.outcomes['flake8'] = result.returncode == 0
            self.stdout.write('')  # newline
    
    def _get_fable_excludes(self):
        
        # Start with some sane default exclusions
        excludes = {'.git', '__pycache__', '*.pyc', '*.pdf', '*.png', '*.jpg', '*.jpeg', '*.gif'}
        
        # Add any configured excludes
        try:
            extra_excludes = self.settings['fable_exclude']
        except KeyError:
            pass
        else:
            # Split the multiline string into a list, stripping whitespace and
            # filtering out empty values
            extra_excludes = [p.strip() for p in extra_excludes.splitlines()]
            excludes.update(filter(None, extra_excludes))
        
        return excludes
    
    def handle_fable(self, explicit):
        
        self.log_step('Running fable...')
        
        excludes = self._get_fable_excludes()
        
        # Get the appropriate good ending from settings
        good_ending = self.settings.get('fable_good_endings', DEFAULT_GOOD_ENDING)
        if good_ending not in ENDINGS:
            raise TaskError(f'Invalid value for fable_good_endings setting ({good_ending}).')
        
        # Compile inverse dictionary of bad line endings
        bad_endings = {v: k for k, v in ENDINGS.items() if k != good_ending}
        
        # Get the maximum file size to analyse from settings
        max_filesize = self.settings.get('fable_max_filesize', DEFAULT_MAX_FILESIZE)
        
        try:
            max_filesize = int(max_filesize)
        except ValueError:
            raise TaskError(f'Invalid value for fable_max_filesize setting ({max_filesize}).')
        
        result = True
        skipped = 0
        for filename in walk('./', excludes):
            if os.path.getsize(filename) > max_filesize:
                skipped += 1
                continue
            
            with open(filename, 'rb') as f:
                content = f.read()
                for ending in bad_endings:
                    if ending in content:
                        self.stdout.write(f'Detected {bad_endings[ending]}: {filename}')
                        result = False
                        break
        
        if skipped:
            self.stdout.write(f'Skipped {skipped} large files')
        
        self.outcomes['fable'] = result
        self.stdout.write('')  # newline
    
    def handle_migrations(self, explicit):
        
        if explicit and not HAS_DJANGO:
            self.stderr.write('Cannot check migrations: Django is not available.')
            return
        
        if HAS_DJANGO:
            self.log_step('\nChecking for missing migrations...')
            
            try:
                call_command('makemigrations', dry_run=True, check=True, stdout=self.stdout, stderr=self.stderr)
            except SystemExit:
                result = False
            else:
                result = True
            
            self.outcomes['migrations'] = result
            self.stdout.write('')  # newline
