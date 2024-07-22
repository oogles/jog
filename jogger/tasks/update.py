import os
import shutil
import sys

from .base import Task, TaskDefinitionError, TaskError


class UpdateTask(Task):
    
    help = (
        'Update the application by checking for remote changes, pulling them '
        'if found, updating dependencies if necessary, migrating the database, '
        'collecting static files, and restarting the relevant services.'
    )
    
    temp_requirements_dir = '/tmp'  # noqa: S108
    default_branch_name = 'main'
    
    def add_arguments(self, parser):
        
        parser.add_argument(
            '--no-input',
            action='store_true',
            dest='no_input',
            help=(
                'Do not prompt for user input, e.g. to confirm dependency '
                'updates or migrations.'
            )
        )
        
        parser.add_argument(
            '--skip-pull',
            action='store_true',
            help=(
                'Skip the "git pull" and proceed directly to the subsequent '
                'update steps. NOTE: This will force these steps to run even '
                'if no code changes have occurred.'
            )
        )
    
    @property
    def branch_name(self):
        
        return self.settings.get('branch_name', self.default_branch_name)
    
    def handle(self, **options):
        
        if not options['skip_pull']:
            self.check_updates()
        
        summary = {}
        requirements_path, temp_requirements_path = self.check_initial_requirements()
        
        if not options['skip_pull']:
            self.do_pull()
            
            # Assume success. Errors/issues will interrupt the process.
            summary['pull'] = True
        else:
            summary['pull'] = None  # skipped
        
        self.pre_update()
        
        summary['dependencies'] = self.do_dependency_check(requirements_path, temp_requirements_path)
        summary['migrations'] = self.do_migration_check()
        summary['content_types'] = self.do_stale_contenttypes_check()
        
        # A build step may not be defined, so a result of None indicates no
        # build at all, rather than the step being skipped
        build_result = self.do_build()
        if build_result is not None:
            summary['build'] = build_result
        
        summary['collect_static'] = self.do_collect_static()
        
        self.post_update()
        self.show_summary(summary)
    
    def get_collectstatic_command(self):
        
        return 'python manage.py collectstatic --no-input'
    
    def check_updates(self):
        
        self.stdout.write('Checking for updates', style='label')
        
        # Get remote refs up to date before checking. Swallow output so it
        # isn't written to the output stream.
        update_result = self.cli('git remote update', capture=True)
        if update_result.returncode:
            self.stderr.write(update_result.stderr.decode('utf-8'))
            raise TaskError('Update check failed, could not update remotes')
        
        branch_name = self.branch_name
        log_result = self.cli(f'git log --oneline origin {branch_name}..{branch_name} | wc -l', capture=True)
        if log_result.returncode:
            self.stderr.write(log_result.stderr.decode('utf-8'))
            raise TaskError('Update check failed, could not run diff')
        
        update_count = int(log_result.stdout)
        if not update_count:
            self.stdout.write('No remote changes')
            sys.exit(0)
        
        self.stdout.write(f'Found {update_count} new remote commits')
    
    def check_initial_requirements(self):
        
        project_dir = self.project_dir
        project_name = os.path.split(project_dir)[1].replace('-', '_')
        
        requirements_path = os.path.join(project_dir, 'requirements.txt')
        temp_requirements_path = os.path.join(
            self.temp_requirements_dir,
            f'{project_name}.lastpull.requirements.txt'
        )
        
        # If this is the first time the command has been run, make a copy of
        # the requirements.txt file prior to pulling
        if not os.path.exists(temp_requirements_path):
            shutil.copyfile(requirements_path, temp_requirements_path)
        
        return requirements_path, temp_requirements_path
    
    def do_pull(self):
        
        self.stdout.write('\nPulling', style='label')
        
        branch_name = self.branch_name
        cmd = f'git pull origin {branch_name} --prune --no-rebase'
        
        result = self.cli(cmd)
        
        if result.returncode:
            # Stop script here if the pull was not successful for any reason
            raise TaskError('Pull failed')
    
    def pre_update(self):
        
        # Hook for subclasses to run any pre-update tasks, such as stopping
        # any necessary services during the update process
        pass
    
    def do_dependency_check(self, requirements_path, temp_requirements_path):
        
        self.stdout.write('\nChecking Python library dependencies', style='label')
        
        # Check for dependency updates by diffing the stored requirements.txt
        # file with the one just pulled in
        diff_result = self.cli(f'diff -U 0 {temp_requirements_path} {requirements_path}', capture=True)
        
        if not diff_result.returncode:
            self.stdout.write('No changes detected')
            return True
        
        # Changes were detected, show the differences and prompt the user
        # whether to proceed with an install or not. Alternatively, if running
        # in no-input mode, proceed directly to the install.
        if self.kwargs['no_input']:
            answer = 'y'
        else:
            self.stdout.write(diff_result.stdout.decode('utf-8'))
            
            answer = input(
                'The above Python library dependency changes were detected, '
                'update now [y/n]? '
            )
        
        if answer.lower() == 'y':
            install_result = self.cli(f'pip install -r {requirements_path}')
            if install_result.returncode:
                self.stderr.write('Dependency install failed')
                return False
            
            # Make a copy of the now-applied requirements.txt to compare
            # next time the task is run
            shutil.copy(requirements_path, temp_requirements_path)
        elif answer.lower() == 'n':
            self.stdout.write('Dependency update skipped', style='warning')
            return None  # skipped
        else:
            # User didn't answer yes OR no, display an error message but
            # don't interrupt execution
            self.stdout.write('Dependency update aborted', style='error')
            return None  # skipped
    
    def do_migration_check(self):
        
        self.stdout.write('\nChecking migrations', style='label')
        
        cmd = "python manage.py migrate --plan --check"
        
        plan_result = self.cli(cmd, capture=True)
        if not plan_result.returncode:
            self.stdout.write('No changes detected')
            return True
        
        # Changes were detected, show them and prompt the user whether to
        # proceed with a migration or not. Alternatively, if running in
        # no-input mode, proceed directly with the migrations.
        if plan_result.stderr:
            self.stderr.write(plan_result.stderr.decode('utf-8').strip(), style='normal')
            self.stderr.write('Migration failed')
            return False
        elif self.kwargs['no_input']:
            answer = 'y'
        else:
            self.stdout.write(plan_result.stdout.decode('utf-8'))
            answer = input('The above migrations are unapplied, apply them now [y/n]? ')
        
        if answer.lower() == 'y':
            migrate_result = self.cli('python manage.py migrate')
            if migrate_result.returncode:
                self.stderr.write('Migration failed')
                return False
        elif answer.lower() == 'n':
            self.stdout.write('Migrations skipped', style='warning')
            return None  # skipped
        else:
            # User didn't answer yes OR no, display an error message but
            # don't interrupt execution
            self.stdout.write('Migrations aborted', style='error')
            return None  # skipped
    
    def do_stale_contenttypes_check(self):
        
        if self.kwargs['no_input']:
            # Due to the possibility of deleting records, do not remove stale
            # content types when running in no-input mode
            return None  # skipped
        
        self.stdout.write('\nChecking stale content types', style='label')
        
        # Fake a call to the management command to get the prompt (including
        # the list of stale content types)
        result = self.cli('yes no | python manage.py remove_stale_contenttypes', capture=True)
        
        if result.returncode:
            self.stderr.write(result.stderr.decode('utf-8').strip(), style='normal')
            self.stderr.write('Failed to detect stale content types')
            return False
        elif not result.stdout:
            self.stdout.write('No stale content types detected')
            return True
        
        # Some stale content types were found. Strip off the last line of
        # output (the prompt) and manually re-prompt in order to detect skipping
        output = result.stdout.decode('utf-8').strip().splitlines()[:-1]
        self.stdout.write('\n'.join(output))
        
        answer = input("Type 'yes' to continue, or 'no' to cancel: ")
        
        if answer.lower() != 'yes':
            return None  # skipped
        else:
            result = self.cli('python manage.py remove_stale_contenttypes --no-input')
            if result.returncode:
                self.stderr.write('Stale content type removal failed')
                return False
        
        return True
    
    def do_build(self):
        
        try:
            proxy = self.get_task_proxy('build')
        except TaskDefinitionError:
            # A "build" task either isn't defined or is invalidly defined.
            # Do nothing.
            return None
        else:
            self.stdout.write('\nRunning build/s', style='label')
            
            # Don't allow TaskErrors in the build step to interrupt the update
            # process, just show the error and note the failure for the summary
            try:
                proxy.execute()
            except TaskError as e:
                self.stderr.write(str(e), style='normal')
                self.stderr.write('Build failed')
                return False
            
            return True
    
    def do_collect_static(self):
        
        self.stdout.write('\nCollecting static files', style='label')
        
        if self.kwargs['no_input'] or self.settings.get('no_static_prompt', False):
            answer = 'y'
        else:
            self.stdout.write(
                f'This may {self.styler.label("overwrite existing files")} in your'
                ' static files directory. Are you sure you want to do this?'
            )
            answer = input('Collect static files now [y/n]? ')
        
        if answer.lower() != 'y':
            return None  # skipped
        else:
            cmd = self.get_collectstatic_command()
            result = self.cli(cmd)
            if result.returncode:
                self.stderr.write('Static file collection failed')
                return False
        
        return True
    
    def post_update(self):
        
        # Hook for subclasses to run any post-update tasks, such as restarting
        # any necessary services
        pass
    
    def show_summary(self, summary):
        
        self.stdout.write('\nSummary', style='label')
        
        for step, result in summary.items():
            if result is None:
                output = self.styler.warning('Skipped')
            elif not result:
                output = self.styler.error('Failed')
            else:
                output = self.styler.success('OK')
            
            step_title = step.capitalize().replace('_', ' ')
            self.stdout.write(f'{step_title}: {output}')
