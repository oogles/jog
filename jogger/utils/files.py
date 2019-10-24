import os


def find_file(target_file_name, from_path, max_search_depth=16):
    """
    Search upwards from ``from_path`` looking for ``target_file_name``,
    through a maximum of ``max_search_depth`` parent directories. Raise
    ``FileNotFoundError`` if the target file is not located.
    
    :param target_file_name: The filename of the target file.
    :param from_path: The directory in which to begin the search.
    :param max_search_depth: The maximum number of parent directories to search
        up through.
    :return: The absolute path of the located file.
    """
    
    path = from_path
    matched_file = None
    depth = 0
    
    while path and depth < max_search_depth:
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
