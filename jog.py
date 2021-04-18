from jogger.tasks import DocsTask, LintTask, Task, TaskError


class ReleaseTask(Task):
    
    def handle(self, *args, **options):
        
        from jogger import __version__
        
        answer = input(f'Build and release version {__version__} (Y/n)? ')
        
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
        
        self.stdout.write('\nDone!', style='label')


tasks = {
    'lint': LintTask,
    'docs': DocsTask,
    'release': ReleaseTask
}
