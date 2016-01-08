from __future__ import absolute_import, unicode_literals, print_function, division

"""This module collates the Git commands from the submodule

...it's a python 2 / 3 compatibility workaround, mostly.
"""

try:
    # Python 3
    from .git.core import *

    from .git.add import *
    from .git.annotate import *
    from .git.commit import *
    from .git.diff import *
    from .git.flow import *
    from .git.history import *
    from .git.repo import *
    from .git.stash import *
    from .git.status import *
    from .git.statusbar import *
except (ImportError, ValueError):
    # Python 2
    from git.core import *

    from git.add import *
    from git.annotate import *
    from git.commit import *
    from git.diff import *
    from git.flow import *
    from git.history import *
    from git.repo import *
    from git.stash import *
    from git.status import *
    from git.statusbar import *
