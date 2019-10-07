import os
import re
import sys

import codasip
import codasip.build.project
import codasip.utility.internal
from codasip.build.project import ProjectBase, CodalProject
from codasip.build.codal_model import CodalModel
from codasip.build.dk_models import BaseModel
from codasip.testsuite.hdk import Hdk as HdkBase

from mastermind.lib.helpers import parse_cmdline_data, configure
from mastermind.lib.utils import is_iterable, walklevel, info, error, warning, debug

# SDK Libraries info
CODASIP_LIBRARIES = codasip.internal_get_libraries_info()
build_type = codasip.utility.internal.BuildType()

class Hdk(HdkBase):
    """Hdk wrapper for HDK

    Add support for multiple uvms iteration.
    """
    def find_uvm(self, **kwargs):
        """Search for the UVM with specified properties."""
        return next(self.iter_uvms(**kwargs), None)

    def iter_uvms(self, rtl_sim=None):
        """
        Filter existing uvms with requested features from Hdk.

        :param rtl_sim: Only uvms with given ``rtl_sim`` are yielded.
        :return: Yields :py:class`codasip.testsuite.plugin_hdk.Uvm` instances.
        :rtype: generator
        """
        def iter_all():
            """Generator for iterating all available UVMs"""
            for model in self.models.itervalues():
                for rtl_sim in self.uvm_tests:
                    uvm = model.uvm(rtl_sim, self.work_dir)
                    yield uvm

        all_uvms = iter_all()

        for uvm in all_uvms:
            if rtl_sim is not None and uvm.rtl_sim != rtl_sim:
                continue

            yield uvm


def filter_codal_object(item, ia=None, asip=None, top=None, pattern=None, disable=None, cls=None):
    """Filter for Codal object.
    
    Apply various filters on passed ``item`` which must be an instance of class used by Codasip
    Build system - :py:class:`~codasip.CodalProject` or :py:class:`~codasip.CodalModel`.

    
    When a filter argument is ``None``, then that filter is not applied.
    
    :param item: Instance on which will be applied filters.
    :param ia: If ``True``, then only IA model is allowed, for ``False`` only CA object is allowed.
    :param ia: If ``True``, then only ASIP model is allowed, for ``False`` only non-ASIP (level, component) object is allowed.
    :param ia: If ``True``, then only TOP model is allowed, for ``False`` only non-TOP object is allowed.
    :param pattern: Regular expression which must be matched by item's name (design_path for 
        :py:class:`~codasip.CodalModel`).
    :param disable: Regular expression which must NOT be matched by item's name (design_path for 
        :py:class:`~codasip.CodalModel`).
    :param cls: Class which must be matched with item's class.
    :type ia: bool
    :type asip: bool
    :type top: bool
    :type pattern: string
    :type disable: string
    :return: ``item`` if ``item`` passed all filters, otherwise ``None``.
    """
    item_id = item.id if isinstance(item, CodalModel) else item.name
    
    if ia is not None and hasattr(item, 'ia') and item.ia != ia:
        return
    if asip is not None and hasattr(item, 'asip') and item.asip != asip:
        return
    if top is not None and hasattr(item, 'top') and top != (item.top is item):
        return
    if pattern is not None:
        if not re.search(pattern, item_id):
            return
    if disable is not None:
        if re.search(disable, item_id):
            return
    if cls is not None and item.__class__ != cls:
        return
    
    return item

def filter_dk_object(item, project_names, ia=None, asip=None, top=None, pattern=None, disable=None, cls=None):
    """Filter for Dk (development kit) object.
    
    Apply various filters on passed ``item`` which must be string or an instance of class used by Codasip
    Development kit wrappers - :py:class:`~codasip.DkModel`.
    
    When a filter argument is ``None``, then that filter is not applied.
    
    :param item: Instance on which will be applied filters.
    :param ia: If ``True``, then only IA model is allowed, for ``False`` only CA object is allowed.
    :param ia: If ``True``, then only ASIP model is allowed, for ``False`` only non-ASIP (level, component) object is allowed.
    :param ia: If ``True``, then only TOP model is allowed, for ``False`` only non-TOP object is allowed.
    :param pattern: Regular expression which must be matched by item's id (design_path for 
        :py:class:`~codasip.DkModel`).
    :param disable: Regular expression which must NOT be matched by item's name (design_path for 
        :py:class:`~codasip.DkModel`).
    :param cls: Class which must be matched with item's class.
    :type ia: bool
    :type asip: bool
    :type top: bool
    :type pattern: string
    :type disable: string
    :return: ``item`` if ``item`` passed all filters, otherwise ``None``.
    """    
    item_id = getattr(item, 'id', str(item))
    project_name = item_id.split('.')[-2]

    if ia is not None:
        regex = '\.ia' if ia else '\.ca'
        if not re.search(regex, item_id):
            return
    if asip is not None:
        regex = '_top\.(ia|ca)$'
        if bool(re.search(regex, item_id)) == asip:
            return 
    if top is not None and top != (project_name+'_top' not in project_names):
        return
    if pattern is not None:
        if not re.search(pattern, item_id):
            return
    if disable is not None:
        if re.search(disable, item_id):
            return
    if cls is not None and item.__class__ != cls:
        return
    
    return item

def filter(items, *args, **kwargs):
    """Filter items from list.
    
    .. note::
    
        Uses :py:func:`filter_codal_object` and :py:func:`filter_dk_object` for filtering.
        Used filter function is determined from the each item's class. 
    
    :return: Yields filtered items.
    :rtype: generator
    
    :Examples:
    
    Load project instance and show all available models referenced from project.
    
    >>> project = codasip.Project.load('codix_helium_top')
    >>> models = project.list_models()
    >>> for model in models:
    ...     print(model.id)
    codix_helium_top.ia
    codix_helium_top.ia.codix_helium.ia
    codix_helium_top.ca
    codix_helium_top.ca.codix_helium.ca
    
    Keep `ca` models only by setting ``ia=False``.
    
    >>> for model in filter(models, ia=False):
    ...     print(model.id)
    codix_helium_top.ca
    codix_helium_top.ca.codix_helium.ca
    
    Filter `asip` models.
    
    >>> for model in filter(models, asip=False):
    ...     print(model.id)
    codix_helium_top.ia
    codix_helium_top.ca

    """    
    if not is_iterable(items):
        items = [items]
    
    def _project_name(item):
        return getattr(item, 'id', str(item)).split('.')[-2]
    
    
    for item in items:
        if isinstance(item, (CodalProject, CodalModel)):
            item = filter_codal_object(item, *args, **kwargs)
        elif isinstance(item, (BaseModel, str)):
            # filter_dk_object needs to know all project names for filtering 'top' models
            project_names = set(map(_project_name, items))
            item = filter_dk_object(item, project_names, *args, **kwargs)
        
        if item:
            yield item
            
def find_projects(paths, name=None, depth=3, load=False, top=False):
    """
    Search the path and load all projects in that path.
    
    :param paths: Paths to search. 
    :param name: If ``None``, find all projects, otherwise return only projects
                 matching the name.
    :param depth: Maximum depth of recursive search.
    :param load: If ``True``, then instances of :py:class:`~codasip.CodalProject` will
                 be returned, otherwise return root directories for projects.
    :param top: If ``True`` return only top-level projects.
    :type paths: list
    :type name: str
    :type depth: int
    :type load: bool
    :type top: bool
    :return: If load is ``True``, then list of found ``CodalProjects``, else \
        directories containing these projects.
    """
    if not is_iterable(paths):
        paths = [paths]
    
    projects = set()
    for project_path in paths:
        # Keep the path absolute
        project_path = os.path.abspath(project_path)
        if not os.path.isdir(project_path):
            continue
        # Search deeper for projects
        for root, _, files in walklevel(project_path, depth=depth):
            for fname in files:
                # Project config found, add its directory to paths
                if fname == CodalProject.CONFIG_FILENAME:
                    project_name = os.path.basename(root)
                    # filter by name
                    if name is None or project_name == name:
                        projects.add(root)
                    break
    
    # Get top projects only
    if top:
        projects = set([p for p in projects if p+'_top' not in projects])
            
    if load:
        projects = map(ProjectBase.load, projects)
    
    return list(projects)


def load_project(dir, config=None, **kwargs):
    """
    Load project with automatic settings.
    
    :param dir: Directory containing project.
    :param config: Pytest Config object.
    :param kwargs: Additional arguments for project initialization.
    :type dir: str
    :type config: :py:class:`~pytest.config.Config`
    :return: Loaded :py:class:`~codasip.CodalProject`.
    :rtype: :py:class:`~codasip.CodalProject`
    """

    if config:
        kwargs.setdefault('configuration', config.getoption('configuration'))
        kwargs.setdefault('configuration_file', config.getoption('configuration_file'))
        kwargs.setdefault('options', parse_cmdline_data(config.getoption('ip_options')))

    p = ProjectBase.load(dir, **kwargs)
    
    if config:
        codal_configuration = parse_cmdline_data(config.getoption('codal_configuration'))
        if codal_configuration:
            configure(p, codal_configuration)
    
    return p
