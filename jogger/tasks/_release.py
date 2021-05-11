import configparser
import os
import re
import sys
from os.path import expanduser

from .base import Task, TaskError

try:
    import build  # noqa
    HAS_BUILD = True
except ImportError:
    HAS_BUILD = False

try:
    import twine  # noqa
    HAS_TWINE = True
except ImportError:
    HAS_TWINE = False


def strip_comments(text):
    """
    Remove comment lines (those starting with #) and leading/trailing
    whitespace from ``text``.
    """
    
    # (m?) enables multiline mode
    return re.sub(r'(?m)^ *#.*\n?', '', text).strip()


class ReleaseTask(Task):
    
    default_main_branch = 'main'
    
    def add_arguments(self, parser):
        
        parser.add_argument(
            'version',
            help='The version number to issue a release of.'
        )
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.current_version = self.get_current_version()
        self.new_version = self.kwargs['version']
        
        self.current_major_version = None
        self.new_major_version = None
        self.release_branch_name = None
        
        major_version_format = self.settings.get('major_version_format', None)
        if major_version_format:
            try:
                self.current_major_version = re.search(major_version_format, self.current_version).group(0)
                self.new_major_version = re.search(major_version_format, self.new_version).group(0)
            except AttributeError:
                raise TaskError('Invalid major version format.')
        
        release_branch_format = self.settings.get('release_branch_format', None)
        if release_branch_format:
            try:
                self.release_branch_name = release_branch_format.format(
                    version=self.new_version,
                    major_version=self.new_major_version
                )
            except AttributeError:
                raise TaskError('Invalid release branch format.')
    
    # TODO: Genericise
    def get_current_version(self):
        
        from jogger import __version__
        
        return __version__
    
    def handle(self, *args, **options):
        
        current_branch_name = self.verify_state()
        
        labeller = self.styler.label
        confirmation = input(
            f'Confirm moving from {labeller(self.current_version)} to '
            f'{labeller(self.new_version)} (Y/n)? '
        )
        if confirmation.lower() != 'y':
            sys.exit(0)
        
        branch_name = self.create_branch(current_branch_name)
        self.bump_version()
        self.commit_and_tag(branch_name)
        self.merge(branch_name)
        self.build()
        
        self.stdout.write('\nDone!', style='label')
    
    def verify_state(self):
        
        self.stdout.write('Verifying state...', style='label')
        
        # Ensure the necessary Python libraries to build and release the
        # package are available
        if not HAS_BUILD:
            raise TaskError('Missing requirement: build')
        
        if not HAS_TWINE:
            raise TaskError('Missing requirement: twine')
        
        # Ensure a correct-looking .pypirc is present
        config_file = configparser.ConfigParser()
        config_file.read(expanduser('~/.pypirc'))
        
        try:
            pypi_config = config_file['pypi']
        except KeyError:
            raise TaskError('A ~/.pypirc file is missing or does not contain a [pypi] section.')
        
        if 'username' not in pypi_config or 'password' not in pypi_config:
            raise TaskError('The PyPI config file must contain at least a username and password.')
        
        # Ensure there are no uncommitted changes
        check_result = self.cli('git diff-index --quiet HEAD --')
        if check_result.returncode:
            raise TaskError('Uncommitted changes detected.')
        
        # Ensure there are no unpushed changes
        lookup_result = self.cli('git branch --show-current', capture=True)
        branch_name = lookup_result.stdout.decode('utf-8').strip()
        
        # Get remote refs up to date before checking for unpushed changes.
        # Swallow output so it isn't written to the output stream.
        update_result = self.cli('git remote update', capture=True)
        if update_result.returncode:
            self.stderr.write(update_result.stderr.decode('utf-8'), style='normal')
            raise TaskError('Could not update remotes')
        
        log_result = self.cli(f'git log --oneline {branch_name}..origin {branch_name} | wc -l', capture=True)
        if log_result.returncode:
            self.stderr.write(log_result.stderr.decode('utf-8'), style='normal')
            raise TaskError('Could not complete check for unpushed changes')
        
        if int(log_result.stdout):
            raise TaskError('Unpushed changes detected.')
        
        self.stdout.write('All good')
        
        return branch_name
    
    def create_branch(self, current_branch):
        
        new_branch = self.release_branch_name
        labeller = self.styler.label
        
        self.stdout.write(f'\nCurrently on branch: {labeller(current_branch)}')
        
        answer = input(f'Create release branch {labeller(new_branch)} from {labeller(current_branch)} (Y/n)? ')
        if answer.lower() != 'y':
            return current_branch
        
        self.stdout.write('Creating release branch', style='label')
        create_result = self.cli(f'git checkout -b {new_branch}')
        if create_result.returncode:
            raise TaskError('Failed to create release branch')
        
        return new_branch
    
    def bump_version(self):
        
        current_version = self.current_version
        current_major_version = self.current_major_version
        new_version = self.new_version
        new_major_version = self.new_major_version
        
        bump_paths = self.settings.get('bump_paths', '')
        bump_paths = [i.strip() for i in bump_paths.splitlines()]
        bump_paths = list(filter(None, bump_paths))
        
        if not bump_paths:
            self.stdout.write('Warning: no paths provided for version bumping.', style='warning')
        
        self.stdout.write('Bumping version', style='label')
        for path in bump_paths:
            with open(path, 'r+') as f:
                file_contents = f.read()
                if current_version not in file_contents:
                    raise TaskError(f'Could not detect version in {path}.')
                
                file_contents = file_contents.replace(current_version, new_version)
                
                if new_major_version and os.path.basename(path) == 'conf.py' and 'Sphinx' in file_contents:
                    # Looks like a Sphinx config file and a separate "major"
                    # version is known
                    if current_major_version != new_major_version:
                        pattern = f'version ?= ?(\'|"){current_major_version}(\'|")'
                        file_contents = re.sub(pattern, f"version = '{new_major_version}'", file_contents)
                
                # Replace the file contents with the updates. Only truncate now,
                # as opposed to opening the file in 'w' mode, due to the
                # potential for errors above leaving the file empty.
                f.seek(0)
                f.truncate()
                f.write(file_contents)
        
        paths_string = ' '.join(bump_paths)
        
        self.cli(f'git --no-pager diff {paths_string}')
        
        self.stdout.write(
            'Check if the above diff is correct. If you proceed, these files '
            'will be staged and you will be prompted to enter a commit message. '
            'If you do not proceed, the above changes will be reverted.'
        )
        
        answer = input('Proceed with committing these changes (Y/n)? ')
        if answer.lower() != 'y':
            self.cli(f'git restore {paths_string}')
            sys.exit(0)
        
        self.cli(f'git add {paths_string}')
    
    def commit_and_tag(self, branch_name):
        
        new_version = self.new_version
        
        self.stdout.write('Committing and tagging version bump', style='label')
        
        diff_result = self.cli('git diff --compact-summary --staged --line-prefix=#', capture=True)
        commit_summary = diff_result.stdout.decode('utf-8')
        default_commit_msg = (
            '# Committing version bump. Enter a commit message below:\n'
            f'Bumped version to {new_version}.\n\n'
            f'# Summary of changes:\n{commit_summary}'
        )
        
        commit_msg = self.long_input(default_commit_msg)
        commit_msg = strip_comments(commit_msg)
        self.cli(f'git commit -m "{commit_msg}"')
        
        default_tag_msg = (
            '# Tagging new version. Enter a tag message below:\n'
            f'Version {new_version}.'
        )
        
        tag_msg = self.long_input(default_tag_msg)
        tag_msg = strip_comments(tag_msg)
        self.cli(f'git tag -a {new_version} -m "{tag_msg}"')
        
        self.cli(f'git push origin {branch_name} --tags')
    
    def merge(self, branch_name):
        
        main_branch_name = self.settings.get('main_branch', self.default_main_branch)
        
        if branch_name == main_branch_name:
            return
        
        self.stdout.write(f'Merging version bump back to {main_branch_name}', style='label')
        
        # Merge the release branch back into the main branch and return
        self.cli(f'git checkout {main_branch_name}')
        self.cli(f'git merge --no-ff {branch_name}')
        self.cli(f'git checkout {branch_name}')
    
    def build(self):
        
        answer = input(f'Build and release version {self.new_version} (Y/n)? ')
        
        if answer.lower() != 'y':
            return
        
        self.stdout.write('Building', style='label')
        build_result = self.cli('python3 -m build')
        if build_result.returncode:
            raise TaskError('Build failed.')
        
        self.stdout.write('\nUploading', style='label')
        upload_result = self.cli('python3 -m twine upload dist/*')
        if upload_result.returncode:
            raise TaskError('Upload failed.')
        
        self.stdout.write('\nCleaning up', style='label')
        rm_result = self.cli('rm -rf ./build/ ./dist/ ./*egg-info/')
        if rm_result.returncode:
            raise TaskError('Cleanup failed.')
