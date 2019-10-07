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
# Desc: Mastermind exceptions
#

import os

class FixtureManagerException(Exception):
    """
    An exception class to throw when :py:class:`~mastermind.lib.internal.FixtureManager`
    encounters an error.
    """
    pass

class MarkerArgumentException(Exception):
    """
    General exception class to throw when marker arguments are errorous.

    :ivar marker: Option marker which had caused an error.
    :ivar metafunc: Pytest metafunc object.
    :ivar message: Message to show.
    :ivar _args: Arguments for ``message`` formatting.
    :ivar _kwargs: Keyword arguments for ``message`` formatting.
    :vartype marker: :py:class:`~mastermind.internal.MarkerGroup`
    :vartype message: str
    :vartype _args: tuple
    :vartype _kwargs: dict
    """
    def __init__(self, marker, metafunc, message='', *args, **kwargs):
        super(MarkerArgumentException, self).__init__(message)
        self.marker = marker
        self.metafunc = metafunc
        self.message = message

        self._args = args
        self._kwargs = kwargs

    def __str__(self):
        mark = self.marker
        name = (self.metafunc.function.__name__ +
                ((' in class {}'.format(self.metafunc.cls.__name__)) if self.metafunc.cls else ''))

        msg = (self.message.format(*self._args, **self._kwargs)
               if self.message else 'Marker argument exception\n')

        msg_vals = (name, mark.marker_name, msg)
        return "Function {}: Invalid arguments for marker '{}'. {}".format(*msg_vals)


class MarkerOptionTypeError(Exception):
    """
    An exception class to throw when marker option type is invalid.

    :ivar marker: Option marker which had caused an error.
    :ivar metafunc: Pytest metafunc object.
    :ivar message: Message to show.
    :ivar _args: Arguments for ``message`` formatting.
    :ivar _kwargs: Keyword arguments for ``message`` formatting.
    :vartype marker: :py:class:`~mastermind.internal.MarkerOption`
    :vartype message: str
    :vartype _args: tuple
    :vartype _kwargs: dict
    """
    def __init__(self, marker, metafunc, message='', *args, **kwargs):
        super(MarkerOptionTypeError, self).__init__(message)
        self.marker = marker
        self.metafunc = metafunc
        self.message = message

        self._args = args
        self._kwargs = kwargs

    def __str__(self):
        mark = self.marker
        name = (self.metafunc.function.__name__ +
                ((' in class {}'.format(self.metafunc.cls.__name__))
                 if self.metafunc.cls else ''))


        msg = (self.message.format(*self._args, **self._kwargs)
               if self.message else 'MarkerOption type mismatch')
        expected = ', '.join([t.__name__ for t in mark.types])

        msg_vals = (name, mark.option_name, mark.static_name, mark.marker_name,
                    expected, type(mark.value).__name__)

        if not msg.endswith('\n'):
            msg += '\n'

        msg += "Function {}: Invalid type for option '{}' or {} for marker '{}'. " \
               "Expected {}, got type '{}'".format(*msg_vals)

        return msg

class ProcessError(Exception):
    """
    An exception class to throw when process encounters an error.

    :ivar exit_code: Exit code of the process.
    :ivar args: Arguments of the process.
    :ivar stdout: Stdout of the process.
    :ivar stderr: Stderr of the process.
    :vartype exit_code: int
    :vartype args: list
    :vartype stdout: str
    :vartype stderr: str
    """
    TIMEOUT = -1

    def __init__(self, message, exit_code=None, args=None, stdout='', stderr='',
                 name=None, timeout=None):
        super(ProcessError, self).__init__(message)
        # cannot use args directly, it is used in Exception base class
        self.process_args = args
        self.exit_code = exit_code
        self.stdout = unicode(stdout, 'utf-8')
        self.stderr = unicode(stderr, 'utf-8')
        self.timeout = timeout
        self.name = None
        if name is not None:
            self.name = name
        elif args:
            self.name = os.path.basename(args[0])

    def __str__(self):
        if self.message:
            msg = self.message
        else:
            msg = "Tool or process has failed"

        if self.name:
            msg += '\nName: {}'.format(self.name)
        if self.process_args:
            msg += "\nArguments: {}".format(self.process_args)

        msg += "\nExit code: {}".format(self.exit_code)

        if self.timeout:
            if isinstance(self.timeout, bool):
                msg += " (Timed out)"
            else:
                msg += " (Timed out after %d seconds)"%(self.timeout)

        return msg

class ToolBuildError(Exception):
    """
    An exception class to throw when Codasip Build system encounters an error.

    :ivar project: :py:class:`~codasip.CodalProject` instance.
    :ivar command: Failed build command.
    :ivar stdout: Stdout of the process.
    :ivar stderr: Stderr of the process.
    :vartype project: :py:class:`~codasip.CodalProject`
    :vartype command: list
    :vartype stdout: str
    :vartype stderr: str
    """
    def __init__(self, message=None, project=None, args=None, stdout='', stderr=''):
        self.message = message
        self.project = project
        # Convert to string
        self.command = ' '.join(args) if isinstance(args, (list, tuple)) else str(args)
        self.stdout = unicode(stdout, 'utf-8')
        self.stderr = unicode(stderr, 'utf-8')

    def __str__(self):
        if self.message:
            msg = self.message
        else:
            msg = "Build failed"

        if self.command:
            msg += '\nBuild command: ' + self.command
        if self.project:
            msg += '\nProject: ' + self.project.name

        msg += '\n'
        return msg
