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
# Desc: Mastermind utility functions and classes.
#
from distutils import dir_util
import os
import platform
import re
import shutil
import stat
import string
import subprocess
import sys
import tarfile
import tempfile
import zipfile

try:
    from cStringIO import StringIO
except ImportError:
    pass


from mastermind.lib import ROOT_PACKAGE, NFS_ROOT, EXE_EXTENSION
from mastermind.lib.exceptions import ProcessError

COMMA_RE = re.compile(r"\s*,\s*(?=(?:[^'\"\[\]]|'[^']*'|\"[^\"]*\"|\[[^\]]*\])*$)")
"""Regular expression for argument parser, so multiple values for single argument
    may be passed. If a value is enclosed with quotes ("" or '') or square brackets [],
    then argument values are not split by comma.
 
    :Examples:
    
    `key1=val1,key2=val2` --> `['key1=val1', 'key2=val2']
    `key1=[val1,val2],key2=val3` --> `['key1=[val1,val2]', 'key2=val3']
"""


class AttrDict(dict):
    """Enables attribute access into dictionary. dict['a'] == dict.a """

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    # def __getattr__(self, key):
    #    """Do no raise AttributeError on non-existing key"""
    #    return self.get(key, None)


class BufferDuplicator(object):
    """Simple wrapper that duplicates buffer."""

    def __init__(self, original, supress_buffer=False, autoflush=True):
        """
        :param original: A file-like object which should be duplicated.
        :type original: file
        """
        self.original = original
        self.supress = supress_buffer
        self.autoflush = autoflush
        self.buffer = StringIO()

    def write(self, text):
        """Writes the duplicated text to original and internal buffers.
        
        :param text: Text to duplicate.
        :type text: str
        """
        if not self.supress:
            self.original.write(text)
            if self.autoflush:
                self.original.flush()
        self.buffer.write(text)

    def __getattr__(self, name):
        """Called for other file-like object methods."""
        return self.original.__getattribute__(name)

    def close(self):
        self.original.close()
        self.buffer.close()

    def getvalue(self):
        """Return string from internal buffer."""
        return self.buffer.getvalue()


class OutputDuplicator():
    """
    Duplicates standard output and error into internal buffers,
    which are accessible while the instance exists. 
    
    Supports context manager.
    
    Writing to stdout or stderr does standard behaviour. 
    
    >>> with OutputDuplicator() as duplicator:
    ...     print("Message to standard output")
    ...     error("Message to standard error")
    Message to standard output.
    
    Stdout and stderr content is available after writing. 
    
    >>> duplicator.out.getvalue()
    Message to standard output.
    >>> duplicator.err.getvalue()
    Message to standard error.
    
    
    """

    def __init__(self, supress_output=False, supress_error=False):
        """Constructor.
        
        :ivar saved: Original stdout and stderr buffer.
        :ivar out: duplicated stdout buffer
        :ivar err: duplicated stderr buffer
        :vartype saved: tuple
        :vartype out: :py:class:`BufferDuplicator`
        :vartype err: :py:class:`BufferDuplicator`
        """
        # Save original buffers and create duplicators
        self.saved = sys.stdout, sys.stderr
        self.out = BufferDuplicator(sys.stdout, supress_output)
        self.err = BufferDuplicator(sys.stderr, supress_error)

    def __enter__(self):
        sys.stdout = self.out
        sys.stderr = self.err
        return self

    def __exit__(self, type, value, tb):
        sys.stdout, sys.stderr = self.saved


class Repository():
    """Simple git repository wrapper."""

    USER = 'git'
    """Remote user name"""
    REMOTE = 'gitlab.codasip.com'
    """Remote server URL"""

    def __init__(self, namespace, repository, dir=None):
        """Constructor.
        
        :param namespace: Repository namespace. 
        :param repository: Repository name.
        :param dir: Path to git repository root. Defaults to repository name.
        :type namespace: str
        :type repository: str
        :type dir: str
        :ivar url: Absolute URL to GIT repository.
        :vartype: str
        
        :Examples:
        
        Repository not cloned yet
        
        >>> Repository('codasip_utils-studio', 'tools')
        <Repository codasip_utils-studio:tools:None, dir=/home/jenkins/git/codasip_urisc, state=uninitialized>
        
        Initialize and clone repository
        
        >>> repo = Repository('codasip_utils-studio', 'tools')
        >>> repo.clone('devel')
        >>> repo
        <Repository codasip_utils-studios:devel, dir=/home/jenkins/git/codasip_urisc, state=initialized>
        """
        self.namespace = namespace
        self.repository = repository[:-4] if repository.endswith('.git') else repository
        self.url = "{}@{}:{}/{}".format(self.USER, self.REMOTE, namespace, repository)
        self.dir = dir
        self._branch = None

        # Automatically set dir
        if dir is None:
            dir = os.path.join(os.getcwd(), self.repository)
        self.dir = os.path.abspath(dir)
        if not self.url.endswith('.git'):
            self.url += '.git'

    def clone(self, branch=None):
        """Clone repository.
        
        :param branch: Branch to clone. If ``None``, then default branch is cloned. ``branch`` can also
            be a tag. If a tag is passed, then default branch is cloned first and the its checkouted to 
            specific tag.
        :type branch: str or None
        :raises `~mastermind.lib.exceptions.ProcessError`: If clone command fails.
        
        .. note::
            
            Clones recursively.
        
        """
        args = ['git', 'clone', '--recursive', self.url, self.dir]

        if branch:
            args += ['-b', branch]
        info("Cloning {} to {}{}".format(self.url, self.dir, ' (branch %s)' % branch if branch else ''))
        run(args)

        if branch:
            self._branch = branch

    def pull(self):
        """Pull repository.
        
        :raises `~mastermind.lib.exceptions.ProcessError`: If pull command fails.
        """
        args = ['git', 'pull']
        info("Pulling {}".format(self.dir))
        run(args, cwd=self.dir)

    def checkout(self, branch, force=False):
        """Checkout a certain branch.
        
        :param branch: Branch to checkout.
        :type branch: str
        :raises `~mastermind.lib.exceptions.ProcessError`: If checkout command fails.
        """
        if branch == self.branch and not force:
            info("Repository {} is already on branch {}".format(self.repository, branch))
            return
        args = ['git', 'checkout', branch]

        # just to be sure, do fetch
        self._fetch()
        info("Switching from {} to {} {} in {}".format(self.branch, type, branch, self.dir))
        run(args, cwd=self.dir)
        self._branch = branch

    def synchronize(self, branch=None):
        """Synchronize repository with remote server.
        
        If repository has not been initialized yet, then
        it is recursively cloned from remote server.
        
        :param branch: Branch to synchronize local repository with.
            If ``None`` then actual (if already cloned) or default (if not cloned)
            branch will be used.
        :type branch: str or None
        :raises `~mastermind.lib.exceptions.ProcessError`: If any GIT command fails.
        
        """
        # Already cloned, just pull
        if self.is_initialized():
            info("Repository already cloned, trying to checkout or pull")
            if branch and branch != self.branch:
                self.checkout(branch)
            else:
                self.pull()
            self._get_submodules()
        else:
            self.clone(branch)
            # Git <= v1.7 does not support tag clone, manual checkout is needed
            # afterwards.
            self.checkout(branch, force=True)

    def _get_submodules(self):
        """Clone submodules.
        
        :raises `~mastermind.lib.exceptions.ProcessError`: If submodule command fails.
        """
        info("Checking-out submodules")
        args = ['git', 'submodule', 'init']
        run(args, cwd=self.dir)
        args = ['git', 'submodule', 'update']
        run(args, cwd=self.dir)

    def _fetch(self):
        """Standard git fetch of the repository.
        
        :raises `~mastermind.lib.exceptions.ProcessError`: If fetch command fails.
        """
        args = ['git', 'fetch', '--tags']

        info("Fetching %s..." % self.repository)
        run(args, cwd=self.dir)

    def is_initialized(self):
        """Detect if repository is cloned"""
        return (os.path.isdir(os.path.join(self.dir, '.git')) and
                os.listdir(self.dir) > 1)

    @property
    def branch(self):
        """Return current branch."""
        # Not cloned yet
        if not self.is_initialized():
            return None
        # Use cached branch
        if self._branch:
            return self._branch

        args = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
        out = run(args, get_output=True, cwd=self.dir)
        branch = None
        if out:
            branch = out.rstrip('\n').split('/')[-1]

        # Repository might be cloned using fetch and checkout.
        # In that case branch contains 'HEAD' -> use another way
        # to detect branch.
        if not branch or branch == 'HEAD':
            args = ['git', 'log', '-n', '1', '--pretty=%d', 'HEAD']
            out = run(args, get_output=True, cwd=self.dir).strip()
            # First try to find branch on origin. If it is not found,
            # then try to find tag.
            match_branch = re.search('origin/([\w\-\._]+)', out)
            match_tag = re.search('tag: ([\w\-\._]+)', out)
            if match_branch:
                branch = match_branch.group(1)
            elif match_tag:
                branch = match_tag.group(1)

        self._branch = branch
        return branch

    @staticmethod
    def branches(url, pattern=None):
        """Detect all branches of repository matching the pattern.
        
        Pattern may be either one or multiple regular expressions. In case
        its a list of regular expressions, then all of the patterns must 
        match the branch name to approve it.
        
        :param pattern: Regular expression to filter branches.
        :type pattern: str
        :return: Repository branches matching the regular expression.
        :rtype: list
        :raises `~mastermind.lib.exceptions.ProcessError`: If branch list fetch fails.
        
        """
        cmd = ['git', 'ls-remote', '--tags', '-h', url]
        out = run(cmd, get_output=True)

        if pattern and not is_iterable(pattern):
            pattern = [pattern]

        res = set()
        if out:
            for line in out.split('\n'):
                branch = line.split('/')[-1].rstrip()
                # When listing tags, each tag is shown twice, e.g.
                # refs/tags/7.2.0-test
                # refs/tags/7.2.0-test^{}
                # So the second is skipped
                if branch.endswith('^{}'):
                    continue
                if pattern is not None and all(re.search(p, branch) for p in pattern):
                    res.add(branch)
        return res

    @property
    def current_commit(self):
        """Return current commit hash of repository."""
        if not self.is_initialized():
            return None
        cmd = ['git', 'rev-parse', 'HEAD']
        commit = run(cmd, get_output=True, cwd=self.dir).rstrip()
        return commit

    @staticmethod
    def checkout_branches(namespace, repository, dir=None, pattern=None, pull=True):
        """
        Checkout multiple branches of a single repository. Branches are cloned
        into separate directories with the appropriate branch name.
        
        :param namespace: Repository namespace.
        :param repository: Repository name.
        :param dir: Path to git repositories. Each branch will be cloned to its own directory.
        :param pattern: Regular expression for branch filtering.
        :param pull: Pull branch if it is cloned already.
        :type namespace: str
        :type repository: str
        :type dir: str or None
        :type pattern: str or None
        :type pull: bool
        :return: List of checkouted repositories.
        :rtype: list
        
        :raises `ValueError`: If no branch matching the pattern(s) has been found.
        """

        # Base repository
        base = Repository(namespace, repository)
        branches = base.branches(base.url, pattern)

        if not branches:
            raise ValueError("No branch has been matched by pattern(s) {}".format(pattern))
        repos = []
        for branch in branches:
            # Set repository root
            dst = dir if dir else base.repository
            dst = os.path.join(dst, branch)
            repo = Repository(namespace, repository, dst)
            if pull or not repo.is_initialized():
                repo.synchronize(branch)
            repos.append(repo)
        return repos

    @property
    def id(self):
        """Build repository ID.
        
        :return: Unique repository ID with namespace, repository
            and branch. These parts are separated by colon.
        :rtype: str
        """
        lst = [self.namespace, self.repository]
        if self.branch:
            lst.append(self.branch)

        return ':'.join(lst)

    @classmethod
    def from_url(cls, url, dir=None):
        """Initialize repository from git url."""
        # Cut user and server
        url = url.split(':')[-1]
        url = url.split('/')
        namespace, repository = url[-2], url[-1]
        return cls(namespace, repository, dir)

    @classmethod
    def from_dir(cls, dir):
        """Initialize repository from cloned directory.
        
        :param dir: Directory containing GIT repository.
        :type dir: str
        :return: Initialized Repository object.
        :rtype: :py:class:`Repository`
        :raises `~mastermind.lib.exceptions.ProcessError`: If directory is not a GIT repository.
        """
        # Get remote url
        cmd = ['git', 'config', '--get', 'remote.origin.url']
        url = run(cmd, get_output=True, cwd=dir).rstrip()
        # dir might be subdirectory of an actual git repository
        cmd = ['git', 'rev-parse', '--show-toplevel']
        dir = run(cmd, get_output=True, cwd=dir).rstrip()
        return cls.from_url(url, dir)

    def __repr__(self):
        return "<Repository {}, dir={}, state={}>".format(self.id, self.dir,
                                                          ("initialized" if self.is_initialized()
                                                           else "uninitialized"))


class Verbosity():
    """Verbosity levels for info."""
    ALWAYS = 0
    DEFAULT = 1
    LOW = 2
    DEBUG = 3
    ALL = 4


class _Logger():
    """Logging class."""

    def __init__(self, verbosity=Verbosity.DEFAULT, out=None):
        self.verbosity = verbosity
        self.out = out

    def log(self, type, msg, *args, **kwargs):
        verb = Verbosity.DEFAULT

        if (type != 'info' or verb >= self.verbosity):
            msg = msg.format(*args, **kwargs)
            if (not msg.endswith('\n')):
                msg += '\n'
            out = self.out
            if not out:
                out = sys.stdout
            out.write('{0}: {1}'.format(type, msg))
            # Flush automatically
            if hasattr(out, 'flush'):
                out.flush()


def debug(msg, *args, **kwargs):
    if '--debug' not in sys.argv:
        return
    _Logger().log('debug', msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """Create info log entry with verbosity level."""
    verbosity = kwargs.pop('verbosity', None)
    if type(msg) is int:
        verbosity = msg
        msg = args[0]
        args = args[1:]
    elif not verbosity:
        verbosity = Verbosity.DEFAULT
    _Logger(verbosity).log('info', msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """Create warning log entry."""
    _Logger().log('warning', msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """Create error log entry."""
    _Logger(out=sys.stderr).log('error', msg, *args, **kwargs)


def fatal(msg, *args, **kwargs):
    """Create fatal log entry and terminate the script execution."""
    _Logger(out=sys.stderr).log('fatal', msg, *args, **kwargs)

####################################################################################################


def compress(sources, output, dir=None, method=None, mode=None,
             remove_sources=False, ignore_error=False):
    """Create a compressed archive from given sources.
    
    :param sources: List of files/directories which should be compressed.
    :param output: Output filename.
    :param dir: Path where archive will be created. It must already exist.
    :param method: Used comprimation method. *zip* or *tar* is supported.
    :param mode: Filemode of archive. See documentation of tarfile and zipfile
                 for further information.
    :param remove_sources: Remove original files which were compressed .
    :param ignore_error: If ``False``, then exception is raised when an error occurs,
        otherwise boolean value representing result (``True`` if success) is returned.
    :type sources: list or str
    :type output: str
    :type dir: str
    :type method: str
    :type mode: str
    :type remove_sources: bool
    :type ignore_error: bool
    :todo: Document ``raises``.
    """
    # Set defaults
    if output.endswith('.zip'):
        method = 'zip'
    else:
        method = 'tar'
    if mode is None:
        mode = 'w' if method == 'zip' else 'w|gz'
    if not is_iterable(sources):
        sources = [sources]

    if dir:
        output = os.path.join(dir, output)

    def _tar():
        with tarfile.open(output, mode) as tf:
            for source in sources:
                tf.add(source, arcname=os.path.basename(source))

    def _zip():
        zf = zipfile.ZipFile(output, mode)
        for source in sources:
            if os.path.isfile(source):
                zf.write(source, arcname=os.path.basename(source))
            elif os.path.isdir(source):
                # Must walk through each file manually
                for root, _, files in os.walk(source):
                    for f in files:
                        zf.write(os.path.join(root, f),
                                 arcname=os.path.relpath(os.path.join(root, f),
                                                         os.path.dirname(source)))
            else:
                zf.close()
                raise RuntimeError("Error while compressing {}. Path does not exist".format(source))
        zf.close()

    ###########################################
    if method == 'tar':
        compress_method = _tar
    elif method == 'zip':
        compress_method = _zip
    elif ignore_error:
        error("Unknown compression method: {}", method)
        return False
    else:
        raise RuntimeError("Unknown compression method: {}", method)

    # Compress and remove sources if required
    try:
        compress_method()

        if remove_sources:
            for source in sources:
                if os.path.isfile(source):
                    os.remove(source)
                else:
                    rmtree(source)
    except:
        if not ignore_error:
            raise

        return False
    return True


def copy(src, dest, copy_root=False, debug=False):
    """Copy file or directory.
    
    If ``dest`` directory doesn't exist, it is automatically created.
    If ``src`` is file, ``src`` is copied with same basename into destination directory.
    If src is directory, content of the directory is copied into ``dest``. 
    
    :param src: Source file or directory.
    :param dest: Destination.
    :param copy_root: If ``True``, entire directory include its root dir is copied into ``dest``.
    :type src: str
    :type dest: str
    :type copy_root: bool
    
    """
    if os.path.isfile(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        if debug:
            info("Copying from {} to {}", src, dest)
        shutil.copy(src, dest)
    else:
        if copy_root:
            dest = os.path.join(dest, os.path.basename(src))

        if not os.path.isdir(dest):
            os.makedirs(dest)
        if debug:
            info("Copying from {} to {}", src, dest)
        dir_util.copy_tree(src, dest, preserve_symlinks=1)


def copy_network(src, dst, user, host, port=None, debug=False):
    remote = '@'.join([user, host])
    ssh = ['ssh', remote]
    if port:
        ssh += ['-p', str(port)]
    ssh += ['mkdir', '-p', dst]

    scp = ['scp']
    if port:
        scp += ['-P', str(port)]

    scp += ['-r', posix_path(src)]

    scp += ['{}:{}'.format(remote, posix_path(dst))]

    if debug:
        info("Creating directory on remote: {}:{}", remote, posix_path(src))
    run(ssh)
    if debug:
        info("Copying files from {} to {}:{}", posix_path(src), remote, posix_path(dst))
    run(scp)


def default_environment():
    """Create dictionary with usual Codasip environmental variables.
    
    :rtype: dict
    """
    env = os.environ.copy()
    license_server = 'licenses.codasip.com'
    env.setdefault('LMX_LICENSE_PATH', '{0}%6200'.format(license_server))
    env.setdefault('LM_LICENSE_FILE', '1717@{0}'.format(license_server))
    env.setdefault('CDS_LIC_FILE', '5280@{0}'.format(license_server))
    env.setdefault('XILINXD_LICENSE_FILE', '2100@{0}'.format(license_server))
    env.setdefault('ALDEC_LICENSE_FILE', '27009@{0}'.format(license_server))
    env.setdefault('SNPSLMD_LICENSE_FILE', '27020@{0}'.format(license_server))

    env['PYTHONPATH'] = os.path.dirname(ROOT_PACKAGE) + os.pathsep + env.get('PYTHONPATH', '')

    if is_codasip_cmdline():
        from codasip import RtlSimulationTool, SynthesisTool

        for tool in RtlSimulationTool + SynthesisTool:
            tool_execpath = get_edatool_info(tool).get('executable')
            if tool_execpath:
                info("Adding {} to path: {}", tool, os.path.dirname(tool_execpath))
                env['PATH'] = env['PATH'] + os.pathsep + os.path.dirname(tool_execpath)

    return env


def detect_project_version(project):
    """Find out ``CodalProject`` version.
    
    :param project: Path to project root.
    :type project: str
    :return: Project version if found, else ``None``.
    :rtype: str
    """
    version_file = None
    for root, _, files in os.walk(project):
        for f in files:
            if f == 'version.codal':
                version_file = os.path.join(root, f)
        if version_file:
            break

    if version_file:
        for line in file(version_file):
            m = re.search('\*\s*Version\W+([\d\.]+)', line)
            if m:
                return m.group(1)


def extract(archive, outdir=None, ignore_errors=False):
    """Extract tar or zip archive to directory.
    
    :param archive: Path to archive.
    :param outdir: Path, where archive will be extracted. By default process working
        directory.
    :param ignore_errors: If ``False``, then exception is raised when an error occurs,
        otherwise boolean value representing result (``True`` if success) is returned.
    :type archive: str
    :type outdir: str
    :type ignore_errors: bool
    :raises `~exceptions.RuntimeError`: If input archive is corrupted.
    """
    if outdir is None:
        outdir = os.getcwd()

    def _untar(archive, outdir):
        tf = tarfile.open(archive, 'r:*')
        for member in tf:
            tf.extract(member, outdir)

    def _unzip(archive, outdir):
        zf = zipfile.ZipFile(archive, 'r')
        zf.extractall(outdir)

    if tarfile.is_tarfile(archive):
        callable = _untar
    elif zipfile.is_zipfile(archive):
        callable = _unzip
    elif ignore_errors:
        error("Unknown format or corrupted archive: {}\n", archive)
        return False
    else:
        raise RuntimeError("Unknown format or corrupted archive: {}".format(archive))

    try:
        callable(archive, outdir)
    except:
        if not ignore_errors:
            raise
        return False
    return True


def get_edatool_info(tool):
    """
    Find ``tool`` installation directory and path to its executable. Search is performed
    on Codasip Network File System.
    
    :param tool: Tool name to search
    :type tool: str 
    :return: Dictionary containing installation information for ``tool``. 
        Key ``dir`` points to the installation directory, if tool is found.
        Key ``executable`` points to the tool executable if tool is found.
    :rtype: dict
    :raises `AssertionError`: If ``tool`` is not among the supported 3rd party tools.
    """
    from codasip import (RTL_SIM_QUESTA, RTL_SIM_RIVIERA, RTL_SIM_XCELIUM, RTL_SIM_INCISIVE, RTL_SIM_VCS,
                         SYNT_CADENCE_RC, SYNT_CADENCE_GENUS, SYNT_XILINX_ISE, SYNT_XILINX_VIVADO)
    #
    if os.name == 'nt':
        try:
            import winshell
        except ImportError:
            info("winshell package not installed, installing...")
            run([sys.executable, '-m', 'pip', 'install', 'winshell', 'pywin32', '--user'])
            try:
                import winshell
            except ImportError:
                info("Unable to reimport winshell after installation")
            else:
                info("winshell successfully installed.")
    # Windows 8.x does not support NFS  Basic and Pro version which are currently used in Codasip
    # infrastructure. EDA tools must be installed on the local machine in system's drive
    # root directory.
    def find_local_installation(tool):
        try:
            system_drive = [letter + ':/' for letter in string.ascii_lowercase
                            if os.path.exists(os.path.join(letter + ':/', 'Windows'))][0]
        except IndexError:
            error("Unable to detect system drive")
        else:
            # Iterate with reversed order to detect most recent version as first.
            for dir in os.listdir(system_drive)[::-1]:
                if re.search(tool, dir):
                    # Always use forward slash for installation directory.
                    return '/'.join([system_drive, dir])
        warning("Local installation of {} could not be found.", tool)

    # Dictionary for basic 3rd party tools info
    # The value is a tuple of (alias, vendor, binary), where alias is searched installation directory name.
    # If alias is None, then the tool name is used to search the installation directory.
    # Binary is relative path from installation directory to executable.
    tool_info = {RTL_SIM_QUESTA: ('questasim', 'mentor', os.path.join('win64' if os.name == 'nt' else
                                                                      'linux_x86_64', 'vsim' + EXE_EXTENSION)),
                 RTL_SIM_RIVIERA: (None, 'aldec', os.path.join('bin', 'vsimsa' + EXE_EXTENSION)),
                 RTL_SIM_XCELIUM: (None, 'cadence', os.path.join('tools', 'bin', '64bit', 'xmroot')),
                 RTL_SIM_INCISIVE: (None, 'cadence', os.path.join('tools', 'bin', '64bit', 'ncroot')),
                 RTL_SIM_VCS: (None, 'synopsys', os.path.join('bin', 'vcs')),
                 SYNT_CADENCE_RC: ('rc', 'cadence', os.path.join('tools.lnx86', 'bin', 'rc')),
                 SYNT_CADENCE_GENUS: ('genus', 'cadence', os.path.join('tools.lnx86', 'bin', 'genus')),
                 SYNT_XILINX_ISE: ('ise', 'xilinx', os.path.join('ISE_DS', 'ISE', 'bin', 'lin64', 'ise')),
                 SYNT_XILINX_VIVADO: ('vivado', 'xilinx', os.path.join('bin', 'vivado')),
                 }

    if tool_info.get(tool) is None:
        warning("Tool {} is not supported by Mastermind", tool)
        return {}
    alias, vendor, binary = tool_info.get(tool)
    alias = alias or tool
    # Absolute path to vendor directory
    edatool_vendor_dir = os.path.join(NFS_ROOT, 'software',
                            'windows' if os.name == 'nt' else 'linux',
                            vendor)
    dir_info = {}
    install_directory = None
    if os.path.exists(edatool_vendor_dir):
        # Find the installation directory
        # Linux tools might have symbolic link for tool,
        # so when link is found, use that one.
        for dirname in os.listdir(edatool_vendor_dir):
            path = os.path.join(edatool_vendor_dir, dirname)
            if re.search(alias, dirname):
                install_directory = path.replace('\\', '//')

                if os.name != 'nt' and os.path.islink(path):
                    break
                elif os.name == 'nt' and dirname.lower().endswith('.lnk'):
                    info("Found Windows shortcut for {}", tool)
                    #if 'winshell' not in sys.modules:
                    #    warning("Unable to read Windows shortcut (winshell module not installed), skipping")
                    #    continue
                    shortcut = winshell.shortcut(path)
                    install_directory = shortcut.path.replace('\\', '/')
                    break

    if install_directory is None and os.name == 'nt':
        info("Unable to find {} on NFS, searching for local installation...", tool)
        install_directory = find_local_installation(tool)

    if install_directory:
        dir_info['dir'] = install_directory

        binary = os.path.join(install_directory, binary)
        if os.path.exists(binary):
            dir_info['executable'] = os.path.join(install_directory, binary).replace('\\', '//')

    return dir_info


def get_system_info(version_length=1):
    """Detect basic operation system info.
    
    :param version_length: Number of version 
    
    :return: Dictionary containing OS name, version and architecture.
    :rtype: dict
    
    :Examples:
    
    >>> get_system_info()
    {'os': 'centos', 'version': (6), 'arch': 'x86_64}
    
    >>> get_system_info(version_length=2)
    {'os': 'centos', 'version': (6, 7), 'arch': 'x86_64}
    
    .. note::
        When calling on Windows server, the version is replaced for Windows 8.1
        for overall compatibility
    
    .. warning::
        
        It is not guaranteed that *version* key in result dictionary will be the same 
        length as `version_length`. Real lenght is only bouded above by `version_length`.
        For example, with `version_length=10`, the version tuple's length will still
        be three (in most cases - major, minor, build number).  
    
    """

    # Windows
    if os.name == 'nt':
        distro = 'windows'
        version_string = platform.win32_ver()[0]
        # Windows server workaround
        if 'server' in version_string.lower():
            version_string = '8.1'
    else:
        distro, version_string, _ = platform.linux_distribution()
        # CentOS Linux -> CentOS
        distro = distro.split()[0]
        # Major and minor version only (ignore build number)

    distro = distro.lower()
    version = tuple(map(int, version_string.split('.')[:version_length]))

    return {'os': distro,
            'version': version,
            'arch': 'x86_64' if '64' in platform.architecture()[0] else 'x86'
        }


def grep(pattern, input):
    """
    Find files matching in input matching the pattern.
    
    :param pattern: Regular expression to match.
    :param input: Scanned input. Can be either string, file-like object
                  or path to file.
    :type pattern: str
    :type input: str or file
    :return: Yields matched lines from input.
    """
    if isinstance(input, basestring) and os.path.isfile(input):
        with open(input, 'r') as f:
            lines = f.readlines()
    elif isinstance(input, file):
        lines = input.readlines()

    for line in lines:
        line.rstrip(os.pathsep)
        if re.search(pattern, line):
            yield line


def is_codasip_cmdline():
    try:
        import codasip
    except ImportError:
        return False
    else:
        return True


def is_iterable(object):
    """Detect if an object is single-valued iterable, but not string.
    
    :param object: Python object
    :type object: object
    :return: ``True`` if ``object`` is single-valued iterable (e.g. not dict) else
        ``False``. 
    
    .. note::
        
        String object are considered as non-iterable in this context although they
        support iteration.
    
    :Examples:
    
    >>> is_iterable([1, 2, 3])
    True
    >>> is_iterable(set([1, 1, 1]))
    True    
    >>> is_iterable("Am I?")
    False
    
    """
    return isinstance(object, (list, tuple, set))


def noext_path2design_path(noext_path):
    parts = noext_path.split('-')
    return '.'.join(parts[:2])


def parse_cmdline_data(data):
    if not data:
        return {}
    if is_iterable(data):
        ','.join(data)

    data = sum(map(lambda x: COMMA_RE.split(x), data), [])
    parsed = {}
    for d in data:

        d_list = d.split('=', 1)
        if len(d_list) != 2:
            warning('Invalid metadata option {}, has to be in format key=value, skipping.', d)
            continue

        key, value = d_list
        # Remove leading dashes from key and convert value to object
        # e.g. --attrib='5'  ->  attrib: 5
        parsed[key.lstrip('-')] = str_to_object(value)

    return parsed


def posix_path(path):
    """Convert windows absolute path to MinGW/POSIX one"""
    if os.name == 'nt':
        match = re.match(r'([\w]):(.+)', path)
        if match and len(match.groups()) == 2:
            path = '/' + match.group(1) + match.group(2)
    return path.replace('\\', '/')


def rmtree(dir, ignore_errors=False, content_only=False, exclude=None):
    """Remove directory tree with safety checks.
    
    :param dir: Root directory to remove. If directory is not empty after removal
        process (e.g. some files matched the exclude regex), the directory
        is not removed.
    :param ignore_errors: If False, then exception is raised when an error occurs,
        otherwise boolean value representing result (True if success) is returned.
    :param content_only: If True, preserve the root directory.
    :param exclude: Regular expression for directories/files which should be preserved.
    :type dir: str
    :type ignore_errors: bool
    :type content_only: bool
    :type exclude: str
    """
    # Test for safe directory
    if dir == '/' or dir == '\\' or re.match(r'^[a-zA-Z]:\\?$', dir):
        error('Trying to remove root directory {}', dir)
        return

    try:
        for root, subdirs, files in os.walk(dir, topdown=False):
            for f in files:
                path = os.path.join(root, f)
                if exclude is not None and re.search(path, exclude):
                    continue
                if not os.path.islink(path):
                    os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                os.remove(path)

            for subdir in subdirs:
                path = os.path.join(root, subdir)
                if exclude is not None and re.search(path, exclude):
                    continue
                if os.path.islink(path):
                    os.remove(path)
                else:
                    os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                    os.rmdir(path)
        if not content_only and not os.listdir(dir):
            os.rmdir(dir)
    except OSError:
        if not ignore_errors:
            raise


def run(args, timeout=None, get_output=False, stdin=None, stdout=None, stderr=None, tool_name=None, **kwargs):
    """
    Runs a subprocess with given arguments and handles std(in|out|err).
    @param args: a list of arguments of the subrocess (args[0] is a binary)
    @param stdin: where to redirect stdin
    @param stdout: where to redirect stdout
    @param stderr: where to redirect stderr
    """
    import threading

    out = err = ''

    inf, outf, errf = None, None, None
    # Handle stdin redirections.
    if stdin is not None:
        inf = open(stdin, 'r')
    # Handle stdout redirections.
    if stdout in [sys.stdout, sys.stderr, None]:
        outf = tempfile.NamedTemporaryFile()
    else:
        outf = open(stdout, 'w+b')
    # Handle stderr redirections.
    if stderr in [sys.stdout, sys.stderr, None]:
        errf = tempfile.NamedTemporaryFile()
    else:
        errf = open(stderr, 'w+b')
    # Run the tool
    kw = dict()
    kw['stdout'] = outf
    kw['stderr'] = errf
    kw['stdin'] = inf
    if os.name == 'nt':
        kw['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    # copy only some allowed arguments, kwargs may contain lot of unsupported items
    kw['env'] = kwargs.get('env', None)
    kw['cwd'] = kwargs.get('cwd', None)
    # support for command_builder
    if hasattr(args, 'args'):
        args = args.args
    p = subprocess.Popen(args, **kw)
    # Prepare a timeout
    t = None
    if timeout and timeout > 0:

        # Specify a timeout handler
        def timeout_handler(p):
            p.timeout = True
            try:
                import signal
                sig_name = signal.CTRL_C_EVENT if os.name == 'nt' else signal.SIGINT
                p.send_signal(sig_name)
            except:
                p.terminate()

        # Create the timer
        t = threading.Timer(timeout, timeout_handler, (p,))
        # Start the timer
        t.daemon = True
        t.start()
    # Wait for the tool to finish
    ec = p.wait()
    timed_out = False
    if timeout:
        if getattr(p, 'timeout', False):
            ec = ProcessError.TIMEOUT
            timed_out = timeout
        else:
            t.cancel()
            t.join()

    # Close stdin redirection.
    if inf is not None:
        inf.close()
    # Close stdout redirection.
    if outf:
        outf.seek(0)
        out = outf.read()
        outf.close()
    # Close stderr redirection.
    if errf:
        errf.seek(0)
        err = errf.read()
        errf.close()
    # Raise an error if on non-zero tool exit
    if ec != 0:
        msg = "Process has failed with exit code {0}".format(ec)
        raise ProcessError(msg, ec, args, out, err, tool_name, timeout=timed_out)
    if get_output:
        return out
    return ec, out, err

'''     
def run(args, timeout=None, get_output=False, supress_stdout=True, supress_stderr=True, 
        stdin=None, **kwargs):
    """Runs a subprocess with given arguments and handles std(in|out|err).
    
    :param args: a list of arguments of the subrocess (args[0] is a binary).
    :param timeout: Time (in seconds) after which the process is killed.
    :param get_output: If ``True`` then only captured stdout is returned, else
                       return tuple (exit_code, stdout, stderr).
    :param supress_stdout: If `True`, then process' stdout is not printed to console,
        but is still captured.
    :param supress_stderr: If `True`, then process' stderr is not printed to console,
        but is still captured.
    :param stdin: 
    :param kwargs: Additional arguments for subprocess.Popen.
    :type args: list
    :type timeout: int
    :type get_output: bool
    :type flush: bool
    :return: Tuple (exit_code, stdout, stderr) or stdout only if get_output is ``True``.
    :raises `~mastermind.lib.exceptions.ProcessError`: If process fails.
    
    .. note::
    
        Process stdout and stderr cannot be overriden. They are always set to :py:data:`subprocess.PIPE`
        as only this settings allow process stdout and stderr capturing and printing simultaneously.
    """
    import threading
    
    def set_timeout(p):
        timer = None
        if timeout:
            # Specify a timeout handler
            def timeout_handler(p):
                p.timeout = True
                try:
                    import signal
                    sig_name = signal.CTRL_C_EVENT if os.name == 'nt' else signal.SIGINT
                    p.send_signal(sig_name)
                except:
                    p.terminate()
            # Create the timer
            timer = threading.Timer(timeout, timeout_handler, (p,))
            p.timer = timer
            # Start the timer
            timer.daemon = True
            timer.start()
    
    def check_timeout(p):
        if not timeout:
            return
        if getattr(p, 'timeout', False):
            p.exit_code = ProcessError.TIMEOUT
        else:
            p.timer.cancel()
            p.timer.join()
    
    if os.name == 'nt':
        from subprocess import CREATE_NEW_PROCESS_GROUP
        kwargs.setdefault('creationflags', CREATE_NEW_PROCESS_GROUP)
    # support for command_builder
    if hasattr(args, 'args'):
        args = args.args
    
    kwargs.pop('stdout', None)
    kwargs.pop('stderr', None)
    
    with OutputDuplicator(supress_stdout, supress_stderr) as duplicator:
        p = Popen(args, stdin=stdin, stdout=PIPE, stderr=PIPE, **kwargs)
        # Prepare a timeout
        set_timeout(p)
        while True:
            ec = p.poll()
            out = p.stdout.readline()
            err = p.stderr.readline()
            
            if out:
                sys.stdout.write(out)
            if err:
                sys.stderr.write(err)
            
            if not out and not err:
                if ec is None:
                    continue
                else:
                    break

        check_timeout(p)
    
    out = duplicator.out.getvalue()
    err = duplicator.err.getvalue()

    # Raise an error if on non-zero tool exit
    if ec != 0:
        msg = "Process has failed with exit code {0}".format(ec)
        raise ProcessError(msg, ec, args, out, err)
    if get_output:
        return out
    return ec, out, err
'''


def setup_cmakes(tools_dir):
    """Configure cmake files to current run.
    
    Find and configure .cmake file located in tools/cmake, so
    Mastermind is able to use licensed 3rd party tools such as
    Questasim, Riviera etc. These tools are installed on
    Codasip NFS.
    """
    from codasip import RtlSimulationTool

    info("Configuring cmake files for licensed 3rd party tools")
    for simulator in RtlSimulationTool:
        cmake_file = os.path.join(tools_dir, 'cmake', simulator + '.cmake')
        simulator_info = get_edatool_info(simulator)

        install_dir = simulator_info.get('dir')

        if install_dir:
            info("RTL simulator {0} installation directory: {1}", simulator, install_dir)
            sed('set\(RTL_SIM_DIR\s".*', 'set(RTL_SIM_DIR "{0}")'.format(install_dir), cmake_file)
    info("Cmake files configuration complete")


def sed(pattern, repl, files):
    """Replaces pattern occurences in files.
    
    :param pattern: Regular expression to find string to replace.
    :param repl: String which will replace the matched pattern.
    :param files: A file or list of files, where substitution will be performed.
    :type pattern: str
    :type repl: str
    :type files: str or list
    """
    if not is_iterable(files):
        files = [files]

    for filename in files:
        try:
            with open(filename, 'r') as fp:
                filedata = fp.read()
            filedata = re.sub(pattern, repl, filedata)
            with open(filename, 'w') as fp:
                fp.write(filedata)
        except:
            error("Could not replace data in file {}\n", filename)


def str_to_object(value):
    """Convert string representation of Python built-in value to Python object."""

    if value.lower() == 'none':
        return None
    if value.lower() == 'false':
        return False
    if value.lower() == 'true':
        return True
    if value.isdigit():
        return int(value)
    if len(value) >= 2 and value[0] == "[" and value[-1] == "]":
        return [str_to_object(o) for o in COMMA_RE.split(value[1:-1])]
    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (
        (value[0] == "'" and value[-1] == "'"))):
        return value[1:-1]

    return value


def to_list(item):
    """
    Convert item to a list. If it already is iterable, then no action is performed.

    .. note::

        Uses :py:func:`is_iterable` to detect if item is iterable.
    """
    if item is not None and not is_iterable(item):
        item = [item]
    return item


def walklevel(dir, depth=1, **kwargs):
    """Traverse directory with limited depth.

    :param dir: Directory to traverse.
    :param depth: Depth of recursive search. Defaults to 1 (:py:func:`os.listdir` behaviour).
    :param kwargs: Additional arguments for :py:func:`os.walk`.
    """
    dir = dir.rstrip(os.path.sep)
    num_sep = dir.count(os.path.sep)
    for root, subdirs, files in os.walk(dir, **kwargs):
        yield root, subdirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + depth <= num_sep_this:
            del subdirs[:]


##########################################################################################
##########################################################################################
##########################################################################################
#                    Codasip Testsuite utilities reimplementations
##########################################################################################
##########################################################################################
##########################################################################################
def string_to_path(value):
    """
    Normalizes string and converts non-alpha characters and spaces to hyphens.

    :param value: value by which should be string normalized
    :type value: str
    """
    return re.sub('[^\w\s\.()]+', '-', value).strip(' \t\r\n-')


DEFAULT_EXCLUDE = ['\.py.?$', '__pycache__']


def filter_method(root, dirs, files, dirbased):
    """
    Filter by which is root directory joined to file. When recursive present
    list of lists of files is created. Done by :py:func:`os.walk` function call.

    :param root: Root directory name.
    :type root: str
    :param dirs: Directories which can be present when recursive filter is done.
    :param files: Files which are joined with root.
    :param dirbased: When present list in list join is done.
    :return: joined list of files.
    :rtype: list(file, file, ... )
    """
    if dirbased:
        if dirs or not files:
            return []
        else:
            return [[os.path.join(root, file) for file in files]]
    return [os.path.join(root, file) for file in files]


def files(path, pattern, exclude=DEFAULT_EXCLUDE, dirbased=False):
    """
    Detect all files in given path that matches any of the pattern.
    Automatically exclude files and directories that matches
    any of the exclude filters. Call :py:func:`filter_method`.

    :param path: Path which should be traversed.
    :type path: str
    :param pattern: Pattern by which should be traversed.
    :type pattern: str or regular expression(r"")
    :param exclude: Files which should be excluded when traversing.
    :type exclude: str or regular expression(r"")
    :param dirbased: When ``True``, another filter method is called.
    :type dirbased: bool
    """
    path = os.path.abspath(path)
    if not isinstance(pattern, (list, tuple)):
        pattern = [pattern]
    if not isinstance(exclude, (list, tuple)):
        exclude = [exclude]
    # precompile infront to for performance
    pattern = [re.compile(p) for p in pattern]
    exclude = [re.compile(p) for p in exclude]

    out = []
    for root, dirs, found_files in os.walk(path, topdown=True):
        # exclusions
        for p in exclude:
            found_files = [f for f in found_files if not p.search(f)]
            dirs = [d for d in found_files if not p.search(d)]
        for p in pattern:
            found_files = [f for f in found_files if p.search(f)]
            dirs = [d for d in found_files if not p.search(d)]
        out.extend(filter_method(root, dirs, found_files, dirbased))
    return out


def commonprefix(l):
    """Fixed version of os.path.commonprefix, that is broken in Python2 - returns string prefix, not
    path one.
    Adopted from http://stackoverflow.com/questions/21498939
    """
    l = [os.path.normpath(p) for p in l]

    cp = []
    ls = [p.split(os.path.sep) for p in l]
    ml = min(len(p) for p in ls)

    for i in range(ml):

        s = set(p[i] for p in ls)
        if len(s) != 1:
            break

        cp.append(s.pop())

    return os.path.sep.join(cp)


def progress(count, total, status=''):
    """Progress bar function with line rewriting. The code is under MIT licence and available from
    https://gist.github.com/vladignatyev/06860ec2040cb497f0f3.

    :param count: Current state.
    :param total: Maximum value.
    :param status: Text description of current state.
    """
    if count > total:
        count = total

    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)

    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    if count < total:
        sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    else:
        sys.stdout.write('[%s] %s%s ...%s\n' % (bar, percents, '%', status))
    sys.stdout.flush()


def find_cmdline(searched_paths):
    """Performs search for Codasip Commandline.

    Search is performed in paths passed in ``searched_paths``.
    Common directory structure of compressed archive with tools
    `package/tools/bin/cmdline`.

    When Codasip Commandline is not found in common directory
    structure, then Jenkins build artifact is searched in
    process working directory.

    :param searched_paths: List of path, which will be traversed.
    :type searched_paths: list
    :return: Path to executable if found, else ``None``.
    :rtype: str or None
    """
    extension = '.exe' if os.name == 'nt' else ''
    common_dirs = ['package', 'tools', 'bin', 'cmdline' + extension]

    def search_path(path):
        # search in order path/cmdline -> path/bin/cmdline -> path/tools/bin/cmdline ->...
        for i in range(len(common_dirs) - 1, -1, -1):
            candidate = os.sep.join([path] + common_dirs[i:])
            if os.path.isfile(candidate):
                return candidate

    cmdline = None
    for spath in searched_paths:
        cmdline = search_path(spath)
        if cmdline:
            break

    # Scan cwd for archive with tools. If more such archives exist,
    # use the one with newest tools.
    if cmdline is None:
        info("Codasip Commandline executable not found, trying to find Jenkins artifact\n")
        archive = None
        cwd = os.getcwd()
        # Sort files, so we find latest version as first
        for item in sorted(os.listdir(cwd))[::-1]:
            m = re.search('^codasip-(framework|tools).*\.tar\.gz$', item)
            if m:
                archive = m.group(0)
                break
        if archive:
            info("Found artifact {0}, extracting\n".format(archive))
            extract(archive, cwd)
            cmdline_path = search_path(cwd)
            if cmdline_path and os.path.isfile(cmdline_path):
                cmdline = cmdline_path
        else:
            warning("Jenkins artifact not found\n")

    return cmdline


def run_in_cmdline(cmd, **kwargs):
    """Execute command with Codasip Commandline.

    When running from system Python, then Codasip Commandline
    is searched using :func:`find_setup_cmdline` in process
    working directory.

    Search is performed in paths passed in ``seached_paths``.
    Common directory structure of compressed archive with tools is
    `package/tools/bin/cmdline`.

    When Codasip Commandline is not found in common directory
    structure, then Jenkins build artifact is searched in
    process working directory and Mastermind parent
    directory, in that order.

    :param cmd: Command to execute with Codasip Commandline.
    :param kwargs: Keyword arguments for :py:func:`~subprocess.check_call`.
    :type cmd: list
    :return: Mastermind exit code.
    :rtype: int
    :raises `~exceptions.RuntimeError`: If running from system Python and
        Codasip Commandline has not been found.
    """
    from subprocess import check_call, CalledProcessError
    ENVIRONMENT = {'LMX_LICENSE_PATH': 'codasip3%6200'}

    try:
        import codasip
    except ImportError:
        info("Running from python, trying to find Codasip Commandline\n")

        cmdline_search_paths = [os.getcwd()]
        mastermind_parent_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if mastermind_parent_folder != os.getcwd():
            cmdline_search_paths.append(mastermind_parent_folder)

        cmdline = find_cmdline(cmdline_search_paths)
        if cmdline is None:
            msg = "Command '{0}' must be ran from Codasip Commandline".format(cmd)
            raise RuntimeError(msg)
    else:
        cmdline = sys.executable

    cmd.insert(0, cmdline)

    # Set Codasip Commandline environment
    env = os.environ.copy()
    env.update(ENVIRONMENT)
    if 'env' in kwargs:
        env.update(kwargs['env'])
        del kwargs['env']
    try:
        info("Mastermind command: {0}\n".format(cmd))
        ret = check_call(cmd, env=env, **kwargs)
    except (CalledProcessError, OSError) as exc:
        ret = exc.returncode

    return ret
