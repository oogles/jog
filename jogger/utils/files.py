import os
from fnmatch import fnmatch as std_fnmatch


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


def fnmatch(filename, patterns):
    """
    Test whether the ``filename`` string matches any of the strings in
    ``patterns``, using the standard library ``fnmatch()`` function internally
    to test each pattern. Return ``True`` if the filename matches or ``False``
    if it does not.
    
    :param filename: The filename to test.
    :param patterns: An iterable of patterns to test against.
    :return: ``True`` if a match is found, ``False`` if not.
    """
    
    return any(std_fnmatch(filename, pattern) for pattern in patterns)


def pathmatch(path, patterns):
    """
    Test whether the ``path`` string matches any of the strings in ``patterns``.
    ``path`` can be a relative file path, with both its basename and absolute
    path also tested against ``patterns``.
    
    :param path: The file path to test.
    :param patterns: An iterable of patterns to test against.
    :return: ``True`` if a match is found, ``False`` if not.
    """
    
    if fnmatch(path, patterns):
        return True
    
    basename = os.path.basename(path)
    if fnmatch(basename, patterns):
        return True
    
    absolute_path = os.path.abspath(path)
    return fnmatch(absolute_path, patterns)


def walk(from_path, exclude_patterns=None):
    """
    Yield all filenames under the ``from_path`` directory, optionally excluding
    any files/directories matching any of the pattern strings in
    ``exclude_patterns``.
    
    :param from_path: The root directory to walk.
    :param exclude_patterns: An iterable of patterns to test against.
    """
    
    if not exclude_patterns:
        # No exclusion patterns, perform simple directory walk
        for root, dirs, files in os.walk(from_path):
            for filename in files:
                yield os.path.join(root, filename)
    else:
        # Perform more complex directory walk, excluding files/directories
        # matching given exclusion patterns
        for root, dirs, files in os.walk(from_path, topdown=True):
            # Removing items from `dirs` will prevent `os.walk` from entering
            # those subdirectories. Iterate a copy so removals don't result in
            # an early exit from the loop.
            for directory in dirs.copy():
                joined = os.path.join(root, directory)
                if pathmatch(joined, exclude_patterns):
                    dirs.remove(directory)
            
            for filename in files:
                joined = os.path.join(root, filename)
                if not pathmatch(joined, exclude_patterns):
                    yield joined
