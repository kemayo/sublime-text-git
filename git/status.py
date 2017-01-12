from __future__ import absolute_import, unicode_literals, print_function, division

import os
import re

import sublime
from . import GitWindowCommand, git_root


class GitStatusCommand(GitWindowCommand):
    force_open = False

    def run(self):
        self.run_command(['git', 'status', '--porcelain'], self.status_done)

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
        if not re.match(r'^[ MADRCU?!]{1,2}\s+.*', item):
            return False
        return len(item) > 0

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_file = self.results[picked]
        if isinstance(picked_file, (list, tuple)):
            picked_file = picked_file[0]
        # first 2 characters are status codes, the third is a space
        picked_status = picked_file[:2]
        picked_file = picked_file[3:]
        self.panel_followup(picked_status, picked_file, picked)

    def panel_followup(self, picked_status, picked_file, picked_index):
        # split out solely so I can override it for laughs

        s = sublime.load_settings("Git.sublime-settings")
        root = git_root(self.get_working_dir())
        if picked_status == '??' or s.get('status_opens_file') or self.force_open:
            file_name = os.path.join(root, picked_file)
            if(os.path.isfile(file_name)):
                # Sublime Text 3 has a bug wherein calling open_file from within a panel
                # callback causes the new view to not have focus. Make a deferred call via
                # set_timeout to workaround this issue.
                sublime.set_timeout(lambda: self.window.open_file(file_name), 0)
        else:
            if s.get('diff_tool'):
                self.run_command(
                    ['git', 'difftool', '--', picked_file.strip('"')],
                    working_dir=root
                )
            else:
                self.run_command(
                    ['git', 'diff', '--no-color', '--', picked_file.strip('"')],
                    self.diff_done, working_dir=root
                )

    def diff_done(self, result):
        if not result.strip():
            return
        self.scratch(result, title="Git Diff")


class GitOpenModifiedFilesCommand(GitStatusCommand):
    force_open = True

    def show_status_list(self):
        for line_index in range(0, len(self.results)):
            self.panel_done(line_index)
