import inspect
import os
import re
import sys

from mastermind.lib import (MODEL, SEMANTICS, ASSEMBLER, DISASSEMBLER, COMPILER, 
                            LIBS, SIMULATOR, COSIMULATOR, DEBUGGER, PROFILER, 
                            RANDOM_ASM, RTL, UVM, _UVM_FU, TOOL2TASK)
from mastermind.lib.utils import AttrDict, to_list
from mastermind.database.model import Status as StatusDBModel

# Enumeration for execution phases of pytest 
STATUS_PHASE_NONE = None
STATUS_PHASE_SETUP = 'setup'
STATUS_PHASE_CALL = 'call'
STATUS_PHASE_TEARDOWN = 'teardown'
STATUS_PHASES = [STATUS_PHASE_NONE, STATUS_PHASE_SETUP, STATUS_PHASE_CALL, STATUS_PHASE_TEARDOWN]
STATUSES = []

# Enumeration for common error types (1 is reserved for TEST_FAILED)
STATUS_FAILED = 1
STATUS_GENERALERROR = 2
STATUS_BUILDERROR = 3
STATUS_TIMEOUT = 4
COMMON_ERRORS = {STATUS_GENERALERROR: ('GENERALERROR', '{} general error', None),
                 STATUS_BUILDERROR: ('BUILDERROR', '{} build error', None),
                 STATUS_TIMEOUT: ('TIMEOUT', '{} timeout exceeded', None),
                  }

class PatternStatus():
    def __init__(self, exit_codes=None, stdout=None, stderr=None, exc_types=None):
        self._exit_codes = to_list(exit_codes)
        self._stdout_patterns = to_list(stdout)
        self._stderr_patterns = to_list(stderr)
        self._exc_types = exc_types
    
    def search(self, exc, *args, **kwargs):
        if self._exc_types is not None and not isinstance(exc, self._exc_types):
            return False
        if hasattr(exc, 'exit_code'):
            if self._exit_codes is not None and exc.exit_code in self._exit_codes:
                return True
        if hasattr(exc, 'stderr') and self._stderr_patterns is not None:
            string = exc.stderr
            for pattern in self._stderr_patterns:
                if re.search(pattern, string, *args, **kwargs):
                    return True
        if hasattr(exc, 'stdout') and self._stdout_patterns is not None:
            string = exc.stdout
            for pattern in self._stdout_patterns:
                if re.search(pattern, string, *args, **kwargs):
                    return True

        return False
    
    def _auto_detect_exit_code(self, string):
        match = re.search('failed with exit code (-?\d+)', string)
        if match:
            return match.group(1)

class Status(object):
    
    SUPPORT_COMMON_ERRORS = True
    
    PHASE_WEIGHT = 10000
    ITEM_WEIGHT = 100
    
    ITEM_ID = None
    ITEM_NAME = None
    TASK_PATTERN = None
        
    PREFIX = 'MASTERMIND'
    PREFIX_STATUS_ATTRIBUTE = 'STATUS_'

    def __init__(self, sid, code, description='', phase=None, patterns=None, prefix=None):
        """Constructor.

        :param phase: Execution phase of Pytest.
        :param id: Unique status ID.
        :param code: 
        :param description:
        :type id: str
        :type code: int
        :type description: str
        """
        assert self.ITEM_ID is not None, "Missing ITEM_ID attribute for {}".format(self.__class__.__name__)
        assert sid >= 0, "Status ID must be greater than 0"

        self._id = sid
        self._code = code
        self.description = description
        self.phase = phase
        self.prefix = prefix
        if prefix is None:
            self.prefix = prefix or self.PREFIX

        self.patterns = to_list(patterns)

    @property
    def status_id(self):
        sid = self.PHASE_WEIGHT * STATUS_PHASES.index(self.phase)
        sid += self.ITEM_WEIGHT * self.ITEM_ID
        sid += self._id
        return sid

    @property
    def code(self):
        parts = []
        if self.prefix:
            parts += [self.prefix]
        if self.phase:
            parts += [self.phase]
        parts += [self._code]

        return '_'.join(parts).upper()
    
    @classmethod
    def search_task(cls, string):
        if cls.TASK_PATTERN is not None:
            return re.search(cls.TASK_PATTERN, string) is not None
        return False
    
    @classmethod
    def status(cls, id, phase=None):
        for name, value in cls.get_status_attributes().items():
            sid, description, patterns = value
            if sid == id:
                # Execution statuses do not use phase, so when phase has
                # been passed, we have to skip these. Otherwise (when phase
                # has been passed), we search for test-result statuses 
                is_execution_result = 'OK' in name or 'EXIT' in name
                if bool(phase) == is_execution_result:
                    continue
                return cls(sid, cls._status_name(name), description,
                            phase, patterns=patterns)

    @classmethod
    def get_status_attributes(cls, include_common=None):
        """Extract status attributes from the class.

        :param item: Class object which represents status item.
        :return: Dictionary with attribute names as keys and
                a triplet representing status
                (status_code, description, <PatternStatus> instance).
        :rtype: dict
        """
        if include_common is None:
            include_common = cls.SUPPORT_COMMON_ERRORS

        prefix = cls.PREFIX_STATUS_ATTRIBUTE
        attrs = {}
        for attribute in cls.__dict__:
            # Get status attributes only
            if attribute.startswith(prefix):
                attrs[attribute] = getattr(cls, attribute)

        if include_common:
            for sid, value in COMMON_ERRORS.items():
                name, description, patterns = value
                description = description.format(cls.ITEM_NAME.capitalize())
                attrs[prefix+name] = (sid, description, patterns)

        return attrs

    @classmethod
    def _status_name(cls, attribute):
        """Cut status prefix from attribute name
        """
        if attribute.startswith(cls.PREFIX_STATUS_ATTRIBUTE):
            item = attribute[len(cls.PREFIX_STATUS_ATTRIBUTE):]
        return item

    ########################################################################
    @classmethod
    def _clasify_ToolBuildError(cls, item, report, exc):
        return cls.status(STATUS_BUILDERROR, report.when)
    
    @classmethod
    def _clasify_ToolError(cls, item, report, exc):
        return cls.status(STATUS_GENERALERROR, report.when)

    @classmethod
    def _clasify_xml_ToolError(cls, result):
        result_log = result.get('log')
        status_id = STATUS_GENERALERROR

        if re.search('has timed out', result_log):
            status_id = STATUS_TIMEOUT
        return cls.status(status_id, STATUS_PHASE_CALL)

    @classmethod
    def _clasify_other(cls, item, report, exc):
        for id, attributes in cls.get_status_attributes(False).items():
            status = cls(id, *attributes, phase=report.when)
            if status.search(exc):
                return status
        return cls.status(STATUS_GENERALERROR, report.when)

    @classmethod
    def _clasify_xml_other(cls, result):
        data = AttrDict(result)
        return cls.status(STATUS_GENERALERROR, STATUS_PHASE_CALL)

    def search(self, exc):
        if not self.patterns:
            return False

        for pattern in self.patterns:
            if pattern.search(exc):
                return True
        return False
            
    def to_db_object(self):
        return StatusDBModel(id=self.status_id, code=self.code, description=self.description)

    def __repr__(self):
        return "%s(id=%d, code=%s, desc='%s')"%(self.__class__.__name__, self.status_id, self.code, self.description)
    
    def __eq__(self, other):
        return self.status_id == other.status_id
    
    def __lt__(self, other):
        return self.status_id < other.status_id
    
    def __gt__(self, other):
        return self.status_id > other.status_id
    
class StatusBootstrap(Status):
    SUPPORT_COMMON_ERRORS = False
    
    ITEM_ID = 5
    ITEM_NAME = 'bootstrap'
    PREFIX = 'BOOTSTRAP'
    
    STATUS_EXIT_OK = (0, 'No errors occured during build', None)
    STATUS_EXIT_FAIL = (1, 'General build error', None)
    STATUS_EXIT_FAIL_PACKAGING = (2, 'Packaging failed', None)
    STATUS_EXIT_FAIL_MODEL = (3, 'Model worker failed', None)
    STATUS_EXIT_FAIL_CLANG = (10, 'Clang worker failed', None)
    STATUS_EXIT_FAIL_CONTRIB = (15, 'Contrib worker failed', None)
    STATUS_EXIT_FAIL_ECLIPSE = (20, 'Eclipse CDT worker failed', None)
    STATUS_EXIT_FAIL_GNU_BINUTILS = (25, 'GNU Binutils worker failed', None)
    STATUS_EXIT_FAIL_IDE = (30, 'IDE worker failed', None)
    STATUS_EXIT_FAIL_INSTALLER = (35, 'Installer worker failed', None)
    STATUS_EXIT_FAIL_LIBRARY = (40, 'Library worker failed', None)
    STATUS_EXIT_FAIL_LLVM = (45, 'LLVM worker failed', None)
    STATUS_EXIT_FAIL_LMX = (50, 'LMX worker failed', None)
    STATUS_EXIT_FAIL_MINGW = (55, 'Mingw worker failed', None)
    STATUS_EXIT_FAIL_MSYS2 = (60, 'Msys2 worker failed', None)
    STATUS_EXIT_FAIL_RTL_CACHE = (65, 'RTL template cache worker failed', None)
    STATUS_EXIT_FAIL_THIRD_PARTY = (70, 'Third party tools worker failed', None)
    STATUS_EXIT_FAIL_TOOLS = (75, 'Tools worker failed', None)
    STATUS_EXIT_FAIL_VIP_DATA = (80, 'VIP data worker failed', None)
    STATUS_EXIT_FAIL_VIP_JTAG = (85, 'VIP JTAG worker failed', None)
    STATUS_EXIT_FAIL_ZERO_TOLERANCE = (90, 'Zero tolerance check worker failed', None)
    STATUS_EXIT_FAIL_LLDB = (95, 'Lldb worker failed', None)
    STATUS_EXIT_FAIL_OPENOCD = (100, 'OpenOCD check worker failed', None)

class StatusInternal(Status):
    SUPPORT_COMMON_ERRORS = False
    ITEM_ID = 0
    ITEM_NAME = 'internal'

    STATUS_OK = (1, 'No errors occured during execution', None)
    STATUS_EXIT_TESTSFAILED = (2, 'Some tests have failed during execution', None)
    STATUS_EXIT_INTERRUPTED = (3, 'Execution has been terminated by user', None)
    STATUS_EXIT_INTERNALERROR = (4, 'Mastermind internal error', None)
    STATUS_EXIT_USAGEERROR = (5, 'Mastermind usage error', None)
    STATUS_EXIT_NOTESTSCOLLECTED = (6, 'No tests were collected', None)

    STATUS_FAILED = (STATUS_FAILED, 'Test Failed', None)
    STATUS_INVALIDCOMMAND = (10, 'Invalid Command', None)

    @classmethod
    def _clasify_InvalidCommand(cls, item, report, exc):
        return cls.status(cls.STATUS_INVALIDCOMMAND[0], report.when)

    @classmethod
    def _clasify_other(cls, item, report, exc):
        return cls.status(cls.STATUS_FAILED[0], report.when)

class StatusModelCompilation(Status):
    ITEM_ID = 1
    ITEM_NAME = MODEL
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[MODEL])
    
    PREFIX = 'MASTERMIND_' + MODEL.upper()

class StatusSemantics(Status):
    ITEM_ID = 2
    ITEM_NAME = SEMANTICS
    TASK_PATTERN = '^_semextr_'
    
    PREFIX = 'MASTERMIND_' + SEMANTICS.upper()


class StatusAssembler(Status):
    ITEM_ID = 3
    ITEM_NAME = ASSEMBLER
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[ASSEMBLER])
    
    PREFIX = 'MASTERMIND_' + ASSEMBLER.upper()

class StatusDisassembler(Status):
    ITEM_ID = 4
    ITEM_NAME = DISASSEMBLER
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[DISASSEMBLER])
    
    PREFIX = 'MASTERMIND_' + DISASSEMBLER.upper()

class StatusCompiler(Status):
    ITEM_ID = 5
    ITEM_NAME = COMPILER
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[COMPILER])
    
    PREFIX = 'MASTERMIND_' + COMPILER.upper()

class StatusLibraries(Status):
    ITEM_ID = 6
    ITEM_NAME = LIBS
    TASK_PATTERN = '^_libs_'
    
    PREFIX = 'MASTERMIND_' + LIBS.upper()

class StatusSimulator(Status):
    ITEM_ID = 7
    ITEM_NAME = SIMULATOR
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[SIMULATOR])
    
    PREFIX = 'MASTERMIND_' + SIMULATOR.upper()

class StatusDebugger(Status):
    ITEM_ID = 8
    ITEM_NAME = DEBUGGER
    
    PREFIX = 'MASTERMIND_' + DEBUGGER.upper()
    
    @classmethod
    def _clasify_xml_ToolError(cls, result):
        result_log = result.get('log')
        status_id = STATUS_GENERALERROR

        if re.search('Timeout', result_log):
            status_id = STATUS_TIMEOUT
        return cls.status(status_id, STATUS_PHASE_CALL)
    

class StatusProfiler(Status):
    ITEM_ID = 9
    ITEM_NAME = PROFILER
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[PROFILER])
    
    PREFIX = 'MASTERMIND_' + PROFILER.upper()

class StatusCosimulator(Status):
    ITEM_ID = 10
    ITEM_NAME = COSIMULATOR
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[COSIMULATOR])
    
    PREFIX = 'MASTERMIND_' + COSIMULATOR.upper()

class StatusRandomAssembler(Status):
    ITEM_ID = 11
    ITEM_NAME = RANDOM_ASM
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[RANDOM_ASM])
    
    PREFIX = 'MASTERMIND_' + RANDOM_ASM.upper()

class StatusRtl(Status):
    ITEM_ID = 12
    ITEM_NAME = RTL
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[RTL])
    
    PREFIX = 'MASTERMIND_' + RTL.upper()
    
class StatusUvm(Status):
    ITEM_ID = 13
    ITEM_NAME = UVM
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[UVM])
    
    PREFIX = 'MASTERMIND_' + UVM.upper()
    
    STATUS_TIMEOUT_DUT = (10, 'DUT Timeout', None)
    STATUS_TIMEOUT_GM = (11, 'Golden Model Timeout', None)
    STATUS_TIMEOUT_DUT_AND_GM = (12, 'DUT and Golden Model Timeout', None)
    
    @classmethod
    def _clasify_ToolError(cls, item, report, exc):
        metadata = getattr(report, 'metadata', [])
        
        uvm_report_path = None
        for md in metadata:
            if md['name'] == 'uvm_report_path':
                uvm_report_path = md['value']
                break

        if uvm_report_path and os.path.isfile(uvm_report_path):
            with open(uvm_report_path, 'r') as uvm_report:
                for linenum, line in enumerate(uvm_report):
                    if linenum == 0:
                        continue
                    elif 'timeout (DUT)' in line:
                        return cls.status(cls.STATUS_TIMEOUT_DUT[0], report.when)
                    elif 'timeout (GOLD)' in line:
                        return cls.status(cls.STATUS_TIMEOUT_GM[0], report.when)
                    elif 'timeout (DUT and GOLD)' in line:
                        return cls.status(cls.STATUS_TIMEOUT_DUT_AND_GM[0], report.when)
        
        return super(StatusUvm, cls)._clasify_ToolError(item, report, exc)        
        

   
class StatusUvmFu(Status):
    ITEM_ID = 14
    ITEM_NAME = 'uvm_fu'
    TASK_PATTERN = '^{}$'.format(TOOL2TASK[_UVM_FU])
    
    PREFIX = 'MASTERMIND_UVMFU'

class StatusTools(Status):
    ITEM_ID = 15
    ITEM_NAME = 'task_tools'
    TASK_PATTERN = '^_(sdk|hdk)_tools$'
    
    PREFIX = 'MASTERMIND_TASKTOOLS'

def status_classes():
    """Extract Status* classes from current module.
    
    :return: Set of class objects implementing statuses.
    :rtype: set
    """
    module = sys.modules[__name__]
    classes = set()
    for name, cls in inspect.getmembers(module, inspect.isclass):
        # getmembers returns classes from imported modules as well,
        # make sure that only classes implemented in this module
        # are considered 
        if cls.__module__ != module.__name__:
            continue
        # Take only relevant class and skip base Status class 
        # (every status must have its own class)
        if name == 'Status' or not name.startswith('Status'):
            continue
        classes.add(cls)
    return classes

def generate_statuses():
    """ Generate all available statuses from its classes.
    """
    
    # Prefix for attributes which represent statuses
    prefix = Status.PREFIX_STATUS_ATTRIBUTE
        
    def _get_attributes(item):
        """Extract status attributes from the class.
        
        :param item: Class object which represents status item.
        :return: Dictionary with attribute names as keys and
                a triplet representing status
                (status_code, description, <PatternStatus> instance).
        :rtype: dict
        """
        attrs = {}
        for attribute in item.__dict__:
            # Get status attributes only
            if attribute.startswith(prefix):
                attrs[attribute] = getattr(item, attribute) 
        return attrs

    def _status_name(item):
        """Cut status prefix from attribute name
        """
        if item.startswith(prefix):
            item = item[len(prefix):]
        return item

    statuses = {}
    
    # Status generation
    # * Every defined status (STATUS_* attribute) is generated
    #   for each execution phase (setup, call, teardown) automatically.
    # * For each status class, there exist common errors, which do not 
    #   need to be specified explicitely (e.g. timeout error).
    for cls in status_classes():
        for phase in STATUS_PHASES[1:]:
            # Generate user-defined statuses
            for attribute, value in cls.get_status_attributes().items():
                # Unpack triplet
                sid, description, patterns = value
                # EXIT_* statuses do not have phase specified
                if _status_name(attribute).startswith(('EXIT', 'OK')):
                    s = cls(sid, _status_name(attribute), description=description)
                else:
                    s = cls(sid, _status_name(attribute), description=description, phase=phase, patterns=patterns)
                statuses[s.status_id] = s
            # Generate common errors for each item
            if cls.SUPPORT_COMMON_ERRORS:
                for sid, (name, description, patterns) in COMMON_ERRORS.items():
                    description = description.format(cls.ITEM_NAME.capitalize())
                    s = cls(sid, _status_name(name), description=description, phase=phase, patterns=patterns)
                    statuses[s.status_id] = s

    return statuses

   
