from __future__ import absolute_import, unicode_literals, print_function, division

import sys

"""This module collates the Git commands from the submodule

...it's a python 2 / 3 compatibility workaround, mostly.
"""

# Sublime doesn't reload submodules. This code is based on 1_reloader.py
# in Package Control, and handles that.

mod_prefix = 'git'

# ST3 loads each package as a module, so it needs an extra prefix
if sys.version_info >= (3,):
    bare_mod_prefix = mod_prefix
    mod_prefix = 'Git.' + mod_prefix
    from imp import reload

# Modules have to be reloaded in dependency order. So list 'em here:
mods_load_order = [
    '',

    '.status',
    '.add',  # imports status
    '.commit',  # imports add

    # no interdependencies below
    '.core',
    '.annotate',
    '.config',
    '.diff',
    '.history',
    '.ignore',
    '.repo',
    '.stash',
    '.statusbar',
    '.flow',
]

reload_mods = [mod for mod in sys.modules if mod[0:3] in ('git', 'Git') and sys.modules[mod] is not None]

reloaded = []
for suffix in mods_load_order:
    mod = mod_prefix + suffix
    if mod in reload_mods:
        reload(sys.modules[mod])
        reloaded.append(mod)

if reloaded:
    print("Git: reloaded submodules", reloaded)

# Now actually import all the commands so they'll be visible to Sublime
try:
    # Python 3
    from .git.core import *  # noqa

    from .git.add import *  # noqa
    from .git.annotate import *  # noqa
    from .git.commit import *  # noqa
    from .git.diff import *  # noqa
    from .git.flow import *  # noqa
    from .git.history import *  # noqa
    from .git.ignore import *  # noqa
    from .git.repo import *  # noqa
    from .git.stash import *  # noqa
    from .git.status import *  # noqa
    from .git.statusbar import *  # noqa
except (ImportError, ValueError):
    # Python 2
    from git.core import *  # noqa

    from git.add import *  # noqa
    from git.annotate import *  # noqa
    from git.commit import *  # noqa
    from git.diff import *  # noqa
    from git.flow import *  # noqa
    from git.history import *  # noqa
    from git.ignore import *  # noqa
    from git.repo import *  # noqa
    from git.stash import *  # noqa
    from git.status import *  # noqa
    from git.statusbar import *  # noqa
