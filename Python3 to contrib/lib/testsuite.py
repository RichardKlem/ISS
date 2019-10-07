import copy
from datetime import datetime
import getpass
import os
import platform

from subprocess import check_call, CalledProcessError
import sys
import time
import traceback

from mastermind.lib import ROOT_REPOSITORY
from mastermind.lib.helpers import ArgumentParser
from mastermind.lib.internal import load_ip_package, get_project_configurations
from mastermind.lib.utils import (default_environment, get_system_info, info, Repository,
                                  error, setup_cmakes, is_codasip_cmdline, warning)
from mastermind.database.model import Environment, MastermindSession, Status
from mastermind.database.driver import Driver
from mastermind.plugins.plugin_reporter import Reporter

from mastermind.lib.statuses import generate_statuses

class ExitCodes():
    """Enum class for exit codes
    """
    # Pytest codes
    EXIT_OK = 0
    EXIT_TESTSFAILED = 1
    EXIT_INTERRUPTED = 2
    EXIT_INTERNALERROR = 3
    EXIT_USAGEERROR = 4
    EXIT_NOTESTSCOLLECTED = 5

def session_wrapper(func):
    def func_wrapper(*args):
        
        # args[0] is Testsuite instance
        # args[1] are real arguments
        _args = args[1] if args[1] is not None else sys.argv[1:]
        parsed, unparsed = args[0]._parse_testsuite_arguments(_args)
        debug = '--debug' in unparsed
        upload_results = '--upload-results' in unparsed
        if upload_results:
            info("Creating Mastermind session")
            job_url = os.getenv('BUILD_URL')
            node_name = os.getenv('NODE_NAME', '-'.join([platform.node(), getpass.getuser()]))
            driver = Driver(parsed.url, debug)
            
            env = get_system_info()
            env['os'] += ' ' + '.'.join(map(str, env['version']))
            del env['version']
            if is_codasip_cmdline():
                from codasip.utility.internal import BuildType
                build_type = BuildType() 
                env['compiler'] = build_type.builder if 'vs' in build_type.builder else 'gcc'
            else:
                env['compiler'] = 'none'
            
            session = MastermindSession()
            #with Driver(db_string, debug) as driver:
            env = driver.query(Environment, **env).first()
            session.created = datetime.now()
            session.command = ' '.join(_args)
            session.node_name = node_name
            session.job_url = job_url
            if env:
                session.environment_id = env.id
            session = driver.insert(session, create_table=True)
            session_id = session.id
            # Bind source and session
            repo = Repository.from_dir(ROOT_REPOSITORY)
            driver.insert_source(repo, session)

            _args.extend(['--session-id', str(session.id)])
            # Close connection
            driver.disconnect()
        
        start = time.time()
        try:
            rc = func(*args)
        except:
            # Any exception means serious internal error.
            rc = ExitCodes.EXIT_INTERNALERROR
        finally:
            if rc != ExitCodes.EXIT_OK:
                tb = traceback.format_exc()
                if tb:
                    print tb
        end = time.time()
        passed = (rc == ExitCodes.EXIT_OK)

        if upload_results:
            info("Updating Mastermind session, ID={}", session_id)
            driver = Driver(parsed.url, debug)
            session = driver.query(MastermindSession, id=session_id).first()
            if session:
                session.duration = int(end - start)
                session.exit_code = rc
                session.passed = passed
                session.status_id = rc + 1
                driver.commit()
                driver.disconnect()
            else:
                error("Unable to update session. No record with ID={} has been found", session_id)

        return rc
    return func_wrapper


class Testsuite():
    """Main Mastermind class which executes pytest process."""
    
    MODELS_DIR = 'models'
    """Directory, where model (or model branches) will be cloned."""
    MODELS_DEFAULT_BRANCH = 'master'
    """Default model branch, when no were specified."""
    IP_PACKAGE_DIR = 'ip_package'
    """Directory, where an IP package will be extracted if passed as archive."""
    REPORT_DIR = 'reports'
    """Directory, where reports will be created."""
    WORK_DEFAULT = 'mastermind_work'
    """Base work dir for the whole testsuite"""
    
    def __init__(self, test_dirs=None, work_dir=None, cores='auto'):
        """Constructor
        
        :ivar dirs: List of directories containing test sources.
        :ivar work_dir: Testsuite working directory.
        :ivar cores: Number of cores for testing. When 'auto' is passed, \
            cores are detected automatically.
        :ivar repositories: List of checkouted :py:class:`~mastermind.lib.helpers.Repository`
            objects. If ``None`` is included in the list, then no repository is available.
        :ivar plugins: List of plugins to use.
        :ivar args: Default arguments for pytest.
        :vartype dirs: list or None
        :vartype work_dir: str
        :vartype cores: int or str
        :vartype repositories: list
        :vartype plugins: list
        :vartype args: list
         
        """
        self.dirs = test_dirs
        self.work_dir = work_dir
        self.cores = cores
        self.repositories = [None]
        
        self.args = [
            sys.executable,
            '-m', 'pytest',
            '--tb=short', # Short tracebacks
            '-v', '-s'
        ]

        self.plugins = [
            'mastermind.plugins.plugin_base',
            'mastermind.plugins.plugin_reporter',
        ]
        
        if is_codasip_cmdline():
            self.plugins += ['mastermind.plugins.plugin_sdk',
                             'mastermind.plugins.plugin_hdk',
                             'mastermind.plugins.plugin_project',
                             'mastermind.plugins.plugin_tools',
                             ]
            self.args += ['--self-contained-html']
        
        for plugin in self.plugins:
            self.args += ['-p', plugin]
    
    def _generate_documentation(self):
        doc_dir = os.path.join(ROOT_REPOSITORY, 'docs')
        info("Generating Mastermind Documentation")
        try:
            check_call(['make', 'html'], cwd=doc_dir)
        except CalledProcessError as exc:
            return exc.returncode
        
        return ExitCodes.EXIT_OK
    
    def _parse_testsuite_arguments(self, args):
        parser = ArgumentParser(add_help=False)
        parser.add_argument('--project', action='store', help="""Path to directory with project or a project name"""
                            """ when used with --repository argument.""")
        group_config = parser.add_mutually_exclusive_group()
        group_config.add_argument('--configuration', action='append', help="""Regular expression for project configuration e.g. bk32-IMp."""
                           """ Accepted multiple times""")
        group_config.add_argument('--configuration-file', action='append', help="""Path to configuration file containing options (ip.conf) or"""
                           """ regular expression for matching presets. It is matched with relative paths from <model>/presets directory.""")
        parser.add_argument('--autodetect-top-project', action='store_true', help="Automatically detect top-level project from repository.")
        parser.add_argument('--ignore-internal-errors', action='store_true', help="""When internal error occurs during pytest execution, continue with testing 
                                                                                    of other branches or model configurations.""")
        parser.add_argument('--ip-package', action='store', help="Path to existing IP package. May be either directory containing the package or an archive.")
        parser.add_argument('--repository', action='store', help="URL to project repository, which will be used by Testsuite.")
        parser.add_argument('--branches', action='append', help="""When passed, Testsuite automatically checkouts branches that match"""
                            """ the regular expression specified by this argument.""")
        parser.add_argument('--pull', action='store_true', help="If passed, then all used git repositories with models will be pulled.")
        parser.add_argument('--work-dir', action='store', help="Working directory of testsuite. By default working directory of process/mastermind_work.")
        parser.add_argument('--generate-doc', action='store_true', help="Generate Mastermind documentation.")
        parser.add_argument('--setup-cmakes', action='store_true', help="Set cmake files for 3rd party licenced tools to Codasip NFS.")
        parser.add_argument('--url', action='store', help="Database connection string.")
        # Add help argument manually so ArgumentParser does not exit program
        parser.add_argument('-h', '--help', action='store_true')
        
        args, argv = parser.parse_args(args)
        # Arguments constraints
        # When using autodetect_top project, exactly one from [project, repository] must
        # be specified to avoid ambiguity
        if (args.autodetect_top_project and 
            (bool(args.project) == bool(args.repository))):
                raise AssertionError("Invalid arguments combination.") 
        return args, argv

    def setup_repositories(self, args):
        """Prepare repositories before pytest execution.
        
        Automatically check-out multiple branches of passed git repository.
                
        :param args: Partially parsed arguments from commandline.
        :type args: dict
        
        :return: Tuple of repositories and project name.
        :rtype: tuple
        """
        repository_url = args.repository
        project_path = args.project
        # base_repository represents a Repository object which will
        # be used to checkout multiple branches.
        base_repository = None
        if repository_url:
            base_repository = Repository.from_url(repository_url)
            # Override git repository to testsuite workdir
            base_repository.dir = os.path.join(self.work_dir,
                                               self.MODELS_DIR,
                                               base_repository.repository,
                                               self.MODELS_DEFAULT_BRANCH
                                               )
        elif project_path:
            from mastermind.lib.codasip_utils import find_projects
            dirs = find_projects(project_path)
            assert len(dirs), "No project has been found in {}".format(project_path)

            try:
                # Try to load repository from passed path.
                base_repository = Repository.from_dir(dirs[0])
            except:
                # Not a git repository
                pass

        # Handle git repositories of models
        repositories = []
        if base_repository:
            # Checkout multiple model branches
            branches = args.branches
            pull = args.pull
            if branches:
                namespace, repository = base_repository.namespace, base_repository.repository
                dir = os.path.join(self.work_dir, self.MODELS_DIR, repository)
                # Checkout all branches at once
                repositories.extend(Repository.checkout_branches(
                    namespace, repository, dir, branches, pull))
            # We got url from cmdline
            elif repository_url and not base_repository.is_initialized():
                base_repository.clone()
            # Repository already exists, pull if requested
            elif pull:
                base_repository.synchronize()

        if not repositories:
            repositories = [base_repository]
        
        return repositories

    def build_arguments(self, repository, args):
        """Create command for specific repository/project.
        
        Yields instances of :py:class:`~codasip.command_builder` with additional execution
        arguments. The purpose of this function is to detect available project configurations
        and filter those which do not meet the requirements from cmdline arguments.
        
        :param repository: Repository object containing tested project. May
            be ``None`` if no project or repository has been passed.
        :param args: Parsed arguments.
        :type repository: :py:class:`~mastermind.lib.utils.Repository` or ``None``
        :type args: :py:class:`~argparse.Namespace` 
        :return: Yields specific arguments for pytest execution.
        :rtype: generator
        """
        config_pattern = args.configuration or args.configuration_file
        project_path = repository.dir if args.repository else args.project
        autodetect_top_project = args.autodetect_top_project
        
        project_name = None
        if args.repository:
            project_name = args.project or repository.repository
        if project_path and not is_codasip_cmdline():
            warning("Projects are not supported when Mastermind is not executed from Commandline")
            project_path = None
        
        configurations = None
        if project_path:
            # When autodetection is enabled, discard project_name filter
            # because the project will be found automatically
            if autodetect_top_project:
                project_name = None
            # Find projects in repository. Also apply filter for project name, 
            # because repository may contain multiple projects
            from mastermind.lib.codasip_utils import find_projects
            dirs = find_projects(project_path, name=project_name, top=autodetect_top_project)
            assert dirs, "No available project has been found in {}".format(project_path)
            project_path = dirs[0]
            project_name = os.path.basename(dirs[0])
            if config_pattern:
                info("Detecting available project configurations, this may take a few seconds...")
                configurations = get_project_configurations(dirs[0], config_pattern,
                                                              is_preset=args.configuration_file)
                assert configurations, "No configurations specified by {} found.".format(config_pattern)
                info("Detected {} configurations", len(configurations))
        
        base_cmd = []
        # Build report file name
        report_name = ['report']
        if project_path:
            base_cmd += ['--project', project_path]
            report_name.append(project_name)
        if repository:
            report_name.append(repository.branch)
        
        if not configurations:
            configurations = [None]
        
        first = True
        for config in configurations:
            tmp_cmd = copy.deepcopy(base_cmd)
                        
            if config:
                # config may be relative path to preset -> remove slashes
                _config = os.path.splitext(os.path.basename(config))[0]
                # For the first time there is no 'config' in report name.
                # In each successive iteration we replace it with current 
                # configuration. 
                if first:
                    report_name.append(_config)
                    first = False
                else:
                    report_name[-1] = _config
                
                tmp_cmd += ['--configuration'] if args.configuration else ['--configuration-file']
                tmp_cmd += [config]
            
            xml_report_name = '_'.join(report_name) + '.xml'
            html_report_name = '_'.join(report_name) + '.html'
            tmp_cmd += ['--junitxml=' + os.path.join(self.report_dir, xml_report_name)]
            if is_codasip_cmdline():
                tmp_cmd += ['--html=' + os.path.join(self.report_dir, html_report_name)]
            yield tmp_cmd
    
    def _setup(self, args):
        """Prepare Testsuite for execution.
        
        Parse commandline arguments and load GIT repositories if ``--repository`` and/or
        ``--branches`` arguments have been passed. Also load IP package if any is available
        and defines common testsuite attributes.
        
        :param args: List of arguments from commandline
        :type args: list
        :return: Tuple containing parsed arguments and unparsed arguments.
        """
        args, argv = self._parse_testsuite_arguments(args)
        
        work_dir = args.work_dir
        if work_dir:
            self.work_dir = os.path.abspath(work_dir)
        elif not self.work_dir:
            self.work_dir = os.path.join(os.path.dirname(ROOT_REPOSITORY), self.WORK_DEFAULT)
        
        self.report_dir = os.path.join(self.work_dir, self.REPORT_DIR) 
        if not os.path.isdir(self.report_dir):
            os.makedirs(self.report_dir)

        # Skip repository checkout and loading ip package
        if args.help or args.generate_doc:
            return args, argv
        
        if  is_codasip_cmdline() and args.setup_cmakes:
            from codasip import tools_dir
            setup_cmakes(tools_dir)

        # Checkout multiple branches if needed
        if is_codasip_cmdline():
            self.repositories = self.setup_repositories(args)
        
        # Load IP package if available
        if args.ip_package and is_codasip_cmdline():
            argv += load_ip_package(args.ip_package, os.path.join(self.work_dir,
                                                                  self.IP_PACKAGE_DIR))
        return args, argv

    def _run(self, args, argv):

        if args.help:
            argv += ['--help']
        elif args.generate_doc:
            return self._generate_documentation()

        env = default_environment()
        # Build execution command
        cmd = []
        # General arguments (plugins, tracebacks, ...)
        cmd += self.args
        # Unparsed cmdline arguments
        cmd += argv
        cmd += ['--work-dir=' + self.work_dir]
        if self.dirs:
            cmd += self.dirs
        # Testing multiple branches - clear tool cache automatically
        if len(self.repositories) > 1 and '--purge-cache' not in args:
            cmd += ['--purge-cache']

        # Run tests
        exit_codes = set()
        interrupted = False
        rc = 0
        for i, repository in enumerate(self.repositories, 1):
            if len(self.repositories) > 1:
                info("Starting testing of branch '{}' ({}/{})".format(repository.branch, i, len(self.repositories)))
            
            for tmp_args in self.build_arguments(repository, args):
                tmp_cmd = copy.deepcopy(cmd)
                tmp_cmd += tmp_args
                
                # Execute pytest
                try:
                    info("pytest cmd: {}".format(tmp_cmd))
                    check_call(tmp_cmd, env=env, cwd=ROOT_REPOSITORY)
                except KeyboardInterrupt:
                    interrupted = True
                except CalledProcessError as exc:
                    rc = exc.returncode
                    # User interrupt
                    # When internal error occurs, we still want to proceed the testing, because
                    # the error might be caused by error in model in current branch, but other
                    # branches should still be tested
                    if rc not in [ExitCodes.EXIT_TESTSFAILED] and not args.ignore_internal_errors:
                        interrupted = True
                else:
                    rc = ExitCodes.EXIT_OK
                finally:
                    # Run collection phase just once
                    if '--collect-only' in argv or args.help:
                        return rc
                    exit_codes.add(rc)
                
                if interrupted:
                    break
            if interrupted:
                break
            
        return max(exit_codes)

    @session_wrapper
    def run(self, args=None):
        """Execute pytest main.
        
        :param args: List of additional arguments to cmdline
        :type args: list
        
        :return: Pytest exit code. If more pytests were executed,
            (multiple branches and/or configurations testing was enabled) then 
            return the code with maximum relevancy.
        :rtype: int
        :todo: Support for xdist plugin
        """
        if args is None:
            args = copy.copy(sys.argv[1:])
        #for _, s in generate_statuses().items():
        #    print s
        #return 0
        # Make all paths absolute
        for i, arg in enumerate(args):
            if not arg.startswith('-') and os.path.exists(arg):
                args[i] = os.path.abspath(arg)
        
        # Parse testsuite arguments, setup repositories 
        args, argv = self._setup(args)
        # Execute Mastermind for all available arguments
        exit_code = self._run(args, argv)

        return exit_code
