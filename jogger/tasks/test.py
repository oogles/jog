import argparse
import os

from .base import Task, TaskError

try:
    import django  # noqa
    HAS_DJANGO = True
except ImportError:
    HAS_DJANGO = False

try:
    import coverage  # noqa
    HAS_COVERAGE = True
except ImportError:
    HAS_COVERAGE = False

try:
    import tblib  # noqa
    HAS_TBLIB = True
except ImportError:
    HAS_TBLIB = False


class TestTask(Task):
    
    help = (
        'Run the test suite. If coverage.py is detected, perform code '
        'coverage analysis, print an on-screen summary, and optionally '
        'generate a fully detailed HTML report.'
    )
    
    reporting_includes_cache_file = '/tmp/cov_reporting_includes'  # noqa: S108
    
    def __init__(self, *args, **kwargs):
        
        self._has_output = False
        
        super().__init__(*args, **kwargs)
    
    def add_arguments(self, parser):
        
        parser.add_argument(
            'paths',
            nargs='*',
            metavar='test_path',
            help='Module paths to test.'
        )
        
        parser.add_argument(
            '-q', '--quick',
            action='store_true',
            help=(
                'Run a "quick" variant of the task: no coverage analysis and '
                'running tests in parallel (where possible).'
            )
        )
        
        parser.add_argument(
            '-a',
            action='store_true',
            dest='accumulate',
            help=(
                'Accumulate coverage data across multiple runs. Disables all '
                'coverage reporting (to be run after all coverage data is'
                'accumulated).'
            )
        )
        
        parser.add_argument(
            '-c', '--cover',
            action='store_true',
            dest='force_cover',
            help=(
                'Force coverage analysis and reports in situations where they '
                'would ordinarily be skipped, e.g. when the test suite fails.'
            )
        )
        
        parser.add_argument(
            '-n', '--no-cover',
            action='store_true',
            dest='no_cover',
            help='Run tests without any code coverage analysis.'
        )
        
        parser.add_argument(
            '--report',
            action='store_true',
            dest='reports_only',
            help=(
                'Skip the test suite and just output the on-screen summary '
                'and generate the HTML report. Useful to review previous '
                'results or if using -a to accumulate results before running '
                'the reports.'
            )
        )
        
        parser.add_argument(
            '--erase',
            action='store_true',
            dest='erase_coverage',
            help=(
                'Erase any previously-stored coverage data. Must be run prior '
                'to the first command in a run when using -a. Otherwise, data '
                'will be accumulated into data from previous runs. Note: This '
                'must be used over calling coverage erase directly.'
            )
        )
        
        parser.add_argument('extra', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    
    def verify_arguments(self, options):
        
        if options['reports_only'] or options['erase_coverage']:
            switch = '--report' if options['reports_only'] else '--erase'
            if options['quick']:
                raise TaskError(f'-q/--quick and {switch} are mutually exclusive.')
            elif options['accumulate']:
                raise TaskError(f'-a and {switch} are mutually exclusive.')
            elif options['paths']:
                raise TaskError(f'Test paths cannot be specified when using {switch}.')
        
        if options['no_cover']:
            if options['force_cover']:
                raise TaskError('--cover and --no-cover are mutually exclusive.')
            elif options['accumulate']:
                raise TaskError('-a and --no-cover are mutually exclusive.')
            elif options['reports_only']:
                raise TaskError('--report and --no-cover are mutually exclusive.')
    
    def process_test_paths(self, test_paths):
        
        # Hook for subclasses to process test paths before they are used.
        # Do nothing by default.
        
        return test_paths
    
    @property
    def section_prefix(self):
        
        # If the command has generated any output, sections should be prefixed
        # with a newline. The first section to generate output should not.
        if self._has_output:
            return '\n'
        
        return ''
    
    def erase_coverage(self):
        
        # Remove any stored reporting includes. This will trigger `--report`
        # to display a useful message re not having any reporting data.
        try:
            os.remove(self.reporting_includes_cache_file)
        except FileNotFoundError:
            pass
        
        # Erase the actual coverage data
        self.cli('coverage erase')
    
    def store_reporting_includes(self, test_paths, accumulate=False):
        
        # Using coverage's `concurrency` configuration to run tests in parallel
        # means the dynamic `--source` option available for `coverage run` is
        # not respected by subprocesses (which only read from config files, not
        # CLI options, see https://coverage.readthedocs.io/en/latest/subprocess.html).
        # Replicate similar functionality by processing the provided test paths
        # and using the `--include` option on the various reporting commands
        # instead. For simplicity, use this approach even when tests are not
        # configured to run in parallel.
        # To facilitate reporting on previous test/coverage runs, store the
        # generated includes list in a file for later retrieval.
        
        if not test_paths:
            includes = 'all'
        else:
            truncated_paths = set()
            for path in test_paths:
                # If a path contains a "tests" segment (be it a directory or a
                # test.py file), truncate that path to only what appears BEFORE
                # that segment, and strip any trailing dots. If the path does
                # not contain a "tests" segment, this will keep the whole path.
                path = path.split('tests')[0].strip('.')
                
                # Convert from a dotted path spec to a file path spec
                path = path.replace('.', '/')
                
                truncated_paths.add(f'{path}/*')
            
            includes = ','.join(truncated_paths)
            
            # For some reason, a trailing comma is required when there is only
            # one path present, otherwise coverage gives "No data to report.",
            # so ensure a trailing comma is always present. This also makes it
            # easier to append to the list if `accumulate` is True.
            includes = f'{includes},'
        
        read_mode = 'a' if accumulate else 'w'
        with open(self.reporting_includes_cache_file, read_mode) as f:
            f.write(includes)
    
    def get_reporting_includes(self):
        
        try:
            with open(self.reporting_includes_cache_file, 'r') as f:
                includes = f.read().strip()
        except FileNotFoundError:
            # This should only occur when attempting to display reports from a
            # previous run that did not generate coverage data.
            raise TaskError('No reporting data available.')
        
        if includes == 'all':
            # The special value 'all' indicates all files should be included
            # in coverage reports, essentially meaning no `--include` option
            # is necessary
            includes = None
        
        return includes
    
    def get_coverage_command(self, accumulate, **options):
        
        accumulate = ' -a' if accumulate else ''
        
        return f'coverage run{accumulate} '
    
    def get_test_command(self, test_paths, using_coverage, quick, verbosity, extra, **options):
        
        command = []
        
        if not using_coverage:
            # Run with warnings enabled, unless the command will be run by
            # coverage (which expects a python script to run, not the `python`
            # program)
            command.append('python -Wa')
        
        command.append('manage.py test')
        command.extend(test_paths)
        
        # Pass all "extra" arguments, and the verbosity level, through to the
        # test command
        command.extend(extra)
        command.append(f'-v {verbosity}')
        
        # Add --parallel switch if using "quick" mode, unless disabled in
        # settings or if the switch is provided explicitly in "extra" arguments
        if not any(v.startswith('--parallel') for v in extra):
            parallel = self.settings.get('parallel', None)
            if quick:
                parallel = self.settings.get('quick_parallel', parallel)
                
                # In "quick" mode, if the parallel setting is not explicitly
                # disabled, assume it should be enabled
                if parallel is None:
                    parallel = True
            
            if parallel:
                if not HAS_TBLIB:
                    self.stdout.write(self.styler.warning(
                        'Tracebacks in parallel tests may not display correctly: '
                        'tblib not detected. pip install tblib to fix.'
                    ))
                
                command.append('--parallel')
                if parallel is not True:
                    # Assume a specific integer count is provided, but ensure
                    # it is appended as a string
                    command.append(str(parallel))
        
        return ' '.join(command)
    
    def do_summary(self, includes, verbosity, **options):
        
        if verbosity < 1:
            return
        
        self.stdout.write(self.styler.label(f'{self.section_prefix}Coverage summary'))
        
        cmd = 'coverage report'
        
        if includes:
            cmd = f'{cmd} --include {includes}'
        
        if verbosity < 2:
            cmd = f'{cmd} --skip-covered'
        
        self.cli(cmd)
    
    def do_html_report(self, includes, verbosity, **options):
        
        self.stdout.write(self.styler.label(f'{self.section_prefix}Generating HTML report...'))
        
        cmd = 'coverage html'
        
        if includes:
            cmd = f'{cmd} --include {includes}'
        
        if verbosity < 2:
            cmd = f'{cmd} --skip-covered'
        
        self.cli(cmd)
        
        html_report_path = os.path.abspath('htmlcov/index.html')
        if os.path.exists(html_report_path):
            html_report_url = f'file://{html_report_path}'
            path_swap = self.settings.get('report_path_swap', None)
            if path_swap:
                if '>' not in path_swap:
                    raise TaskError('Invalid format for report_path_swap setting.')
                
                old_path, new_path = path_swap.split('>')
                html_report_url = html_report_url.replace(old_path.strip(), new_path.strip())
            
            self.stdout.write(f'View the report at: {self.styler.label(html_report_url)}')
        else:
            self.stdout.write(f'Location of HTML report unknown, expected: {html_report_path}', style='warning')
    
    def do_tests(self, test_paths, coverage_command, **options):
        
        test_command = self.get_test_command(test_paths, using_coverage=bool(coverage_command), **options)
        
        # If coverage is enabled, ensure previous coverage data is erased prior
        # to the test suite being run, and combined afterwards. This ensures
        # that, even when tests are not being run in parallel, coverage.py
        # configurations with the `concurrency` setting enabled will have
        # access to clean, combined coverage data for reporting. However,
        # this is only necessary if the `accumulate` flag is not set. If it
        # is, assume the caller will handle erasing/combining as necessary.
        handle_coverage = coverage_command and not options['accumulate']
        
        if handle_coverage:
            self.erase_coverage()
        
        result = self.cli(f'{coverage_command}{test_command}')
        
        if handle_coverage:
            self.stdout.write('')  # newline
            self.cli('coverage combine')
        
        # Generate and store an "includes" list, based on the given test paths,
        # for use in later coverage reporting. This MUST be done after previous
        # coverage data is erased, should that be necessary, otherwise the
        # stored includes list will also be erased.
        self.store_reporting_includes(test_paths, options['accumulate'])
        
        return result.returncode == 0
    
    def handle_tests(self, paths, **options):
        
        test_paths = self.process_test_paths(paths)
        
        if not HAS_COVERAGE:
            coverage_command = ''
        elif options['no_cover'] or options['quick']:
            # This run will not generate coverage data, so clear any
            # previously stored reporting includes to prevent later
            # reporting attempts. There will be nothing to report.
            self.erase_coverage()
            coverage_command = ''
        else:
            coverage_command = self.get_coverage_command(**options)
        
        return self.do_tests(test_paths, coverage_command, **options)
    
    def handle(self, *args, **options):
        
        if not HAS_DJANGO:
            raise TaskError('Django not detected.')
        
        self.verify_arguments(options)
        
        if options['erase_coverage']:
            self.erase_coverage()
            return
        
        reports_only = options['reports_only']
        tests_passed = True
        
        if not reports_only:
            test_paths = options.pop('paths', None)
            tests_passed = self.handle_tests(test_paths, **options)
            self.stdout.write('')  # newline
        
        if not HAS_COVERAGE:
            # Not having coverage available is simply a warning unless directly
            # requesting coverage reports, in which case it is an error
            msg = 'Code coverage not available: coverage.py not detected'
            if not reports_only:
                self.stdout.write(msg, style='warning')
            else:
                raise TaskError(msg)
        elif not options['no_cover'] and not options['accumulate'] and not options['quick']:
            if not tests_passed and not options['force_cover']:
                self.stdout.write(
                    'Tests failed, coverage reports skipped. Show reports '
                    'anyway by using the --cover switch.'
                )
            else:
                includes = self.get_reporting_includes()
                self.do_summary(includes, **options)
                
                if reports_only:
                    # Only include the HTML report when explicitly requesting
                    # reports. Don't include as part of the standard post-run
                    # coverage summary.
                    self.do_html_report(includes, **options)
                
                self.stdout.write('')  # newline
    
    def cli(self, *args, **kwargs):
        
        self._has_output = True
        
        return super().cli(*args, **kwargs)
