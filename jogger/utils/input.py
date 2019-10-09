import os
from importlib.util import module_from_spec, spec_from_file_location

from jogger.exceptions import TaskDefinitionError

MAX_CONFIG_FILE_SEARCH_DEPTH = 10
JOG_FILE_NAME = 'jog.py'


def find_config_file(target_file_name):
    
    path = os.getcwd()
    matched_file = None
    depth = 0
    
    while path and depth < MAX_CONFIG_FILE_SEARCH_DEPTH:
        
        filename = os.path.join(path, target_file_name)
        
        if os.path.exists(filename):
            matched_file = filename
            break
        
        new_path = os.path.dirname(path)
        if new_path == path:
            break
        
        path = new_path
        depth += 1
    
    if not matched_file:
        raise FileNotFoundError(f'Could not find {target_file_name}.')
    
    return matched_file


def get_tasks():
    
    jog_file = find_config_file(JOG_FILE_NAME)
    
    spec = spec_from_file_location('jog', jog_file)
    jog_file = module_from_spec(spec)
    spec.loader.exec_module(jog_file)
    
    try:
        return jog_file.tasks
    except AttributeError:
        raise TaskDefinitionError(f'No tasks dictionary defined in {JOG_FILE_NAME}.')
