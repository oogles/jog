from jogger.tasks import DocsTask, LintTask
from jogger.tasks._release import ReleaseTask


tasks = {
    'lint': LintTask,
    'docs': DocsTask,
    'release': ReleaseTask
}
