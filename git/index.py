from __future__ import absolute_import, unicode_literals, print_function, division

import os
import re

import sublime
from . import GitWindowCommand, git_root
from .status import GitStatusCommand


class GitUpdateIndexAssumeUnchangedCommand(GitStatusCommand):
    def status_filter(self, item):
        return super(GitUpdateIndexAssumeUnchangedCommand, self).status_filter(item) and not item[1].isspace()

    def show_status_list(self):
        self.results = [] + [[a, ''] for a in self.results]
        return super(GitUpdateIndexAssumeUnchangedCommand, self).show_status_list()

    def panel_followup(self, picked_status, picked_file, picked_index):
        working_dir = git_root(self.get_working_dir())

        command = ['git']
        picked_file = picked_file.strip('"')
        if os.path.exists(working_dir + "/" + picked_file):
            command += ['update-index', '--assume-unchanged']
        command += ['--', picked_file]

        self.run_command(
            command, self.rerun,
            working_dir=working_dir
        )

    def rerun(self, result):
        self.run()


class GitUpdateIndexNoAssumeUnchangedCommand(GitWindowCommand):
    force_open = False

    def run(self):
        root = git_root(self.get_working_dir())
        self.run_command(['git', 'ls-files', '-v'], self.status_done, working_dir=root)

    def status_done(self, result):
        self.results = list(filter(self.status_filter, result.rstrip().split('\n')))
        if len(self.results):
            self.show_status_list()
        else:
            sublime.status_message("Nothing to show")

    def show_status_list(self):
        self.quick_panel(
            self.results, self.panel_done,
            sublime.MONOSPACE_FONT
        )

    def status_filter(self, item):
        # for this class we don't actually care
        if not re.match(r'^h\s+.*', item):
            return False
        return len(item) > 0

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        root = git_root(self.get_working_dir())
        picked_file = self.results[picked]
        if isinstance(picked_file, (list, tuple)):
            picked_file = picked_file[0]
        # first 1 character is a status code, the second is a space
        picked_file = picked_file[2:]
        self.run_command(
            ['git', 'update-index', '--no-assume-unchanged', picked_file.strip('"')],
            self.rerun, working_dir=root
        )

    def rerun(self, result):
        self.run()
