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
#
from collections import OrderedDict
import os

ROOT_PACKAGE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
"""Path to root directory of Mastermind package."""
ROOT_REPOSITORY = os.path.dirname(ROOT_PACKAGE)
"""Path to directory of Mastermind repository."""
EXE_EXTENSION = '.exe' if os.name == 'nt' else ''
"""Platform dependent extension of executable files."""
DATABASE_ENV_VARNAME = 'MASTERMIND_DB'
"""Environmental variable containing database string."""
DATABASE_DEBUG_URL = 'mysql://root@localhost/mastermind'

# Tool names
MODEL = 'model'
SEMANTICS = 'semantics'
ASSEMBLER = 'assembler'
DISASSEMBLER = 'disassembler'
COMPILER = 'compiler'
LIBS = 'libs'
SIMULATOR = 'simulator'
COSIMULATOR = 'cosimulator'
DEBUGGER = 'debugger'
PROFILER = 'profiler'
RANDOM_ASM = 'random_asm'
QEMU = 'qemu'
DOCUMENTATION = 'doc'
SDK = 'sdk'
RTL = 'rtl'
UVM = 'uvm'
HDK = 'hdk'

# Names for private tasks
_SDK_TOOLS = 'sdk_tools'
_HDK_TOOLS = 'hdk_tools'
_BACKEND = 'backend'
_INCLUDE = 'include'
_UVM_FU = 'uvm_fu'
_REMOVE_OPTIONS = 'remove_options'

# Build system tasks
TASK_MODEL = 'model'
TASK_ASSEMBLER = 'asm'
TASK_DISASSEMBLER = 'dsm'
TASK_COMPILER = 'compiler'
TASK_LIBS = 'libs'
TASK_SIMULATOR = 'sim'
TASK_COSIMULATOR = 'cosim'
TASK_DEBUGGER = 'dbg'
TASK_PROFILER = 'prof'
TASK_RANDOM_ASM = 'random_asm'
TASK_DOCUMENTATION = 'doc'
TASK_SDK = 'sdk'
TASK_RTL = 'rtl'
TASK_UVM = 'uvm'
TASK_HDK = 'hdk'
TASK_PUBLISH_IP = 'publish_ip'

# Private tasks
TASK_SDK_TOOLS = '_sdk_tools'
TASK_HDK_TOOLS = '_hdk_tools'
TASK_BACKEND = '_backend'
TASK_INCLUDE = '_include'
TASK_UVM_FU = '_uvm_fu'
TASK_REMOVE_OPTIONS = '_remove_options'

IA_TOOLS = [ASSEMBLER, DISASSEMBLER, COMPILER, LIBS, SIMULATOR, COSIMULATOR, DEBUGGER, PROFILER, QEMU, SDK]
"""List of IA tools."""
CA_TOOLS = [SIMULATOR, COSIMULATOR, DEBUGGER, PROFILER, SDK, RTL, UVM, HDK]
"""List of CA tools."""
TOOLS = set(IA_TOOLS + CA_TOOLS)
SDK_TOOLS = [ASSEMBLER, DISASSEMBLER, COMPILER, LIBS, SIMULATOR, DEBUGGER, PROFILER, SDK]
"""List of SDK tools."""
HDK_TOOLS = [RTL, UVM, HDK]
"""List of HDK tools."""

TOOL2TASK = {MODEL: TASK_MODEL,
             ASSEMBLER: TASK_ASSEMBLER,
             DISASSEMBLER: TASK_DISASSEMBLER,
             COMPILER: TASK_COMPILER,
             LIBS: TASK_LIBS,
             SIMULATOR: TASK_SIMULATOR,
             COSIMULATOR: TASK_COSIMULATOR,
             DEBUGGER: TASK_DEBUGGER,
             PROFILER: TASK_PROFILER,
             RANDOM_ASM: TASK_RANDOM_ASM,
             DOCUMENTATION: TASK_DOCUMENTATION,
             SDK: TASK_SDK,
             RTL: TASK_RTL,
             UVM: TASK_UVM,
             HDK: TASK_HDK,
             _SDK_TOOLS: TASK_SDK_TOOLS, 
             _HDK_TOOLS: TASK_HDK_TOOLS,
             _BACKEND: TASK_BACKEND,
             _INCLUDE: TASK_INCLUDE,
             _UVM_FU: TASK_UVM_FU, 
             _REMOVE_OPTIONS: TASK_REMOVE_OPTIONS,
             }
"""Maps user-friendly tool names to Codasip build system tasks."""

ITEM2TITLE = OrderedDict([(TASK_MODEL, 'Model Compilation'),
                          (SEMANTICS, 'semantics'),
                          (TASK_ASSEMBLER, 'Assembler'),
                          (TASK_DISASSEMBLER, 'Disassembler'),
                          (TASK_COMPILER, 'C/C++ Compiler'),
                          (TASK_LIBS, 'SDK Libraries'),
                          (TASK_SIMULATOR, 'Simulator'),
                          (TASK_COSIMULATOR, ' Co-simulator'),
                          (TASK_DEBUGGER, 'Debugger'),
                          (TASK_PROFILER, 'Profiler'),
                          (TASK_RANDOM_ASM, 'Random Assembler Programs'),
                          (TASK_DOCUMENTATION, 'Documentation'),
                          (TASK_SDK_TOOLS, 'SDK Tools'),
                          (TASK_SDK, 'SDK'),
                          (TASK_RTL, 'RTL'),
                          (TASK_UVM_FU, 'UVM Verification of functional units'),
                          (TASK_UVM, 'UVM Verification'),
                          (TASK_HDK_TOOLS, 'HDK Tools'),
                          (TASK_HDK, 'HDK'),
                          #(TASK_BACKEND, 'C/C++ Backend'),
                          #(TASK_INCLUDE, 'Includes'),
                          (TASK_PUBLISH_IP, 'IP Publication'),
                          (TASK_REMOVE_OPTIONS, 'Remove Options')
                          ])


IA_TASKS = list(set([TOOL2TASK.get(tool, tool) for tool in IA_TOOLS] + [TASK_MODEL, TASK_BACKEND,
                                                                   TASK_INCLUDE]))
"""List of tasks for IA models."""
CA_TASKS = list(set([TOOL2TASK.get(tool, tool) for tool in CA_TOOLS] + [TASK_MODEL, TASK_UVM_FU]))
"""List of tasks for CA models."""
TASKS = list(set(IA_TASKS + CA_TASKS))
"""List of tasks for models."""
ASIP_TASKS = [TASK_ASSEMBLER, TASK_DISASSEMBLER, TASK_PROFILER, TASK_SIMULATOR, TASK_COMPILER, TASK_LIBS, TASK_SDK, 
              TASK_COSIMULATOR, TASK_DEBUGGER, TASK_RANDOM_ASM, TASK_RTL, TASK_UVM, TASK_HDK, TASK_UVM_FU]
"""List of tasks for ASIP models."""
LEVEL_TASKS = [TASK_PROFILER, TASK_SIMULATOR, TASK_SDK, TASK_COSIMULATOR, TASK_RTL, TASK_UVM, TASK_HDK]
"""List of tasks for LEVEL models."""

TEST_TYPE_DEFAULT = 'default'
TEST_TYPE_IP_NIGHTLY = 'ip_nightly'
TEST_TYPE_IP_RELEASE = 'ip_release'
TEST_TYPE_STUDIO_NIGHTLY = 'studio_nightly'
TEST_TYPE_STUDIO_RELEASE = 'studio_release'
TEST_TYPES = [TEST_TYPE_DEFAULT, TEST_TYPE_IP_NIGHTLY, TEST_TYPE_IP_RELEASE,
              TEST_TYPE_STUDIO_NIGHTLY, TEST_TYPE_STUDIO_RELEASE]

CACHE_DIR = 'cache'
"""Path to Mastermind cache directory. Cache stores project repositories, generated tools and cached data for testcases."""
DEFAULT_BUILD_DIR = 'default_tools'
"""Path to build directory with tools using default model configuration (relative to :py:data:`CACHE_DIR`)."""
CACHED_BUILD_DIR = 'configured_tools'
"""Path to build directory with tools using overriden model configuration (relative to :py:data:`CACHE_DIR`)."""

# NFS root for 3rd party tools
NFS_ROOT = os.path.join(r"//nfs.codasip.com", "var", "nfs") if os.name == 'nt' else os.path.join('/', 'mnt', 'edatools')
"""Path to Codasip network file system."""