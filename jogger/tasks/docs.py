import os

from jogger.utils.input import JOG_FILE_NAME, find_config_file

from .base import Task, TaskError

try:
    import sphinx  # noqa
    HAS_SPHINX = True
except ImportError:
    HAS_SPHINX = False


class DocsTask(Task):
    
    help = (
        'Build the project documentation using Sphinx.'
    )
    
    def add_arguments(self, parser):
        
        parser.add_argument(
            '-f', '--full',
            action='store_true',
            dest='full',
            help=(
                'Remove previously built documentation before rebuilding all '
                'pages from scratch.'
            )
        )
        
        parser.add_argument(
            '-l', '--link',
            action='store_true',
            dest='link_only',
            help='Output the link to previously built documentation and exit.'
        )
    
    def handle(self, **options):
        
        if not HAS_SPHINX:
            raise TaskError('Sphinx not detected.')
        
        # Get the project directory by locating the task file (jog.py). Assume
        # a "docs" directory under that.
        project_dir = os.path.dirname(find_config_file(JOG_FILE_NAME))
        docs_dir = os.path.join(project_dir, 'docs')
        
        if not os.path.exists(docs_dir):
            raise TaskError(f'Documentation directory not found at {docs_dir}.')
        
        if options['link_only']:
            show_link = True
            output_prefix = ''
        else:
            command = [f'cd {docs_dir}']
            if options['full']:
                command.append('make clean')
            
            command.append('make html')
            
            result = self.cli(' && '.join(command))
            show_link = result.returncode == 0
            output_prefix = '\n'
        
        if show_link:
            index_path = os.path.join(docs_dir, '_build', 'html', 'index.html')
            if os.path.exists(index_path):
                self.stdout.write(self.styler.label(
                    f'{output_prefix}Generated documentation can be viewed at: file://{index_path}'
                ))
            else:
                self.stdout.write(self.styler.warning(
                    f'{output_prefix}Generated documentation not found, expected at: {index_path}'
                ))
