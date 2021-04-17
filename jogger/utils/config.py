import configparser
import os
from importlib.util import module_from_spec, spec_from_file_location

from jogger.exceptions import TaskDefinitionError

from .files import find_file

MAX_CONFIG_FILE_SEARCH_DEPTH = 8
JOG_FILE_NAME = 'jog.py'
CONFIG_FILE_NAME = 'setup.cfg'
ENV_CONFIG_FILE_NAME = 'joggerenv.cfg'
CONFIG_BLOCK_PREFIX = 'jogger'


class JogConf:
    """
    Entry point to all configuration files for ``jogger``.
    
    Instantiation initiates an upward search from the current working directory
    looking for the task definition file (``JOG_FILE_NAME``). The file can be
    up to a maximum of ``MAX_CONFIG_FILE_SEARCH_DEPTH`` directories higher. If
    not found, raise ``FileNotFoundError`` - the project must contain this
    file in order to use ``jogger``.
    
    The location of the task definition file dictates the "project directory"
    for the purposes of ``jogger``, and any other config files must also appear
    under the same directory.
    """
    
    def __init__(self):
        
        path = os.getcwd()
        
        jog_file_path = find_file(JOG_FILE_NAME, path, MAX_CONFIG_FILE_SEARCH_DEPTH)
        project_dir = os.path.dirname(jog_file_path)
        
        self.project_dir = project_dir
        self.jog_file_path = jog_file_path
        self.config_file_path = os.path.join(project_dir, CONFIG_FILE_NAME)
        self.env_config_file_path = os.path.join(project_dir, ENV_CONFIG_FILE_NAME)
    
    def get_tasks(self):
        """
        Import the located task definition file as a Python module and return
        its inner ``tasks`` dictionary. Raise ``TaskDefinitionError`` if no
        ``tasks`` dictionary is defined in the imported module.
        
        :return: The task definition file's dictionary of tasks.
        """
        
        spec = spec_from_file_location('jog', self.jog_file_path)
        jog_file = module_from_spec(spec)
        spec.loader.exec_module(jog_file)
        
        try:
            return jog_file.tasks
        except AttributeError:
            raise TaskDefinitionError(f'No tasks dictionary defined in {JOG_FILE_NAME}.')
    
    def get_task_settings(self, task_name):
        """
        Locate any config file/s in the project directory, parse the file/s and
        return a collection of the settings corresponding to ``task_name``. If
        no such settings exist, return an empty collection.
        
        :return: The settings collection for the given task, as a
            ``configparser.SectionProxy`` object.
        """
        
        config_file = configparser.ConfigParser()
        config_file.read((self.config_file_path, self.env_config_file_path))
        
        section = f'{CONFIG_BLOCK_PREFIX}:{task_name}'
        
        # If the section does not exist, add a dummy one. This allows this
        # method to always return a value of a consistent type.
        if not config_file.has_section(section):
            config_file.add_section(section)
        
        return config_file[section]
