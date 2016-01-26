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
