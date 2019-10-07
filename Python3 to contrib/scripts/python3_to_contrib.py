# Codasip Ltd
#
# CONFIDENTIAL
#
# Copyright 2019 Codasip Ltd
#
# All Rights Reserved.
#
# NOTICE: All information contained in this file, is and shall remain
# the property of Codasip Ltd and its suppliers, if any.
#
# The intellectual and technical concepts contained herein are
# confidential and proprietary to Codasip Ltd and are protected by
# trade secret and copyright law.  In addition, elements of the
# technical concepts may be patent pending.
#
# Author: Richard Klem
# Date: 22.8.2019
# Description: This SCRIPT is adding python3 into user contrib
# (location has to be specified) in purpose of use of a supertest.

import os
import sys
from shutil import copy
from lib.utils import extract, info, warning, error, is_codasip_cmdline

PY26 = (2, 6,) <= sys.version_info <= (3,)
python3_location = ""


def copy_python_to_contrib(src, dst):
    copy(src, dst, follow_symlinks=True)


def main(args):

    if len(args) != 1:
        error("You must specify where is your contrib folder.")
        return -1
    elif not PY26:
        py_version_string = '.'.join(map(str, sys.version_info[:3]))
        error("Script does not support Python {0}. Python 2.6.x or Python 2.7.x is required.",
              py_version_string)
        return -1
    else:
        copy_python_to_contrib(python3location, args)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
