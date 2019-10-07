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
# Desc: Predefined special markers. 
from collections import Iterable
import pytest
import os
import types

from mastermind.lib import TEST_TYPES
from mastermind.lib.internal import MarkerGroup, MarkerOption


try:
    from mastermind.lib.helpers import CODASIP_LIBRARIES
except ImportError:
    CODASIP_LIBRARIES = []    

####################################################################################################
# Get build type from cmdline
# Platform markers - skips test if marker
linux = pytest.mark.skipif(os.name=='nt', reason='Test is disabled on Windows platforms.')
"""Run test only on Linux platforms"""
windows = pytest.mark.skipif(not os.name != 'nt', reason='Test is disabled on Linux platforms.')
"""Run test only on Windows platforms"""

MARKER_OPTIONS = [MarkerGroup('project', ('asip', 'PROJECT_ASIP', [bool],),
                                         ('pattern', 'PROJECT_PATTERN', [str],),
                                         ('disable', 'PROJECT_PATTERN_DISABLE', [str],),
                              ),
                  MarkerGroup('model', ('ia', 'MODEL_IA', [bool],),
                                       ('asip', 'MODEL_ASIP', [bool],),
                                       ('top', 'MODEL_TOP', [bool],),
                                       ('pattern', 'MODEL_PATTERN', [str],),
                                       ('disable', 'MODEL_PATTERN_DISABLE', [str],),
                             ),
                  MarkerGroup('tools', ('configurations', 'TOOLS_CONFIGURATIONS', [dict],),
                                       ('filter', 'TOOLS_CONFIGURATIONS_FILTER', [types.FunctionType],),
                                       ('id_generator', 'TOOLS_CONFIGURATIONS_ID_GENERATOR', [types.FunctionType],),
                             ),
                  MarkerGroup('generate', ('combinations', 'GENERATE_COMBINATIONS', [dict],),
                                          ('filter', 'GENERATE_COMBINATIONS_FILTER', [types.FunctionType],),
                                          ('id_generator', 'GENERATE_COMBINATIONS_ID_GENERATOR', [types.FunctionType],),
                             ),
                  MarkerGroup('compiler', ('optimization', 'COMPILER_OPTIMIZATION', [Iterable, str, int],),
                                            *[(name.replace('-', '_'), 'COMPILER_' + name.replace('-', '_').upper(), [bool])
                                              for name in CODASIP_LIBRARIES]
                            ),
                  MarkerGroup('simulator', ('ia', 'SIMULATOR_IA', [bool],),
                                           ('debugger', 'SIMULATOR_DEBUGGER', [bool],),
                                           ('dump', 'SIMULATOR_DUMP', [bool],),
                                           ('profiler', 'SIMULATOR_PROFILER', [bool],),
                             ),
                  MarkerGroup('debugger', ('ia', 'DEBUGGER_IA', [bool],),
                                          ('codal_debugger', 'DEBUGGER_CODAL', [bool],),
                             ),
                  MarkerGroup('profiler', ('ia', 'PROFILER_IA', [bool],),
                             ),
                  MarkerGroup('randomgen', ('one_per_testcase', 'RANDOMGEN_ONE_PER_TESTCASE', [bool],),
                              varkwargs=True
                             ),
                  MarkerGroup('uvm',    ('hdl_languages', 'UVM_HDL_LANGUAGES', [Iterable, str],),
                                        ('rtl_simulators', 'UVM_RTL_SIMULATORS', [Iterable, str],),
                                        ('synthesis_tools', 'UVM_SYNTHESIS_TOOLS', [Iterable, str],),
                             ),
                  MarkerGroup('find_files', ('name', 'FIND_FILES_NAME', [str]),
                                            ('path', 'FIND_FILES_PATH', [str]),
                                            ('pattern', 'FIND_FILES_PATTERN', [Iterable, str]),
                                            ('exclude', 'FIND_FILES_EXCLUDE', [Iterable, str]),
                             ),
                  MarkerGroup('directory_collect', ('name', 'DIRECTORY_COLLECT_NAME', [str]),
                                                   ('path', 'DIRECTORY_COLLECT_PATH', [str]),
                                                   ('pattern', 'DIRECTORY_COLLECT_PATH', [Iterable, str]),
                                                   ('exclude', 'DIRECTORY_COLLECT_EXCLUDE', [Iterable, str]),
                             ),
                  MarkerGroup('test_metadata', varargs=True, varkwargs=True
                             ),
                  MarkerGroup('test_type', ('enable', 'TEST_TYPE_ENABLE', [Iterable, str], TEST_TYPES),
                                           ('disable', 'TEST_TYPE_DISABLE', [Iterable, str], TEST_TYPES),
                             ),
                ]
"""
List of supported options by Mastermind.


``@pytest.mark.project``

Filters test cases based on :class:`~codasip.CodalProject` properties

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
|       asip        |       PROJECT_ASIP         |           bool           |  If ``True``, then test case will be    |
|                   |                            |                          |  executed for asip project only.        |
|                   |                            |                          |  If ``False``, then test case will be   |
|                   |                            |                          |  executed for level project only.       |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
|      pattern      |     PROJECT_PATTERN        |           str            |  Regular expression, which must be      | 
|                   |                            |                          |  matched to execute test case for       |
|                   |                            |                          |  loaded project. If regular expression  |
|                   |                            |                          |  does not match project's **name**,     |
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
|      disable      |  PROJECT_PATTERN_DISABLE   |           str            |  Regular expression, which must NOT be  | 
|                   |                            |                          |  matched to execute test case for       |
|                   |                            |                          |  loaded project. If regular expression  |
|                   |                            |                          |  matches project's **name**, then       |
|                   |                            |                          |  test case is skipped.                  |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+

Examples:
    .. code-block:: python
        
        # Execute for asip project only (skips levels)
        @pytest.mark.project(asip=True)
        def test_project(project):
            ...

    .. code-block:: python
        
        # Execute only for Codix Berkelium
        @pytest.mark.project(pattern='codix_berkelium')
        def test_project(project):
            ...

    .. code-block:: python
        
        # Skip test for Codasip Urisc
        @pytest.mark.project(disable='codasip_urisc')
        def test_project(project):
            ...

``@pytest.mark.model``

Filters test cases based on :class:`~codasip.CodalModel` properties. 

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
|       asip        |        MODEL_ASIP          |           bool           |  If ``True``, then test case will be    |
|                   |                            |                          |  executed for asip models only.         |
|                   |                            |                          |  If ``False``, then test case will be   |
|                   |                            |                          |  executed for level models only.        |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
|        ia         |         MODEL_IA           |           bool           |  If ``True``, then test case will be    |
|                   |                            |                          |  executed for ia models only.           |
|                   |                            |                          |  If ``False``, then test case will be   |
|                   |                            |                          |  executed for ca models only.           |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
|        top        |         MODEL_TOP          |           bool           |  If ``True``, then test case will be    |
|                   |                            |                          |  executed for models which are on top   |
|                   |                            |                          |  of the model hierarchy. Models, which  |
|                   |                            |                          |  have a parent in a hierarchy are       |
|                   |                            |                          |  skipped for test case.                 |
|                   |                            |                          |  If ``False``, then test case is        |
|                   |                            |                          |  skipped for the top level models       |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
|      pattern      |       MODEL_PATTERN        |           str            |  Regular expression, which must be      | 
|                   |                            |                          |  matched to execute test case for       |
|                   |                            |                          |  loaded model. If regular expression    |
|                   |                            |                          |  does not match model's **design path**,|
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
|      disable      |    MODEL_PATTERN_DISABLE   |           str            |  Regular expression, which must NOT be  | 
|                   |                            |                          |  matched to execute test case for       |
|                   |                            |                          |  loaded model. If regular expression    |
|                   |                            |                          |  matches model's **design path**,       |
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+

Examples:
    .. code-block:: python
        
        # Execute for level models only (skips asip models)
        @pytest.mark.model(asip=False)
        def test_model(model):
            ...


    .. code-block:: python
        
        # Execute for ia models only (skips ca models)
        @pytest.mark.model(ia=True)
        def test_model(model):
            ...

    .. code-block:: python
            
        # When Mastermind is executed e.g. with project codix_berkelium_top, then the model hierarchy is as following.
        # Using option top will execute test case for models which are on top of the hierarchy. In this case, 
        # the top level models are codix_berkelium_top.ia and codix_berkelium_top.ca.
        #
        #                +-------------------------+
        #                |        PROJECT          |
        #                |                         |
        #                |   codix_berkelium_top   |
        #                |                         |
        #                +-------------------------+                         
        #                     /                 \
        #                    /                   \
        #                   /                     \
        #                  /                       \
        #                 /                         \
        #                /                           \                
        #  +-------------------------+   +-------------------------+
        #  |          LEVEL          |   |          LEVEL          |
        #  |                         |   |                         |
        #  | codix_berkelium_top.ia  |   | codix_berkelium_top.ca  |
        #  |                         |   |                         |
        #  +-------------------------+   +-------------------------+
        #               |                            |
        #               |                            |
        #               |                            |                
        #               |                            |                
        #               |                            |                
        #               |                            |                
        #               |                            |                
        #               |                            |                
        #   +-------------------------+   +-------------------------+
        #   |        ASIP             |   |        ASIP             |
        #   |                         |   |                         | 
        #   | codix_berkelium_top.ia. |   | codix_berkelium_top.ca. | 
        #   | codix_berkelium.ia      |   | codix_berkelium.ca      | 
        #   |                         |   |                         | 
        #   +-------------------------+   +-------------------------+ 
        @pytest.mark.model(top=True)
        def test_model(model):
            ...

    .. code-block:: python
        
        # Execute only for Codix Berkelium
        @pytest.mark.model(pattern='codix_berkelium')
        def test_model(model):
            ...

       
    .. code-block:: python
        
        # Skip test for Codasip Urisc
        @pytest.mark.model(disable='codasip_urisc')
        def test_model(model):
            ...

``@pytest.mark.tools``

Allows to override configuration from codal.conf and use it for tools generation.

.. note::

    Marker is available only when :class:`~codasip.CodalProject` has been loaded. If any option is used without project, 
    test case is skipped.

.. note::

    Options ``filter`` and ``id_generator`` must be used together with ``configuration`` option as these options allow 
    selecting subset of configurations from all possible configurations.

+------------------------+-------------------------------------+------------------+-----------------------------------------+
|      Option name       |       Static variable name          |    Data types    |               Description               |
|                        |                                     |                  |                                         |
+========================+=====================================+==================+=========================================+
|                        |                                     |                  |                                         |
| configurations         | TOOLS_CONFIGURATIONS                | | dict           |  Overrides codal configuration for test |
|                        |                                     |                  |  case. Dictionary keys are keys         |
|                        |                                     |                  |  identical to keys from codal.conf      |
|                        |                                     |                  |  and values are new values to set.      |
|                        |                                     |                  |  Value may be a single value or list of |
|                        |                                     |                  |  values.  If list of values is set,     |
|                        |                                     |                  |  then test case is executed for each    |
|                        |                                     |                  |  combination of configuration.          |
|                        |                                     |                  |                                         |
+------------------------+-------------------------------------+------------------+-----------------------------------------+
|                        |                                     |                  |                                         |
| filter                 | TOOLS_CONFIGURATIONS_FILTER         | | function       |  Function for certain configuration     | 
|                        |                                     |                  |  filtering. Function takes one parameter|
|                        |                                     |                  |  which is the current codal             |
|                        |                                     |                  |  configuration (from configurations     |
|                        |                                     |                  |  option). then test case is skipped.    |
|                        |                                     |                  |  ``True`` is returned if current        |
|                        |                                     |                  |  configuration is valid should be used  |
|                        |                                     |                  |  for tools generation. If ``False``     |
|                        |                                     |                  |  is returned, then current configuration|
|                        |                                     |                  |  is skipped.                            |
|                        |                                     |                  |                                         |
+------------------------+-------------------------------------+------------------+-----------------------------------------+
|                        |                                     |                  |                                         |
| id_generator           | TOOLS_CONFIGURATIONS_ID_GENERATOR   | | function       |  Function for generating unique id      |
|                        |                                     |                  |  of overriden codal configuration which |
|                        |                                     |                  |  will be displayed in test case ID      |
|                        |                                     |                  |  generated by pytest. Function takes    |
|                        |                                     |                  |  two arguments - key and value, where   |
|                        |                                     |                  |  key and value is taken from the codal  |
|                        |                                     |                  |  configuration dictionary. Function     |
|                        |                                     |                  |  returns string representation of given |
|                        |                                     |                  |  key and value. If empty ``str`` or     |
|                        |                                     |                  |  ``None`` is returned, then current     |
|                        |                                     |                  |  key-value pair is ommited from test    |
|                        |                                     |                  |  case ID.                               |
|                        |                                     |                  |                                         |
+------------------------+-------------------------------------+------------------+-----------------------------------------+

Examples:
    .. code-block:: python
        
        # Override default codal configuration of model.
        # There are 2*3=6 possible combinations of codal configuration,
        # therefore test case will be executed 6 times for each configuration
        # and each test case will use sdk with different features (with/without
        # newlib and different optimizations).
        @pytest.mark.tools(configurations={'sdk.newlib': [True, False],
                                           'sdk.startup': False,
                                           'optimization': [0, 1, 2]})
        def test_tools(sdk, codal_configuration):
            ...

    .. code-block:: python
        
        # Define filter function (lambda expression are supported as well).
        # Skip configuration with newlib and optimization 1 or 2, other configurations
        # will be used to generate sdk
        def configuration_filter(configuration):
            if configuration.get('sdk.newlib') and configuration.get('optimization') in [1, 2]:
                return False
            return True
        
        # Test case will be executed 4 times as 2 configurations are filtered by filter option.
        @pytest.mark.tools(configurations={'sdk.newlib': [True, False],
                                           'sdk.startup': False,
                                           'optimization': [0, 1, 2]},
                           filter=configuration_filter)
        def test_tools(sdk, codal_configuration):
            ...

    .. code-block:: python
        
        # ID generators are useful when automatically generated ids are too long.
        # That might cause worse readable reports or even errors on Windows systems
        # which have path length limit.
        
        # Define id generator function (lambda expression are supported as well).
        # Shortens sdk.newlib key - returns 'newlib' when newlib is available,
        #                           otherwise skips the key
        # From optimization returns only value
        # Ignores sdk.startup key as is will remain unchanged in all configurations,
        # so there is no reason to keep it in configuration ID.
        def id_generator(key, value):
            if key == 'sdk.newlib' and value:
                return 'newlib'
            if key == 'optimization':
                return str(value)
        
        # The following ids will be generated:
        #      Without id_generator            With id_generator
        #
        #    sdk.newlib,optimization:0            newlib,0
        #    optimization:0                          0
        #    sdk.newlib,optimization:1            newlib,1
        #    optimization:1                          1
        #    sdk.newlib,optimization:2            newlib 2
        #    optimization:2                          2
        @pytest.mark.tools(configurations={'sdk.newlib': [True, False],
                                           'sdk.startup': False,
                                           'optimization': [0, 1, 2]},
                           id_generator=id_generator)
        def test_tools(sdk, codal_configuration):
            ...

``@pytest.mark.generate``

Allows to generate combinations from dictionary. Behaviors is almost identical to @pytest.mark.tools marker with the only 
difference that generated combinations are not used to override codal configurations and therefore this option may be used 
without :class:`CodalProject` instance.

+------------------------+-------------------------------------+------------------+-----------------------------------------+
|      Option name       |       Static variable name          |    Data types    |               Description               |
|                        |                                     |                  |                                         |
+========================+=====================================+==================+=========================================+
|                        |                                     |                  |                                         |
| combinations           | GENERATE_COMBINATIONS               | | dict           |  Generated combinations from dictionary.|
|                        |                                     |                  |  Dictionary keys are any type which     |
|                        |                                     |                  |  supports hashing (e.g. str) and values |
|                        |                                     |                  |  may be any data type.                  |
|                        |                                     |                  |  Value may be a single value or list of |
|                        |                                     |                  |  values.  If list of values is set,     |
|                        |                                     |                  |  then test case is executed for each    |
|                        |                                     |                  |  combination.                           |
|                        |                                     |                  |                                         |
+------------------------+-------------------------------------+------------------+-----------------------------------------+
|                        |                                     |                  |                                         |
| filter                 | GENERATE_COMBINATIONS_FILTER        | | function       |  Function for certain combination       | 
|                        |                                     |                  |  filtering. Function takes one parameter|
|                        |                                     |                  |  which is the current combination       |
|                        |                                     |                  |  (from combinations option).            |
|                        |                                     |                  |  ``True`` is returned if current        |
|                        |                                     |                  |  combination is valid. If ``False``     |
|                        |                                     |                  |  is returned, then current combination  |
|                        |                                     |                  |  is skipped.                            |
|                        |                                     |                  |                                         |
+------------------------+-------------------------------------+------------------+-----------------------------------------+
|                        |                                     |                  |                                         |
| id_generator           | GENERATE_COMBINATIONS_ID_GENERATOR  | | function       |  Function for generating unique id      |
|                        |                                     |                  |  of combination which                   |
|                        |                                     |                  |  will be displayed in test case ID      |
|                        |                                     |                  |  generated by pytest. Function takes    |
|                        |                                     |                  |  two arguments - key and value, where   |
|                        |                                     |                  |  key and value is taken from the        |
|                        |                                     |                  |  combination dictionary. Function       |
|                        |                                     |                  |  returns string representation of given |
|                        |                                     |                  |  key and value. If empty ``str`` or     |
|                        |                                     |                  |  ``None`` is returned, then current     |
|                        |                                     |                  |  key-value pair is ommited from test    |
|                        |                                     |                  |  case ID.                               |
|                        |                                     |                  |                                         |
+------------------------+-------------------------------------+------------------+-----------------------------------------+

Examples:
    .. code-block:: python
        
        # There are 2*2=4 possible combinations
        # therefore test case will be executed 4 times for each combination
        @pytest.mark.generate(combinations={'fruit': ['apple', 'banana'],
                                            'vegetable': ['carrot', 'sweetcorn'],
                                            })
        def test_generate(combination):
            ...

    .. code-block:: python
        
        # Define filter function (lambda expression are supported as well).
        # Skip combination of apple and carrot.
        def combination_filter(combination):
            if combination.get('fruit') == 'apple' and combination.get('vegetable') == 'carrot':
                return False
            return True
        
        # Test case will be executed 3 times as 1 combination is filtered by filter option.
        @pytest.mark.generate(combinations={'fruit': ['apple', 'banana'],
                                            'vegetable': ['carrot', 'sweetcorn'],
                                            },
                              filter=configuration_filter)
        def test_generate(combination):
            ...

    .. code-block:: python
        
        # ID generators are useful when automatically generated ids are too long.
        # That might cause worse readable reports or even errors on Windows systems
        # which have path length limit.
        
        # Define id generator function (lambda expression are supported as well).
        # Returns only first letter of the value.
        def id_generator(key, value):
            return value[0].upper()
        
        # The following ids will be generated:
        #        Without id_generator            With id_generator
        #
        #    fruit:apple,vegetable:carrot              A,C
        #    fruit:apple,vegetable:sweetcorn           A,S
        #    fruit:banana,vegetable:carrot             B,C
        #    fruit:banana,vegetable:sweetcorn          B,S
        @pytest.mark.generate(combinations={'fruit': ['apple', 'banana'],
                                            'vegetable': ['carrot', 'sweetcorn'],
                                            },
                              id_generator=id_generator)
        def test_generate(combination):
            ...


``@pytest.mark.compiler``

Allows to specify required features of compiler. If compiler does not meet any requirement, test case is skipped.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| optimization      | COMPILER_OPTIMIZATION      | | str                    |  Optimizations, which will be used      |
|                   |                            | | int                    |  for compiler execution. If not         |
|                   |                            | | Iterable               |  specified, then all available          |
|                   |                            |                          |  optimizations will be used             |
|                   |                            |                          |  (0, 1, 2, 3, s, z).                    |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| startup           | COMPILER_STARTUP           | | bool                   |  Require startup library for compiler.  |
|                   |                            |                          |  If library is not available,           |
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| compiler_rt       | COMPILER_COMPILER_RT       | | bool                   |  Require compiler-rt library for        |
|                   |                            |                          |  compiler. If library is not available, |
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| newlib            | COMPILER_NEWLIB            | | bool                   |  Require newlib library for             |
|                   |                            |                          |  compiler. If library is not available, |
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| stdcxx            | COMPILER_STDCXX            | | bool                   |  Require standard C++ library for       |
|                   |                            |                          |  compiler. If library is not available, |
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| cxxabi            | COMPILER_CXXABI            | | bool                   |  Require C++ ABI library for            |
|                   |                            |                          |  compiler. If library is not available, |
|                   |                            |                          |  then test case is skipped.             |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+


Examples:
    .. code-block:: python
        
        # Execute for only for optimization 1
        @pytest.mark.compiler(optimization=1)
        def test_compiler(compiler):
            ...

    .. code-block:: python
        
        # Execute for optimizations 0, 1 and z
        @pytest.mark.compiler(optimization=[0, 1, 'z'])
        def test_compiler(compiler):
            ...

    .. code-block:: python
        
        # Require compiler-rt and non-present startup libraries/
        # Note that if requirements are met, test case will be executed for
        # all available optimizations.
        @pytest.mark.compiler(compiler_rt=True, startup=False)
        def test_compiler(compiler):
            ...

``@pytest.mark.simulator``

Allows to specify required features of simulator. If simulator does not meet any requirement, test case is skipped.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| ia                | SIMULATOR_IA               | | bool                   |  Require IA or CA simulator. If         |
|                   |                            |                          |  ``True``, then test case is executed   |
|                   |                            |                          |  for IA simulators only.                |
|                   |                            |                          |  If ``False``, then test case is        |
|                   |                            |                          |  executed for CA simulators only.       |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| debugger          | SIMULATOR_DEBUGGER         | | bool                   |  Require debugger support.              |
|                   |                            |                          |  If ``True``, then test case is executed|
|                   |                            |                          |  for simulators with debugger support   |
|                   |                            |                          |  only. If ``False``, then test case     |
|                   |                            |                          |  is executed only for simulators        |
|                   |                            |                          |  without debugger support.              |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| dump              | SIMULATOR_DUMP             | | bool                   |  Require dump support.                  |
|                   |                            |                          |  If ``True``, then test case is executed|
|                   |                            |                          |  for simulators with dump support       |
|                   |                            |                          |  only. If ``False``, then test case     |
|                   |                            |                          |  is executed only for simulators        |
|                   |                            |                          |  without dump support.                  |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| profiler          | SIMULATOR_PROFILER         | | bool                   |  Require profiler support.              |
|                   |                            |                          |  If ``True``, then test case is executed|
|                   |                            |                          |  for simulators with profiler support   |
|                   |                            |                          |  only. If ``False``, then test case     |
|                   |                            |                          |  is executed only for simulators        |
|                   |                            |                          |  without profiler support.              |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+


Examples:
    .. code-block:: python
        
        # Execute only for CA simulators
        @pytest.mark.simulator(ia=False)
        def test_simulator(simulator):
            ...

    .. code-block:: python
        
        # Execute only for simulators with dump support
        @pytest.mark.simulator(dump=True)
        def test_simulator(simulator):
            ...
            

``@pytest.mark.debugger``

Allows to specify required features of debugger. If debugger does not meet any requirement, test case is skipped.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| ia                | DEBUGGER_IA                | | bool                   |  Require IA or CA debugger. If          |
|                   |                            |                          |  ``True``, then test case is executed   |
|                   |                            |                          |  for IA debuggers only.                 |
|                   |                            |                          |  If ``False``, then test case is        |
|                   |                            |                          |  executed for CA debuggers only.        |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| codal_debugger    | DEBUGGER_CODAL             | | bool                   |  Require CODAL debug support.           |
|                   |                            |                          |  If ``True``, then test case is executed|
|                   |                            |                          |  for deniggers with CODAL debug support |
|                   |                            |                          |  only. If ``False``, then test case     |
|                   |                            |                          |  is executed only for debuggers         |
|                   |                            |                          |  without CODAL debug support.           |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+


Examples:
    .. code-block:: python
        
        # Execute only for IA debuggers
        @pytest.mark.debugger(ia=True)
        def test_debugger(debugger):
            ...

    .. code-block:: python
        
        # Execute only for debugger which do NOT support CODAL debugging
        @pytest.mark.debugger(codal_debugger=False)
        def test_debugger(debugger):
            ...

``@pytest.mark.profiler``

Allows to specify required features of profiler. If profiler does not meet any requirement, test case is skipped.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| ia                | PROFILER_IA                | | bool                   |  Require IA or CA profiler. If          |
|                   |                            |                          |  ``True``, then test case is executed   |
|                   |                            |                          |  for IA profilers only.                 |
|                   |                            |                          |  If ``False``, then test case is        |
|                   |                            |                          |  executed for CA profilers only.        |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+


Examples:
    .. code-block:: python
        
        # Execute only for IA profilers
        @pytest.mark.profiler(ia=True)
        def test_profiler(profiler):
            ...

``@pytest.mark.uvm``

Allows to specify required features of UVM. If UVM does not meet any requirements, test case is skipped.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| hdl_languages     | UVM_HDL_LANGUAGES          | | str                    |  HDL languages which will be            |
|                   |                            | | Iterable               |  used for test case execution.          |
|                   |                            |                          |  If not specified, then all             |
|                   |                            |                          |  available HDL languages will be used.  |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| rtl_simulators    | UVM_RTL_SIMULATORS         | | str                    |  RTL simulators which will be           |
|                   |                            | | Iterable               |  used for test case execution.          |
|                   |                            |                          |  If not specified, then all             |
|                   |                            |                          |  available RTL simulators will be used. |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| synthesis_tools   | UVM_SYNTHESIS_TOOLS        | | str                    |  Synthesis tools which will be          |
|                   |                            | | Iterable               |  used for test case execution.          |
|                   |                            |                          |  If not specified, then all             |
|                   |                            |                          |  available synthesis tools will be      |
|                   |                            |                          |  used.                                  |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+

Examples:
    .. code-block:: python
        
        # Execute test case for VHDL and verilog languages
        @pytest.mark.uvm(hdl_languages=['vhdl', 'verilog'])
        def test_uvm(uvm):
            ...

    .. code-block:: python
        
        # Execute test case only for Questasim
        @pytest.mark.uvm(rtl_simulators='questa')
        def test_uvm(uvm):
            ...

    .. code-block:: python
        
        # Execute test case only for Xilinx ISE
        @pytest.mark.uvm(synthesis_tools='xilinx_ise')
        def test_uvm(uvm):
            ...

``@pytest.mark.find_files``

Traverses file system and parametrizes test cases with files matching requested pattern.

.. note::

    ``.py``, ``.pyc`` files and ``__pycache__`` directory are always ommited from the search.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| name              | FIND_FILES_NAME            | | str                    |  Fixture name to parametrize.           |
|                   |                            |                          |  If not set, then fixturename ``file``  |
|                   |                            |                          |  is used.                               |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| path              | FIND_FILES_PATH            | | str                    |  Path to root directory, where files    |
|                   |                            |                          |  will be searched. Path may be absolute |
|                   |                            |                          |  or relative. When using relative path, |
|                   |                            |                          |  then it is relative to the directory,  |
|                   |                            |                          |  where the test case source is located. |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| pattern           | FIND_FILES_PATTERN         | | str                    |  Regular expression which must be       |
|                   |                            | | Iterable               |  matched with the file name to accept   |
|                   |                            |                          |  that filename. If multiple patterns    |
|                   |                            |                          |  are passed, then ALL must be matched.  |
|                   |                            |                          |  Patterns are matched against the       |
|                   |                            |                          |  absolute path of the files.            |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| exclude           | FIND_FILES_EXCLUDE         | | str                    |  Regular expression which must NOT be   |
|                   |                            | | Iterable               |  matched with the file name to accept   |
|                   |                            |                          |  that filename. If multiple patterns    |
|                   |                            |                          |  are passed, then NONE must be matched. |
|                   |                            |                          |  Patterns are matched against the       |
|                   |                            |                          |  absolute path of the files.            |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+

Examples:
    For the following examples, assume the following directory structure:
    
    * tests
        * applicationsA
            * source_a.c
            * source_b.c
            * source_c.c
            * source_d.c
        * applicationsB
            * source_1.c
            * source_2.c
            * source_3.c
            * source_4.c
        * test_find_files.py

    .. code-block:: python
        
        # Try to find files in tests directory as it is default path
        # and override the default *file* fixture name by *application*
        # Test case will be executed 8 times, as 8 files will be found.
        @pytest.mark.find_files(name='application')
        def test_find_files(application):
            ...

    .. code-block:: python
        
        # Try to find files in tests/applicationsA directory.
        # No patterns are used, so 4 files (source_a.c, ..., source_d.c)
        # will be used.
        @pytest.mark.find_files(path='applicationsA')
        def test_find_files(file):
            ...

    .. code-block:: python
        
        # Try to find files in tests/applicationsA directory and apply
        # regular expression. Pattern will match files ending
        # with a.c or b.c. It will be matched for files source_a.c
        # and source_b.c.
        @pytest.mark.find_files(path='applicationsA', pattern='(a|b)\.c$')
        def test_find_files(file):
            ...

    .. code-block:: python
        
        # Try to find files in tests directory which do not match
        # the required pattern. Therefore sources in
        # applicationsA will be skipped and all remaining sources
        # (from directory applicationsB) will be used.
        @pytest.mark.find_files(exclude='applicationsA')
        def test_find_files(file):
            ...


``@pytest.mark.directory_collect``

Traverses file system and parametrizes test cases with list of files matching requested pattern. 
Behaviour is similar to ``@pytest.mark.find_files`` with the only difference that list of files 
(from the same directory) is passed to test case instead of single file.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| name              | DIRECTORY_COLLECT_NAME     | | str                    |  Fixture name to parametrize.           |
|                   |                            |                          |  If not set, then fixturename ``files`` |
|                   |                            |                          |  is used.                               |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| path              | DIRECTORY_COLLECT_PATH     | | str                    |  Path to root directory, where files    |
|                   |                            |                          |  will be searched. Path may be absolute |
|                   |                            |                          |  or relative. When using relative path, |
|                   |                            |                          |  then it is relative to the directory,  |
|                   |                            |                          |  where the test case source is located. |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| pattern           | DIRECTORY_COLLECT_PATTERN  | | str                    |  Regular expression which must be       |
|                   |                            | | Iterable               |  matched with the file name to accept   |
|                   |                            |                          |  that filename. If multiple patterns    |
|                   |                            |                          |  are passed, then ALL must be matched.  |
|                   |                            |                          |  Patterns are matched against the       |
|                   |                            |                          |  absolute path of the files.            |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| exclude           | DIRECTORY_COLLECT_EXCLUDE  | | str                    |  Regular expression which must NOT be   |
|                   |                            | | Iterable               |  matched with the file name to accept   |
|                   |                            |                          |  that filename. If multiple patterns    |
|                   |                            |                          |  are passed, then NONE must be matched. |
|                   |                            |                          |  Patterns are matched against the       |
|                   |                            |                          |  absolute path of the files.            |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+

``@pytest.mark.test_metadata``

Passes additional metadata to test case. Test metadata are passed from commandline with ``--test-metadata`` argument.
Marker arguments are considered as required, so when any marker argument is missing in metadata, test case is skipped.
One can set default value for key using keyword arguments. These keys are considered as optional as they always contain
some value, either one passed from commandline or one specified in this marker.

Examples:
    .. code-block:: python
        
        # test_metadata dictionary will contain all keys and values which were passed from commandline.
        def test_metadata(test_metadata):
            ...
            
    .. code-block:: python
        
        # Test case requires two keys in test metadata (required1, required2)
        # If any of these keys has value, then test case is skipped.
        # Key 'optional' has default value specified, so it is not required
        # from commandline.
        @pytest.mark.test_metadata('required1', 'required2', optional=None)
        def test_metadata(test_metadata):
            ...

``@pytest.mark.test_type``

Allows to specify test types for which the test case is enabled and/or disabled.

+-------------------+----------------------------+--------------------------+-----------------------------------------+
|    Option name    |    Static variable name    |        Data types        |               Description               |
|                   |                            |                          |                                         |
+===================+============================+==========================+=========================================+
|                   |                            |                          |                                         |
| enable            | TEST_TYPE_ENABLE           | | str                    |  Test types for which test case is      |
|                   |                            | | Iterable               |  available. If current testing type     |
|                   |                            |                          |  does not match any of the specified    |
|                   |                            |                          |  values, test case is skipped.          |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+
|                   |                            |                          |                                         |
| disable           | TEST_TYPE_DISABLE          | | str                    |  Test types for which test case is NOT  |
|                   |                            | | Iterable               |  available. If current testing type     |
|                   |                            |                          |  matches any of the specified values,   |
|                   |                            |                          |  test case is skipped.                  |
|                   |                            |                          |                                         |
+-------------------+----------------------------+--------------------------+-----------------------------------------+

Examples:
    .. code-block:: python

        # Execute test only for testing type 'ip_nightly'.
        # For any other testing type, test case will be skipped.
        @pytest.mark.test_type(enable='ip_nightly')
        def test_type():
            ...
            
        # For testing type 'default' or 'ip_nightly' or 'studio_nightly', test case
        # will be skipped.
        @pytest.mark.test_type(disable=['default', 'ip_nightly', 'studio_nightly'])
        def test_type():
            ...            
"""










