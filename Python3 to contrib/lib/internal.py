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
# Desc: Internal mastermind utilities
#
from collections import Iterable
from copy import copy as objcopy, deepcopy
import inspect
import os
import pytest
from _pytest.fixtures import FixtureDef
import re
import sys
import tempfile

from mastermind.lib import ITEM2TITLE
from mastermind.lib.exceptions import (FixtureManagerException, MarkerArgumentException,
                                       MarkerOptionTypeError, ToolBuildError)
from mastermind.lib.utils import copy, extract, info, is_iterable, grep, warning, rmtree
from mastermind.lib.statuses import (Status, StatusInternal, status_classes, STATUS_FAILED,
                                     STATUS_BUILDERROR, STATUS_TIMEOUT, 
                                     STATUS_PHASE_CALL)

class FixtureManager(object):
    """Class for dynamic fixture managing."""
    
    # Ordered pytest scopes 
    SCOPES = ('session', 'module', 'class', 'function')
    
    def __init__(self, config):
        self.config = config
        self.debug = config.getoption('debug')
    
    def register_dynamic_fixtures(self, metafunc, scope, names=None, prefix='dynamic_', default_scope='function'):
        """
        Search for requested ``names`` in fixturenames and add dynamic-scoped fixtures.
        A dynamic-scoped fixture will be named ``prefix + name``. For example when ``name`` is `sdk`, then default
        fixture name will be `dynamic_sdk` with the requested scope.
        For making dynamic fixtures usable, multiple implementations must exist (one for each requested scope).
        The naming convention of implementations is following: `<scope>_<name>`, e.g. `function_sdk`, `class_sdk`, etc.
                
        :param metafunc: Pytest Metafunc object.
        :param scope: Scope of generated fixture.
        :param names: List of arguments which use dynamic fixtures. By default all arguments.
        :param prefix: Dynamic fixture prefix.
        :param default_scope: Scope to use when any fixture function with 'scope' has not been found.
        :type scope: str
        :type names: list, str or None
        :type prefix: str
        :type default_scope: str
        :todo: default_scope argument is now ignored.
        
        :Examples:
         
        Dynamic fixtures are usable in cases when you need to use fixture, where the scope is 
        based on some condition and different implementations are desired for each scope. 
        Let us define the following fixtures and ``pytest_generate_tests`` hook.
        
        Note that each definition may have different signature.
        
        .. code-block:: python
            
            def function_server(dependency_x):
                ...
            
            def class_server(request, dependency_y):
                ...
            
            def server(dynamic_server):
                ...
                
            def pytest_generate_tests(metafunc):
                
                if 'server' in metafunc.fixturenames:
                    manager = FixtureManager(metafunc.config)
                    
                    # Scope is determined by use_class marker
                    if metafunc.has_marker('use_class'):
                        scope = 'class'
                    else:
                        scope = 'function'
                
                    manager.register_dynamic_fixtures(metafunc, scope, names='server')
            
        When a test function is marked by `use_class` marker, then ``class_server`` implementation is used,
        otherwise ``function_server`` implementation is called before executing server fixture.
        
        .. warning::
            ``FixtureManager`` does not change scope of any fixture dependencies. This responsibility is left
            for user to solve.
        """
        # By default search in all fixturenames
        if names is None:
            names = metafunc.fixturenames
        elif not is_iterable(names):
            names = [names]
        
        for name in names:
            # Test if name is really a fixture
            fixturedef = metafunc._arg2fixturedefs.get(name, [None])[0]
            if fixturedef is None:
                continue
            # Get list of functions from the fixture module
            module = sys.modules[fixturedef.func.__module__]
            functions = inspect.getmembers(module, predicate=inspect.isfunction)
            
            for fname, fobj in functions:
                # Match fixture basename and scope
                if fname.startswith(scope) and fname.endswith(name):
                    # Generate fixture and add
                    fixture = pytest.fixture(scope=scope, name=prefix + name)(fobj)
                    self.add_fixture(metafunc, prefix + name, fixture, scope)
                    break

    def add_fixture(self, metafunc, argname, func, scope='function', rewrite=True, baseid=None,
                    params=None, unittest=False, ids=None):
        """
        Add a new fixture to metafunc.
        
        :param metafunc: Pytest Metafunc object.
        :param argname: Fixture name.
        :param func: Function object to call while executing fixture.
        :param scope: Fixture scope.
        :param rewrite: If ``True``, then rewrite existing fixture with ``argname`` name. 
        :param baseid: Fixture baseid.
        :param param: Fixture params.
        :param unittest: ``True`` if fixture is unittest.
        :param ids: Fixture ids.
        :type argname: str
        :type func: function
        :type scope: str
        :type rewrite: bool
        :type baseid: str or None
        :type unittest: bool
        :type ids: list
        :raises FixtureManagerException: If ``metafunc`` already has the fixture 
            and ``rewrite`` is not enabled.
        """
        
        if argname in metafunc._arg2fixturedefs and not rewrite:
            raise FixtureManagerException("Fixturename '{}' already defined".format(argname))
        
        fd = FixtureDef(metafunc.config.pluginmanager.get_plugin('funcmanage'),
                        baseid=baseid,
                        argname=argname,
                        func=func,
                        scope=scope,
                        params=params,
                        unittest=unittest,
                        ids=ids)
        
        # Add fixture arguments to metafunc dependencies
        for arg in fd.argnames:
            if arg not in metafunc.fixturenames:
                metafunc.fixturenames.append(arg)
        metafunc._arg2fixturedefs[argname] = (fd,)
    
    def update_fixture(self, metafunc, name, **kwargs):
        """
        Override ``metafunc`` attributes.
        
        :param metafunc: Pytest ``Metafunc`` object
        :param name: Fixture name
        :param kwargs: Attributes and values which will be updated.
        :type name: str
        
        .. warning::
        
            Method should be used with caution. Invalid values
            may caused fixture corruption and lead to undesired 
            behaviour.
        """
        fixture = self.get_fixture(metafunc, name)
        for key, value in kwargs.items():
            if key == 'scope':
                setattr(fixture, 'scopenum', self.SCOPES.index(value))
            setattr(fixture, key, value)

        metafunc._arg2fixturedefs[name] = (fixture,)
        
    def get_fixture(self, metafunc, fixturename):
        """
        Find metafunc fixturedef.
        
        :param metafunc: Pytest ``Metafunc`` object.
        :param fixturename: Fixture name in test
        :type fixturename: str
        
        :raises `~mastermind.lib.exceptions.FixtureManagerException`: If fixture is not found.
        """
        if fixturename not in metafunc._arg2fixturedefs:
            raise FixtureManagerException("Fixture {} not found for {}".format(fixturename, metafunc.function.__name__))
        return metafunc._arg2fixturedefs[fixturename][-1]


class MarkerGroup():
    """
    Class for detecting and processing Pytest markers.
    
    :ivar marker_name: Pytest marker name.
    :ivar varargs: ``True`` if marker supports variable arguments.
    :ivar varkwargs: ``True`` if marker supports variable keyword arguments.
    :ivar values:
    :ivar args: Marker arguments.
    :ivar kwargs: Marker keyword arguments. 
    :ivar markers: Instances of :py:class:`MarkerOption` which are supported by
    this Marker Group.
    :ivar _options: Set of supported option names.
    :vartype marker_name: str
    :vartype varargs: bool
    :vartype varkwargs: bool
    :vartype values: dict
    :vartype args: tuple
    :vartype kwargs: dict
    :vartype markers: set
    :vartype _options: set
    
    """

    def __init__(self, marker_name, *args, **kwargs):
        self.marker_name = marker_name
        self.varargs = kwargs.get('varargs', False)
        self.varkwargs = kwargs.get('varkwargs', False)
        self.values = {}
        self.args = ()
        self.kwargs = {}
        self.markers = set()
        self._options = set()
        
        for marker_option in args:
            self.add_option(*marker_option)
    
    def add_option(self, *args, **kwargs):
        """Add support for marker option.
        
        Argument ``args`` contains either MarkerOption instance or arguments
        for it's initialization. See :py:class:`MarkerOption` for available
        arguments. Note that ``marker_name`` is automatically inherited from
        ``MarkerGroup``. 
        """
        if args and isinstance(args[0], MarkerOption):
            option = args[0]
            assert option.marker_name == self.marker_name, """Marker names of MarkerGroup 
                                                            and Marker Option must match.
                                                           """
        else:
            option = MarkerOption(self.marker_name, *args, **kwargs)
        
        self.markers.add(option)
        self._options.add(option.option_name)
    
    def find_options(self, metafunc, filter_known_kwargs=True):
        """
        Find marker options for pytest function with type checking.
        
        :param metafunc: Pytest Metafunc object.
        :param filter_known_args: If ``True``, then delete registered options
        from marker keywords and preserve only unregistered ones.
        :type filter_known_args: bool
        :return: :py:class:`MarkerGroup` instance with detected marker option values.
        :rtype: :py:class:`MarkerGroup`
        """
        # Create copy, so this object is reusable.
        result = objcopy(self)
        # Detect option values and validate types
        for marker_option in self.markers:
            result.values[marker_option.option_name] = marker_option.find_option(metafunc)
        
        # Detect variable arguments and keyword arguments
        marker_obj = getattr(metafunc.function, self.marker_name, None)
        if marker_obj:
            m_args, m_kwargs = deepcopy(marker_obj.args), deepcopy(marker_obj.kwargs)
            
            if not self.varargs and m_args:
                msg = 'Variable argument are not supported by this marker, got: {}.'
                raise MarkerArgumentException(result, metafunc, msg, ', '.join(map(str, m_args)))
        
            if not self.varkwargs:
                errorous = [key for key in m_kwargs if key not in self._options]
                if errorous:
                    msg = 'Variable keyword arguments are not supported by this marker, unknown keys: {}.'
                    raise MarkerArgumentException(result, metafunc, msg, ', '.join(errorous))
            
            # Remove registered options from keyword arguments
            if filter_known_kwargs:
                for kw in marker_obj.kwargs:
                    if kw in self._options:
                        del m_kwargs[kw]
            
            result.args = m_args
            result.kwargs = m_kwargs
        
        return result
    
    def get(self, key):
        """Get marker option"""
        return self.values.get(key)
    
    def get_value(self, option, default=None):
        """Syntax sugar for option value extraction
        
        :param option: Option name.
        :param default: Default value if option is not found.
        :return: Extracted value or default if option is not found.
        """
        res = self.get(option)
        if res is None:
            return default
        return res.value

    def get_values(self, *options):
        """Extract option values.
        
        :param options: Options to extract. 
        :return: Dictionary containing ``options`` as keys and extracted values
        for each corresponding option. If option's value is ``None``, then
        that option is skipped and is not present in the returned dictionary.
        :rtype: dict
        """
        if not options:
            options = self._options
        return {option: self.get_value(option) for option in options 
                if self.get_value(option) is not None}
    
    def get_scope(self, option, default=None):
        """Syntax sugar for option scope extraction
        
        :param option: Option name.
        :param default: Default scope if option is not found.
        :return: Extracted scope or default if option is not found.
        """        
        res = self.get(option)
        if res is None:
            return default
        return res.scope
    
    def get_scopes(self, *options):
        """Extract option scopes.
        
        :param options: Options to extract. 
        :return: Dictionary containing ``options`` as keys and extracted scopes
        for each corresponding option.
        :rtype: dict
        """
        if not options:
            options = self._options
        return {option: self.get_value(option) for option in options 
                if self.get_value(option) is not None}        
        if not options:
            options = self._options
        return {option: self.get_scope(option) for option in options}
    
    def __repr__(self):
        return 'MarkerGroup(marker_name=%s, varargs=%s, varkwargs=%s, options=%s)' % (self.marker_name, self.varargs, self.varkwargs, self._options)


class MarkerOption():
    """Single pytest marker option representation.
    
    :ivar marker_name: Pytest marker name.
    :ivar option_name: Option name (keyword argument of marker).
    :ivar static_name: Static variable name for class and module scopes.
    :ivar types: List of supported types for option.
    :ivar value: Extracted option value.
    :ivar scope: Extracted value scope.
    """

    def __init__(self, marker_name, option_name=None, static_name=None, valid_types=None, choices=None):
        """Constructor
    
        :param marker_name: Pytest marker name.
        :param option_name: Option name (keyword argument of marker).
        :param static_name: Static variable name for class and module scopes.
        :param valid_types: List of supported types for option.
        :type marker_name: str
        :type option_name: str
        :type static_name: str
        :type valid_types: tuple or list
        """
        self.marker_name = marker_name
        self.option_name = option_name
        self.static_name = static_name
        self.types = valid_types
        self.choices = choices
        
        self.value = None
        self.scope = None
    
    def __repr__(self):
        return 'MarkerOption(name=%s, option=%s, static_name=%s, types=%s' % (
            self.marker_name, self.option_name, self.static_name, self.types)
    
    def find_option(self, metafunc):
        """Extract 
        
        :param metafunc: Pytest metafunc object.
        :return: :py:class:`MarkerOption` with extracted values and scope.
        :rtype: :py:class:`MarkerOption`
        """
        value, scope = self._get_value(metafunc)
        
        # Copy self to make MarkerOption reusable.
        result = objcopy(self)
        result.value = value
        result.scope = scope
        
        if value is None:
            return result
        
        # Check value type
        invalid_values = self.validate_type(value)
        if invalid_values:
            raise MarkerOptionTypeError(result, metafunc)
        
        invalid_values = self.validate_value(value)
        if invalid_values:
            raise MarkerArgumentException(result, metafunc)
        
        return result
    
    def _get_value(self, metafunc):
        """
        Process options set on testcase to find most priority one. First markers on function or class
        with given name and option (e.g. @pytest.mark.marker_name(option_name=....) ) are used, then 
        static variable in class or module named ``static_name`` is searched for. If option is not found,
        None is returned. For each option extract it's scope as well.
        """
        value, scope = None, None
        # highest priority has marker on the test case
        if hasattr(metafunc.function, self.marker_name):
            marker = getattr(metafunc.function, self.marker_name)
            value, scope = marker.kwargs.get(self.option_name), 'function'
        if value is None:
            # next priority is class static variable
            value, scope = getattr(metafunc.cls, self.static_name, None), 'class'
        if value is None:
            # last priority is module global variable
            value, scope = getattr(metafunc.module, self.static_name, None), 'module'
        if value is None:
            scope = None
    
        return value, scope
    
    def validate_type(self, value):
        """Check if value is valid.
        
        :param: Value to validate. Can be either single value
        or an iterable (list, tuple, set).
        :return: List of invalid values.
        :rtype: list of invalid values.
        """
        # Nothing to check, all types are allowed
        if self.types is None:
            return []
        
        option_types = self.types[:]
        # Detect if iterable objects are supported
        iterable = (Iterable in option_types)

        # Value cannot be iterable, but it is.
        if not iterable and is_iterable(value):
            return value
        
        if not is_iterable(value):
            value = [value]
        
        if iterable:
            option_types.remove(Iterable)
        
        invalid_values = []
        for v in value:
            if any([isinstance(v, t) for t in option_types]):
                continue
            invalid_values.append(v)
        
        return invalid_values
    
    def validate_value(self, value):
        if not self.choices:
            return []
        
        if not is_iterable(value):
            value = [value]
            
        return [v for v in value if v not in self.choices]
        
    
class OptionFinder():
    """Class for options detection.
    
    """

    def __init__(self, marker_groups):
        assert all([isinstance(group, MarkerGroup) for group in marker_groups])
        
        self.groups = marker_groups
        
        self._marker_names = set([group.marker_name for group in marker_groups])
    
    def find_options(self, metafunc, options=None, filter_known_kwargs=True):
        # Find all available options
        if options is None:
            options = self._marker_names
        else:
            # Get slice of available options
            if not is_iterable(options):
                options = [options]
            _options = set()
            
            for o in options:
                if o not in self._marker_names:
                    warning('Unknown marker option {}, ignoring.'.format(o))
                    continue
                _options.add(o)
            options = _options
        
        if not options:
            warning("No options to detect, either got empty options list unsupported " \
                    "options have been passed")
            return None

        # Detect options
        result = {}
        for marker_name in options:
            group = self.find_group(marker_name)
            result[marker_name] = group.find_options(metafunc, filter_known_kwargs)
        
        # Do not return dict when single option was requested.
        if len(options) == 1:
            return result[marker_name]
        
        return result

    def find_group(self, name):
        for g in self.groups:
            if g.marker_name == name:
                return g

class StatusClasifier():
    """Clasifier detecting status from test result.
    
    :ivar _config: Pytest :py:class:`~pytest.config.Config` instance.
    :ivar _classes: Set of classes representing statuses. These classes are
        used to find appropriate status according to test result.
    """
    STATUS_OK_ID = (StatusInternal, STATUS_FAILED)
    
    def __init__(self, config=None):
        self._config = config
        self._classes = status_classes()
    
    def find_status_class(self, item_id=None, item_name=None, precise=True):
        """"""
        for cls in self._classes:
            if item_id is not None and cls.ITEM_ID != item_id:
                continue
            if (item_name is not None and ((precise and cls.ITEM_NAME != item_name)
                or (not precise and not re.search('\s'+cls.ITEM_NAME+'\s', item_name.lower())))):
                continue
            return cls

    def _get_passed_status(self):
        cls, status_id = self.STATUS_OK_ID
        return cls.status(status_id)

    def _get_general_failed_status(self, phase=None):
        return StatusInternal.status(STATUS_FAILED, phase)

    def clasify(self, from_xml, *args, **kwargs):
        if from_xml:
            return self._clasify_xml(*args, **kwargs)
        else:
            return self._clasify(*args, **kwargs)

    def _clasify(self, item, call, report):
        if report.passed:
            return self._get_passed_status()
        
        cls = None
        # When test fails during tool execution, then report has 'tool' attribute
        # which holds the name of failed tool.
        if hasattr(report, 'tool'):
            cls = self.find_status_class(item_name=report.tool)
        
        if cls is None:
            # By default use methods implemented in Clasifier
            cls = self
        # Get appropriate method for clasification according to raised exception.
        method = getattr(cls, '_clasify_' + call.excinfo.typename, cls._clasify_other)
        return method(item, report, call.excinfo.value)

    def _clasify_xml(self, result):
        if result.get('skipped'):
            return None
        if result.get('passed'):
            return self._get_passed_status()
        # Failed
        
        result_log = result.get('log')
        
        match_exception = re.search('E\s+(?P<excname>\w+(Error|Exception))', result_log)
        cls = self.find_status_class(item_name=result_log, precise=False)
        
        if cls and match_exception:
            excname = match_exception.group('excname')
            method = getattr(cls, '_clasify_xml_' + excname, cls._clasify_xml_other)
            return method(result)
        
        return self._get_general_failed_status(STATUS_PHASE_CALL)
        
    def _failed_task_name(self, exc):
        """
        Extract failed task name from exception. This task name can be 
        used for status code detection later.
        
        :param exc: Exception, which was raised during tool generation
        :type exc: :py:class:`~mastermind.lib.exceptions.ToolBuildError`
        :return: Task name, which failed.
        """
        import doit
        if isinstance(exc, doit.exceptions.InvalidCommand):
            return exc.not_found.split('.')[0]
        # Extract task name from error output
        # Doit provides standard error message format, which is for example:
        # fatal: TaskFailed - task:model.ia:codasip_urisc.ia
        for line in exc.stderr.split('\n')[::-1]:
            if line.startswith('fatal:'):
                m = re.search('\s(\w+)\.', line)
                if m:
                    return m.group(1)
        # If we could not detect task name from standard error, then
        # try standard output. Doit framework prints out task name 
        # before it's execution, for example:
        # .  Model Compilation codasip_urisc.ia
        # For task name detection a dictionary with mapping of
        # task name to its user-friendly description is used.
        for line in exc.stdout.split('\n')[::-1]: 
            if line.startswith('.'):
                for task, title in ITEM2TITLE.items():
                    if title in line:
                        return task

    def _clasify_other(self, item, report, exc):
        """General method for detection of statuses"""
        return StatusInternal._clasify_other(item, report, exc)

    def _clasify_InvalidCommand(self, item, report, exc):
        return StatusInternal._clasify_InvalidCommand(item, report, exc)


    def _clasify_ToolBuildError(self, item, report, exc):

        item_name = self._failed_task_name(exc)
        if item_name:
            # Detect status class from item name
            status_class = None
            for cls in self._classes:
                if cls.search_task(item_name):
                    status_class = cls
                    break
            if status_class:
                return status_class._clasify_ToolBuildError(item, report, exc)
        # Unable to detect task, return general build error
        return StatusInternal.status(STATUS_BUILDERROR, report.when)

class TestingType():

    def __init__(self, config, type):
        self._config = config
        self.type = type
    
    def is_runnable(self, item):
        options = self._config.option_finder.find_options(item, 'test_type').get_values()
        
        if options:
            dct = {True: options.get('enable'),
                   False: options.get('disable')}
            
            for should_match, values in dct.items():
                if not values:
                    continue
                if not is_iterable(values):
                    values = [values]
                if (self.type in values) != should_match: 
                    msg = "Test is {} for testing type(s) {}. Current testing type is '{}'".format('enabled' if should_match else 'disabled',
                                                                                            'and '.join(values), self.type
                                                                                            )
                    item.add_marker(pytest.mark.skip(reason=msg))


def get_project_configurations(project_path, pattern=None, is_preset=False):
    """Get list of available configurations for project.
    
    :param project_path: Path to project
    :param pattern: List of regular expressions which must be matched with found configurations.
                    If ``None``, then no filtering is applied. All regular expression must
                    be matched to mark a configuration as valid.
    :param is_preset: If ``True``, then configurations are searched in 'presets' directory
                      located in ``project_path``. Otherwise the project in that path is
                      loaded and configurations are extracted from supported options.
    :type project_path: str
    :type pattern: str of list
    :type is_preset: bool
    :return: List of project configurations matching the ``pattern``. If ``pattern`` is ``None``,
             then return all found configurations.
    """
    if pattern and not is_iterable(pattern):
        pattern = [pattern]
    
    def _find_presets():
        """Search configuration files"""
        presets_path = os.path.join(project_path, 'presets')
        for root, _, files in os.walk(presets_path):
            for fname in files:
                preset = os.path.relpath(os.path.join(root, fname), presets_path)
                if pattern and not all([re.search(p, preset) for p in pattern]): 
                    continue
                yield os.path.join(root, fname)
    
    def _find_configs():
        """List all available configurations and select those matching ``pattern``"""
        from codasip.build.options import product as options_product
        from codasip.build.project import ProjectBase

        project = ProjectBase.load(project_path)
        metadata = project.options_metadata
        
        option_constraints = metadata.get_pattern_values()
        for current_options in options_product(metadata, option_constraints):
            arch_tuple = current_options.get_configuration()
            if pattern and not all([re.search(p, arch_tuple) for p in pattern]): 
                continue
            
            yield arch_tuple
    
    configs = _find_presets() if is_preset else _find_configs()
    return list(configs)

    
def load_ip_package(source, destination, clean=True):
    """Prepare IP package for execution.
    
    Extract IP package from ``source``. Then detect package content (sdk, hdk, ...)
    and build list of arguments for Mastermind execution.
    
    :param source: Path to IP package or directory containing the package.
    :param destination: Directory where the package will be extracted
    :param clean: If ``True`` then clean ``destination`` directory if it exists.
    :type source: str
    :type destination: str
    :type clean: bool
    :return: Arguments for Mastermind, which are based on IP package capabilities. 
    :rtype: list
    :raises AssertionError: If ``source`` does not exist or no IP package is found in ``source``.
    
    """
    assert os.path.exists(source), '{} does not exist'.format(source)
    
    if clean:
        if os.path.exists(destination):
            rmtree(destination)
    
    # Try to find archive or extracted package
    if os.path.isdir(source):
        packages = [item for item in os.listdir(source) if re.search('.+CORE.+', item)]
        assert len(packages) <= 1, "Multiple IP packages have been found in {}.".format(source)
        if packages:
            source = os.path.join(source, packages[0])
    
    if os.path.isfile(source):
        tempdir = tempfile.mkdtemp(prefix='mm_ip_package_')
        info("Extracting package {} to temporary directory {}", source, tempdir)
        extract(source, tempdir)
        info("Copying IP package to {}", destination)
        # Get the archive basename. It may contain suffix '.FAILED' in case when testing
        # of the package has failed. Although the archived directory does not contain 
        # such suffix, so we have to remove it from basename.
        basename = os.path.splitext(os.path.basename(source.replace('.FAILED', '')))[0]
        if basename in os.listdir(tempdir):
            copy(os.path.join(tempdir, basename), destination)
        else:
            copy(tempdir, destination)
        info("Cleaning temporary directory")
        rmtree(tempdir, ignore_errors=True)

    # Traverse package and detect capabilities
    args = []
    for item in os.listdir(destination):
        if item in ('hdk', 'sdk'):
            args += ['--' + item, os.path.join(destination, item)]
        elif item == 'README.txt':
            configuration = list(grep('Configuration: ', os.path.join(destination, item)))
            assert len(configuration) <= 1, 'Config parse error'
            if configuration:
                configuration = configuration[0].strip().split()[1]
                args += ['--configuration', configuration]
    
    assert args, 'IP package does not contain any testable feature (sdk or hdk)'
    
    return args


def uvm_configuration_filter(configuration_dict, config):
    """Filter for uvm configurations.
    
    Removed configuration which do not match arguments from cmdline, e.g. using
    only certain HDL languages or RTL simulators.
    
    :param config: Pytest config object.
    :param configuration_dict: Tested configuration.
    :type configuration_dict: dict
    :return: ``False`` if ``configuration_dict`` should be filtered from execution, else ``True``. 
    :rtype: bool
    """
    from codasip import RTL_SIM_QUESTA, RTL_SIM_RIVIERA

    for key, value in configuration_dict.items():
        if key == 'rtl.language' and value not in config.hdl_languages:
            return False
        # rtl-simulation-tool and synthesis-tool are lists
        elif key == 'rtl.rtl-simulation-tool' and not any([v for v in value if v in config.rtl_simulators]):
            return False
        elif key == 'rtl.synthesis-tool' and not any([v for v in value if v in config.synthesis_tools]):
            return False
    
    # Filter simulators which are not supported on Windows system
    rtl_simulators = configuration_dict.get('rtl.rtl-simulation-tool')
    win_supported_sims = [RTL_SIM_QUESTA, RTL_SIM_RIVIERA]
    if rtl_simulators and os.name == 'nt' and any(sim not in win_supported_sims for sim in rtl_simulators):
        return False
        
    
    return True 
    
