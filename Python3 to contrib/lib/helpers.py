#
# Codasip Ltd
#
# CONFIDENTIAL
#
# Copyright 2017 Codasip Ltd
#
# All Rights Reserved.
#
# NOTICE: All information contained in this file, is and shall remain the property of Codasip Ltd
# and its suppliers, if any.
#
# The intellectual and technical concepts contained herein are confidential and proprietary to
# Codasip Ltd and are protected by trade secret and copyright law.  In addition, elements of the
# technical concepts may be patent pending.
#
# Author: Milan Skala
# Desc: Helper functions, usable from plugins and tests
#
import argparse
import errno
from gettext import gettext as _ # argparse compatibility
import inspect
import itertools
import os
import re
import shutil
import stat

from mastermind.lib.utils import is_iterable, parse_cmdline_data, walklevel



class ArgumentParser(argparse.ArgumentParser):
    """Customized argument parser.
    
    Parser is able to ignore unknown arguments.
    """
    
    def parse_args(self, args=None, namespace=None, ignore_unknown=True, auto_split=True):
        """Parse arguments.
        
        When ``args`` is ``None``, then arguments from commandline are used by parser.
        
        :param args: Arguments to parse. If ``None``, then `sys.argv` is used.
        :param namespace: Namespace instance. If ``None``, then a new instance will be 
            created.
        :param ignore_unknown: If ``True`` then do not throw error on unknown arguments.
        :param auto_split: If ``True`` then split argument value by ``,`` symbol. This is applied
            only when argument's action is **append**.
        :type args: list
        :type namespace: :py:class:`~argparse.Namespace`
        :type ignore_unknown: bool
        :type auto_split: bool
        :return: Tuple (args, argv) if ``ignore_unknown`` is ``True`` else args. Args are parsed known
            arguments. Argv is a list containing unknown arguments.
        """
        args, argv = self.parse_known_args(args, namespace)
        
        if argv and not ignore_unknown:
            msg = _('unrecognized arguments: %s')
            self.error(msg % ' '.join(argv))
        
        # Split argument values by a comma
        if auto_split:
            for action in self._option_string_actions.values():
                # Read parsed values
                argval = getattr(args, action.dest, None)
                # Available only for 'append' action 
                if argval and isinstance(action, argparse._AppendAction):
                    result = map(lambda x: x.split(','), argval)
                    # Flatten the result list
                    result = [item for sublist in result for item in sublist]
                    setattr(args, action.dest, result)

        return (args, argv) if ignore_unknown else args

class Cache:
    """Wrapper object for test cache"""
    
    def __init__(self, dir, create=True):
        self.dir = dir
        
        if create and not os.path.isdir(dir):
            os.makedirs(dir)
    
    def purge(self):
        """Wipe cache content"""
        # read-only files cause problem on windows
        # define handler which changes permissions on error
        # and tries to remove again
        def remove_read_only(func, path, exc):
            excvalue = exc[1]
            if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
                # 0777
                os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) 
                func(path)
            else:
                raise
        
        if os.path.isdir(self.dir):
            shutil.rmtree(self.dir, onerror=remove_read_only)
        
def configure(item, configuration):
    """
    Override ``codal.conf`` options of :py:class:`~codasip.CodalProject` or 
    :py:class:`~codasip.CodalModel`.
    Automatically handles per-model configuration keys (e.g. `sdk`).
    
    :param item: An instance to configure.
    :param configuration: Dictionary containing options to override codal.conf.
    :type item: :py:class:`~codasip.CodalProject` or :py:class:`~codasip.CodalModel`
    :type configuration: dict
    """
    def event_model_init(event, model):
        # Tuple of keys which can be used multiple times (multiple="yes" in dtd.xml)
        multiple_keys = ('codal', 'sdk', 'compiler', 'extern')
        for key, value in configuration.items():
            if key.startswith(multiple_keys):
                option, k = key.split('.')
                c = model.config.find(option, model.id, create=True)
            else:
                c, k = model.config, key
            
            c[k] = value
    item = getattr(item, "project", item)
    # Add event hook so model is configured automatically right before task build.
    # Hook is necessary for correct setting of keys which are used during model
    # analysis, e.g. codal.args.
    item.event_hooks['model_init'] = []
    item.add_event_hook('model_init', event_model_init)
    # Configure models for the first time so caller can work with configured project
    for model in item.list_models():
        event_model_init(None, model)

def generate_combinations(dict, id_generator=None, filters=None, config=None):
    """
    Generate list of combinations from dictionary. If the value in a dictionary
    is list or tuple with n elements, then n single-valued dictionaries will be
    generated. In other words, it does permutations of all values.
     
    :param dict: Dictionary to process.
    :param id_generator: Function which will be applied on each pair in generated combination
                         to build unique id of given combination. Function expects 2 arguments
                         (key and value from combination) and must return string
                         or ``None`` if the pair should not be present in the id.
    :param filters: Function or list of functions for defining constraints on generated combinations. Function(s)
                    expect one or two arguments - generated combination and optional ``config``. If ``config`` argument is
                    available, then it represents an instance of pytest Config object. It must return ``True`` if 
                    combination is valid or ``False``  if combination should be filtered.
    :param config: Pytest Config object.
    :type dict: dict
    :type id_generator: function
    :type filter: function or list
    :type config: Pytest Config
    :return: Tuple containing generated combinations and list of ID's for each combination.
    :rtype: tuple
    :raises `~exceptions.ValueError`: If duplicate id is found.
    
    :Examples:
    
    Defining functions for examples
    
    .. code-block:: python
    
        def id_gen(key, value):
            return str(value)
    
        def filter_func(combination):
            if combination.get('key1') == 1:
                return False
            return True
        
        d = {'key1': [1, 2, 3], 'key2': 'a'}
    
    Default behaviour 
    
    >>> generate_combinations(d)
    ([{'key1': 1, 'key2': 'a'}, {'key1': 2, 'key2': 'a'}, {'key1': 3, 'key2': 'a'}], # combinations
    ['key1:1,key2:a', 'key1:2,key2:a', 'key1:3,key2:a']) # identifiers
    
    Example of using ``filter`` and ``id_generator`` arguments.
         
    >>> generate_combinations(d, id_gen, filter_func)
    [{'key1': 2, 'key2': 'a'}, {'key1': 3, 'key2': 'a'}], # combinations
    ['2,a', '3,a'] # identifiers
    """
    def default_generator(key, value):
        """
        If option is boolean type and is True, then only key is shown,
        if False, key is ignored. Otherwise show key and value.
        """
        if value is True:
            return key
        elif value is False:
            return None
        else:
            return key + ':' + str(value)

    def generate_id(config, fn):
        """Build string id based on combination"""        
        fields = []
        for key, value in config.items():
            part = fn(key, value)
            # Ignore empty and 'None' parts
            if not part:
                continue
            fields.append(part)
        return ','.join(fields)
    ###################################################
    if not dict:
        return [], []
    if id_generator is None:
        id_generator = default_generator
    
    # Preprocess filters
    filter_args = {}
    if filters:
        if not is_iterable(filters):
            filters = [filters]

        for f in filters:
            argnames = inspect.getargspec(f)[0]
            assert 1 <= len(argnames) <= 2, "Filter function {} must have 1 or 2 arguments".format(f.__name__)
            filter_args[f] = (config, ) if len(argnames) == 2 else ()
    
    # Split keys and values to sequential objects
    # so we can combine them later again.
    keys = []
    values = []
    for k, v in dict.items():
        if not is_iterable(v):
            v = [v]
        keys.append(k)
        values.append(v)
    
    # Generate combinations
    combinations = []
    ids = []
    for c in itertools.product(*values):
        combination = {}
        # Assign values to their appropriate keys
        for i, val in enumerate(c):
            key = keys[i]
            combination[key] = val
        
        if filters and not all([f(combination, *args) for f, args in filter_args.items()]):
            continue
        combinations.append(combination)
        id = generate_id(combination, id_generator)
        if id and id in ids:
            duplicates = combination, combinations[ids.index(id)]
            raise ValueError(("Duplicate id: '{}'\nCombination 1: {} \nCombination2: {}".format(id, *duplicates)))
        ids.append(id)
    
    return combinations, ids


def get_metafunc_id(metafunc):

    metafunc_id = []
    for attr in ['module', 'cls', 'function']:
        value = getattr(metafunc, attr, None)
        if value is not None:
            if attr == 'module':
                metafunc_id.append(value.__name__.split('.')[-1])
            else:
                metafunc_id.append(value.__name__)
    return '::'.join(metafunc_id)

