import os

import sublime
import functools
from . import GitWindowCommand

class GitMv(GitWindowCommand):
    def run(self, **args):
        filename = self._active_file_name()
        branch, leaf = os.path.split(filename)

        if not os.access(filename, os.W_OK):
            sublime.error_message(leaf + " is read-only")

        inputtext = "New path/name"
        placeholder = filename
        # rename does not change mechanic, only the following with exception of retarget path
        rename = args.get('rename', False)
        if rename:
            inputtext = "Rename to"
            placeholder = leaf

        panel = self.get_window().show_input_panel(inputtext, placeholder,
            functools.partial(self.on_input, rename, branch), None, None)

        name, ext = os.path.splitext(leaf)
        panel.sel().clear()
        panel.sel().add(sublime.Region(0, len(name)))

    def on_input(self, rename, branch, newpath):
        newpath = str(newpath)  # avoiding unicode
        if newpath.strip() == "":
            self.panel("No input received")
            return
        import shlex
        command_splitted = ['git', 'mv', self._active_file_name(), newpath]
        if rename:
            newpath = os.path.realpath(branch + os.sep + newpath)
        print(command_splitted)
        self.run_command(command_splitted, functools.partial(self.on_done, newpath))

    def on_done(self, newpath, gitresponse):
        self.active_view().retarget(newpath)
