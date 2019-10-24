import configparser
import os
from importlib.util import module_from_spec, spec_from_file_location

from jogger.exceptions import TaskDefinitionError

from .files import find_file

MAX_CONFIG_FILE_SEARCH_DEPTH = 8
JOG_FILE_NAME = 'jog.py'
CONFIG_FILE_NAME = 'setup.cfg'
CONFIG_BLOCK_PREFIX = 'jogger'


def find_config_file(target_file_name):
    
    path = os.getcwd()
    
    return find_file(target_file_name, path, MAX_CONFIG_FILE_SEARCH_DEPTH)


def get_tasks():
    
    jog_file = find_config_file(JOG_FILE_NAME)
    
    spec = spec_from_file_location('jog', jog_file)
    jog_file = module_from_spec(spec)
    spec.loader.exec_module(jog_file)
    
    try:
        return jog_file.tasks
    except AttributeError:
        raise TaskDefinitionError(f'No tasks dictionary defined in {JOG_FILE_NAME}.')


def get_task_settings(task_name):
    
    config_file_path = find_config_file(CONFIG_FILE_NAME)
    config_file = configparser.ConfigParser()
    config_file.read(config_file_path)
    
    try:
        return config_file[f'{CONFIG_BLOCK_PREFIX}:{task_name}']
    except KeyError:
        return {}
