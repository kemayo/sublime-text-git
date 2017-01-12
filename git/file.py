import os

import sublime
import functools
from . import GitWindowCommand, git_root


class GitFileMove(GitWindowCommand):
    def run(self, **args):
        filename = self.relative_active_file_path()
        branch, leaf = os.path.split(filename)

        if not os.access(self.active_file_path(), os.W_OK):
            sublime.error_message(leaf + " is read-only")

        panel = self.get_window().show_input_panel(
            "New path / name", filename,
            self.on_input, None, None
        )

        if branch:
            # We want a trailing slash for selection purposes
            branch = branch + os.path.sep

        # Now, select just the base part of the filename
        name, ext = os.path.splitext(leaf)
        panel.sel().clear()
        panel.sel().add(sublime.Region(len(branch), len(branch) + len(name)))

    def on_input(self, newpath):
        newpath = str(newpath)  # avoiding unicode

        if not newpath.strip():
            return self.panel("No input received")

        working_dir = git_root(self.get_working_dir())
        newpath = os.path.join(working_dir, newpath)

        command = ['git', 'mv', '--', self.active_file_path(), newpath]
        self.run_command(command, functools.partial(self.on_done, newpath), working_dir=working_dir)

    def on_done(self, newpath, result):
        if result.strip():
            return self.panel(result)

        self.active_view().retarget(newpath)
