import os

from .base import Command


class TestCommand(Command):
    
    help = (
        'Run the full test suite under coverage, printing an on-screen report'
        'of the files with less than 100% coverage at the end, and generating '
        'a HTML report of all files for in-depth analysis.'
    )
    
    def handle(self, *args, **options):
        
        os.system('coverage run --branch manage.py test; coverage report --skip-covered && coverage html')
