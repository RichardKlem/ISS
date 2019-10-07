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
# Desc: Wrappers for tools and generators
import os
import pytest
import re

import codasip
from codasip.utility.utils import command_builder
from codasip.testsuite.sdk import Sdk
from mastermind.lib import (TOOL2TASK, IA_TASKS, CA_TASKS, IA_TOOLS, CA_TOOLS, TASK_RANDOM_ASM,
                            ASIP_TASKS, LEVEL_TASKS, EXE_EXTENSION)
from mastermind.lib.codasip_utils import load_project, filter, Hdk
from mastermind.lib.exceptions import ToolBuildError
from mastermind.lib.helpers import configure
from mastermind.lib.utils import OutputDuplicator, info, is_iterable, warning

class RandomGen(object):   
    """Simple wrapper for random assembler generator."""
    
    KEY_PREFIX = 'random-assembler-programs'
    
    def __init__(self, model):
        """Constructor.
        
        :param model: Instance which will be used to generate
            random applications.
        :type model: :py:class:`~codasip_utils.CodalModel`
        :ivar model: :py:class`~codasip_utils.CodasipModel` instance.
        :ivar dir: Path to random applications directory.
        :vartype dir: str
        :raises `~exceptions.ValueError`: When ``model`` does not support random application
            generation.
            
        .. warning::
            
           Valid model must be IA and ASIP. 
        """
        if not model.ia or not model.asip:
            raise RuntimeError("Invalid model for RandomGen. Valid model must be IA asip, got {} {}".format(
                ))

        #self.project = load_project(model.project.dir, work_dir=str(model.project.work_dir))
        self.model = model
        self.dir = model.work_dir.get_randomgen_dir(model.id)
        self._config = {}
        
    def run(self, **kwargs):
        """
        Execute randomgen.
        
        :param kwargs: Keyword arguments for randomgen. Each key is a configuration key
            for `codal.conf` without :py:data:`KEY_PREFIX`.
            
        :Examples:
    
        >>> RandomGen(model).run(instructions=100, programs=20)
            
        .. note::
        
            Uses **random_asm** task from Codasip Commandline to build applications.
        
        """
        for key, value in kwargs.iteritems():
            key = self.KEY_PREFIX + '.' + key.replace('_', '-')
            self._store_and_set_config(key, value)
        
        self.model.project.build(self.model.get_task_id(TASK_RANDOM_ASM))
        self._restore_config()
    
    def _store_and_set_config(self, key, value):
        """Stores config key and value to internal cache,
        so it can be restored after generation. Also overrides
        model configuration.
        
        :param key: ``codal.conf`` key.
        :param value: Value for ``key``.
        :type key: str
        """
        self._config[key] = self.model.config[key]
        self.model.config[key] = value
    
    def _restore_config(self):
        """Restores model configuration to its original state,"""
        for key, value in self._config.iteritems():
            self.model.config[key] = value
        self._config = {}

class ToolBuilder(object):
    """
    Simple wrapper for building sdk and hdk tools
    """
    
    def __init__(self, project, reload=True, config=None, **kwargs):
        """Constructor
        
        :param project: Instance of CodalProject or path to project root
        :param reload: If ``True``, then ToolBuilder creates a new instance of project
                       for its own usage. 
        :param config: Pytest Config object 
        :param kwargs: Keyword arguments for project loading. If no reload is
                       performed, arguments are ignored.
        :type project: :py:class:`~codasip_utils.CodalProject` or str
        :type reload: bool
        :type config: ``Config``
        """
        import codasip.build.project
        if not isinstance(project, codasip.build.project.CodalProject):
            self.project = load_project(project, config, **kwargs)
        elif reload:
            self.project = load_project(project.dir, config, **kwargs)
        else:
            self.project = project
            
        self._config = config
        self._built = set()
        
    def configure(self, configuration):
        """
        Overrides current project configuration. Automatically handles per-model
        configuration keys.
        
        :param configuration: Dictionary with configuration. Keys are codal.conf keys.
        :type configuration: dict
        
        .. seealso::
            
            Uses :py:func:`~mastermind.lib.helpers.configure` function to configure project.
        """
        configure(self.project, configuration)
    
    @property
    def models(self):
        return self.project.models

    def build(self, tools, args=None, auto_detect_models=False, **kwargs):
        """Build requested tools.
        
        :param tools: List of tools to build. Might be either tool name or a task
                      for build system (e.g. assembler and asm are equivalent).
        :param args: Additional arguments for Codasip Build system.
        :param auto_detect_models: If True, then model auto-detection is performed,
            e.g. when building compiler for ca model, then ia model is used 
            for compiler build.        
        :param kwargs: Keyword arguments for model filtering.
        :type tools: list or str
        :type args: list or tuple
        :type auto_detect_models: bool
        :return: Dictionary containing Sdk and Hdk wrappers of built tools. If tools are
                 built for multiple models, partial SDKs and/or HDKs will be merged.
        :rtype: dict
        :raises `~exceptions.ToolBuildError`: When build fails.
        
        .. seealso::
            
            See :py:mod:`~mastermind.lib` module for list of available tasks.

        .. seealso::
            
            See :py:func:`~mastermind.lib.helpers.filter` for available filters.
        
        """        
        if not is_iterable(tools):
            tools = [tools]
        # Apply user defined filters
        models = list(filter(self.models.values(), **kwargs))
        
        if not models:
            models = ', '.join([model.id for model in self.models.values()])
            keywords = ', '.join([key+'='+str(value) for key, value in kwargs.items()])
            warning("No models are available for build.\nModels {} have been filtered by {}".format(models, keywords))
            return
        if self._config:
            # Running from pytest - there might be some filters from commandline
            models = [model for model in models if model.id in self._config.design_paths]
            if not models:
                pytest.skip("No models available for build. Maybe they were filtered by cmdline option or marker")
                return
        
        # Save models for latter sdk/hdk wrapper creation
        self._built.clear()
        #self._current_models.update(models)
        
        for model in models[:]:
            # Build tools for single model (method may add 
            # May add models to _current_models if auto detection is enabled
            self._build(model, tools, args, auto_detect_models)
        
        return self._get_tools(map(lambda x: x.split(':')[1], self._built))
        
    def _build(self, model, tools, args, auto_detect_models):
        """Perform real tool generation for a single model.
        
        :param model: CodalModel instance.
        :param tools: List of tools to build. Might be either tool name or a task
                      for build system (e.g. assembler and asm are equivalent).
        :param args: Additional arguments for Codasip Build system.
        :param auto_detect_models: If ``True``, then model auto-detection is performed,
            e.g. when building compiler for ca model, then ia model is used 
            for build itself.
        :type tools: list or str
        :type args: list or tuple
        :type auto_detect_models: bool
        :raises `~exceptions.ToolBuildError`: When build fails.        
        """
        info("Building {} for {}".format(', '.join(tools), model.id))
        info("Model autodetection is {}".format('enabled' if auto_detect_models else 'disabled'))
        if not is_iterable(tools):
            tools = [tools]
        
        # Build task command
        cmd = command_builder()
        
        # Build system arguments
        if args:
            cmd += args
            
        for tool in tools:
            # Get task tool alias has been passed
            task_name = TOOL2TASK.get(tool, tool)
            if auto_detect_models:
                detected = self._detect_model(model, task_name)
                
                if detected is None:
                    warning("Alternate model for {} could not be detected, ignoring generation of '{}'", model.id, tool)
                    continue
                task_id = detected.get_task_id(task_name)
                #self._built.add((task_name, detected))
                #cmd += detected.get_task_id(task_name)
            else:
                task_id = model.get_task_id(task_name)
            
            if task_id in self._built:
                #info("Found alternate model {} for tool {} which has already been built, skipping", model.id, tool)
                info("Task {} has already been built, skipping.", task_id)
                continue
            self._built.add(task_id)
            cmd += task_id
            #cmd += model.get_task_id(task_name)
        
        if not cmd.args:
            info("Nothing to build, skipping")
            return

        # Capture stdout and stderr
        import codasip.utility.exceptions
        with OutputDuplicator() as duplicator:
            try:
                self.project.build(cmd.args)
            except codasip.utility.exceptions.BuildError as exc:
                out = duplicator.out.getvalue()
                err = duplicator.err.getvalue()
                raise ToolBuildError(str(exc),
                                     project=self.project,
                                     args=cmd,
                                     stdout=out,
                                     stderr=err)
    
    def _is_built(self, tool, model):
        return (tool, model) in self._built
        
    def _detect_model(self, model, task):
        # Detect if tool is for IA or CA models only
        ia = task in (IA_TOOLS + IA_TASKS)
        ca = task in (CA_TOOLS + CA_TASKS)
        # Tool exists for both descriptions
        if ia and ca:
            ia = None
        # Tool and model mismatch
        if ia is not None and model.ia != ia:
            detected = model.get_sibling_model(not model.ia)
            if detected:
                info("Task: {}, Original model: {}, alternative: {}", task, model.id, detected.id)
                model = detected
            else:
                return None
        
        asip = task in ASIP_TASKS
        level = task in LEVEL_TASKS
        if asip and level:
            asip = None
        
        # If model is ASIP, then get top level
        # If model is level, then get child ASIP (model.references)
        if asip is not None and model.asip != asip:
            detected = None
            if asip:
                for ref in model.references:
                    if ref.asip:
                        detected = ref
                        break
            else:
                detected = model.parent
            
            if detected and detected.asip == asip:
                info("Task: {}, Original model: {}, alternative: {}", task, model.id, detected.id)
                model = detected
            else:
                return None
    
        return model

    def _get_tools(self, models=None):
        """Create SDK and/or HDK wrapper for existing tools for given models.
        
        Automatically merges all available SDKs/HDKs to a single object. 
        
        :param models: List of CodalModel instances. If ``None`` all project models
            are used.
        :type models: list
        :return: Dictionary containing built SDK and/or HDK.
        :rtype: dict
        """
        if models is None:
            models = self.models.values()
        elif not is_iterable(models):
            models = [models]

        sdk_dirs = set()
        hdk_dir = None
        # Detect model directories
        for model in models:
            if isinstance(model, basestring):
                model_name = model.split('.')[1]
                m = self.models.get(model_name)
                if m is None:
                    warning("Model {} not found, could not create SDK/HDK wrapper.", model)
                    continue
                model = m
            if os.path.exists(model.sdk_dir) and Sdk.FILENAME in os.listdir(model.sdk_dir):
                sdk_dirs.add(model.sdk_dir)
            if not model.ia and os.path.exists(model.hdk_dir) and Hdk.FILENAME in os.listdir(model.hdk_dir):
                hdk_dir = model.hdk_dir
        # Instantiate wrappers
        objs = {}
        if sdk_dirs:
            objs['sdk'] = Sdk(list(sdk_dirs))
        if hdk_dir:
            objs['hdk'] = Hdk(hdk_dir, self._config.work_dir)
        
        return objs


class CodasipTools():
    """Wrapper for easier Codasip tools traversal.
    """
    
    def __init__(self):
        """Constructor
        
        :ivar build_type: Contains build info. 
        :ivar dir: Path to tools directory.
        :ivar version: Codasip tools version.
        :vartype build_type: :py:class:`codasip_utils.utils.BuildType`
        :vartype dir: str
        :vartype version: str
        """
        import codasip.utility.internal
        
        self.build_type = codasip.utility.internal.BuildType()
        self.dir = codasip.tools_dir
        self.version = codasip.version
    
    def get_path(self, name):
        """Build path to tool.
        
        Does not perform existence check.
        
        :param name: Tool name to find.
        :type name: str
        :return: Path to tool.
        :rtype: str
        """
        dir = 'cmake' if re.search('\.cmake$', name) else 'bin'
        if dir == 'bin' and not os.path.splitext(name)[1]:
            name += EXE_EXTENSION
        elif dir == 'cmake' and not os.path.splitext(name)[1]:
            name += '.cmake'

        return os.path.join(self.dir, dir, name)
    
    def find(self, name):
        """Find tool.
        
        :param name: Tool name to find.
        :return: Path to tool if tool exists else ``None``.
        :rtype: str or None
        """
        p = self.get_path(name)
        if os.path.exists(p):
            return p
        


