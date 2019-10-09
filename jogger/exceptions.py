class TaskDefinitionError(Exception):
    """
    Raised when there is an error in the definition of the task list used by
    ``jogger``.
    """
    
    pass


class TaskError(Exception):
    """
    Used to indicate problem during the execution of a task, yielding a nicely
    printed error message in the appropriate output stream (e.g. ``stderr``).
    """
    
    pass
