import configparser
import os
from importlib.util import module_from_spec, spec_from_file_location

try:
    import tomllib
except ImportError:
    tomllib = None

from jogger.exceptions import TaskDefinitionError

from .files import find_file

MAX_CONFIG_FILE_SEARCH_DEPTH = 8
JOG_FILE_NAME = 'jog.py'
CONFIG_TABLE = 'jogger'


def get_toml_config(file_path, table):
    
    with open(file_path, 'rb') as f:
        config = tomllib.load(f)
    
    for t in table.split('.'):  # support nested tables
        try:
            config = config[t]
        except KeyError:
            return {}
    
    return config


def get_ini_config(file_path, section):
    
    config = configparser.ConfigParser()
    config.read(file_path)
    
    try:
        config = config[section]
    except KeyError:
        return {}
    
    config_dict = dict(config)
    
    # Auto-convert boolean and list values
    for k, v in config_dict.items():
        if v.lower() in ('true', 'false'):
            config_dict[k] = config.getboolean(k)
        elif '\n' in v:
            v = [i.strip() for i in v.splitlines()]
            config_dict[k] = list(filter(None, v))
    
    return config_dict


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
        
        # Define paths to accepted config files, and the prefixes for the table
        # within each file, to which the name of the task will be added, that
        # contains the task settings.
        self.config_files = [
            (os.path.join(project_dir, 'pyproject.toml'), f'tool.{CONFIG_TABLE}.'),
            (os.path.join(project_dir, 'setup.cfg'), f'{CONFIG_TABLE}:')
        ]
        
        # Define paths to accepted environment-specific config files, and the
        # prefixes for the table within each file, to which the name of the
        # task will be added, that contains the task settings. Being
        # jogger-specific (as opposed to project-wide), tables don't
        # necessarily need to be prefixed.
        self.env_config_files = [
            (os.path.join(project_dir, 'joggerenv.toml'), ''),
            (os.path.join(project_dir, 'joggerenv.cfg'), f'{CONFIG_TABLE}:')
        ]
    
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
        return a dictionary of the settings corresponding to ``task_name``. If
        no such settings exist, return an empty dictionary.
        
        :return: The settings for the given task, as a dictionary.
        """
        
        settings = {}
        
        # Look first for project-wide config files, then for
        # environment-specific ones
        config_files_lists = [self.config_files, self.env_config_files]
        
        for file_list in config_files_lists:
            for path, table_prefix in file_list:
                if os.path.exists(path):
                    ext = os.path.splitext(path)[-1]
                    
                    if ext == '.toml' and tomllib:
                        config = get_toml_config(path, f'{table_prefix}{task_name}')
                        if config:
                            settings.update(config)
                            break
                    elif ext != '.toml':  # assume a configparser-compatible format
                        config = get_ini_config(path, f'{table_prefix}{task_name}')
                        if config:
                            settings.update(config)
                            break
        
        return settings
