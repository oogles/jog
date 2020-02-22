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
    """
    Search upwards from the current working directory looking for a config file
    named ``target_file_name``. The number of parent directories to search
    through is controlled by ``MAX_CONFIG_FILE_SEARCH_DEPTH``.
    
    :param target_file_name: The filename of the target file.
    :return: The absolute path of the located file.
    """
    
    path = os.getcwd()
    
    return find_file(target_file_name, path, MAX_CONFIG_FILE_SEARCH_DEPTH)


def get_tasks():
    """
    Search upwards from the current working directory looking for the task
    definition file (``JOG_FILE_NAME``). Import the file as a Python module
    and return its inner ``tasks`` dictionary. Raise ``TaskDefinitionError``
    if no ``tasks`` dictionary is defined in the imported module.
    
    :return: The task definition file's dictionary of tasks.
    """
    
    jog_file = find_config_file(JOG_FILE_NAME)
    
    spec = spec_from_file_location('jog', jog_file)
    jog_file = module_from_spec(spec)
    spec.loader.exec_module(jog_file)
    
    try:
        return jog_file.tasks
    except AttributeError:
        raise TaskDefinitionError(f'No tasks dictionary defined in {JOG_FILE_NAME}.')


def get_task_settings(task_name):
    """
    Search upwards from the current working directory looking for the project
    config file (``CONFIG_FILE_NAME``). Parse the file and return the section
    corresponding to ``task_name``. If no such section exists, return an empty
    section.
    
    :return: The config file section, as a ``configparser.SectionProxy`` object,
        for the given task.
    """
    
    config_file = configparser.ConfigParser()
    
    try:
        config_file_path = find_config_file(CONFIG_FILE_NAME)
    except FileNotFoundError:
        # Silently ignore non-existent settings files, they are not mandatory
        pass
    else:
        config_file.read(config_file_path)
    
    section = f'{CONFIG_BLOCK_PREFIX}:{task_name}'
    
    # If the section does not exist, add a dummy one. This allows this method
    # to always return a value of a consistent type.
    if not config_file.has_section(section):
        config_file.add_section(section)
    
    return config_file[section]
