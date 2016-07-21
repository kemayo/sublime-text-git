from __future__ import absolute_import, unicode_literals, print_function, division

import os
import re

import sublime
from . import GitTextCommand, GitWindowCommand, git_root
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

        self.run_command(command, self.rerun,
            working_dir=working_dir)

    def rerun(self, result):
        self.run()

