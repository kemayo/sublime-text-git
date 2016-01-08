from __future__ import absolute_import, unicode_literals, print_function, division

import os
import sublime
import sublime_plugin

from . import GitWindowCommand, GitTextCommand


class GitCustomCommand(GitWindowCommand):
    may_change_files = True

    def run(self):
        self.get_window().show_input_panel("Git command", "",
            self.on_input, None, None)

    def on_input(self, command):
        command = str(command)  # avoiding unicode
        if command.strip() == "":
            self.panel("No git command provided")
            return
        import shlex
        command_splitted = ['git'] + shlex.split(command)
        print(command_splitted)
        self.run_command(command_splitted)


class GitRawCommand(GitWindowCommand):
    may_change_files = True

    def run(self, **args):
        self.command = str(args.get('command', ''))
        show_in = str(args.get('show_in', 'pane_below'))

        if self.command.strip() == "":
            self.panel("No git command provided")
            return
        import shlex
        command_split = shlex.split(self.command)

        if args.get('append_current_file', False) and self._active_file_name():
            command_split.extend(('--', self._active_file_name()))

        print(command_split)

        self.may_change_files = bool(args.get('may_change_files', True))

        if show_in == 'pane_below':
            self.run_command(command_split)
        elif show_in == 'quick_panel':
            self.run_command(command_split, self.show_in_quick_panel)
        elif show_in == 'new_tab':
            self.run_command(command_split, self.show_in_new_tab)
        elif show_in == 'suppress':
            self.run_command(command_split, self.do_nothing)

        view = self.active_view()
        view.run_command('git_branch_status')

    def show_in_quick_panel(self, result):
        self.results = list(result.rstrip().split('\n'))
        if len(self.results):
            self.quick_panel(self.results,
                self.do_nothing, sublime.MONOSPACE_FONT)
        else:
            sublime.status_message("Nothing to show")

    def do_nothing(self, picked):
        return

    def show_in_new_tab(self, result):
        msg = self.window.new_file()
        msg.set_scratch(True)
        msg.set_name(self.command)
        self._output_to_view(msg, result)
        msg.sel().clear()
        msg.sel().add(sublime.Region(0, 0))


class GitGuiCommand(GitTextCommand):
    def run(self, edit):
        command = ['git', 'gui']
        self.run_command(command)


class GitGitkCommand(GitTextCommand):
    def run(self, edit):
        command = ['gitk']
        self.run_command(command)


class GitUpdateIgnoreCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        data = self.view.window().project_data()
        project_file_name = self.view.window().project_file_name()
        for folder in data['folders']:
            path = folder['path']
            if project_file_name:
                path = os.path.join(os.path.dirname(project_file_name), path)
            gitignore = os.path.join(path, ".gitignore")
            print("gitignore path", gitignore)
            if (os.path.exists(gitignore)):
                with open(gitignore) as gitignore_file:
                    if "folder_exclude_patterns" not in folder:
                        folder["folder_exclude_patterns"] = []
                    if "file_exclude_patterns" not in folder:
                        folder["file_exclude_patterns"] = []
                    for pattern in gitignore_file:
                        pattern = pattern.strip()
                        if len(pattern) == 0 or pattern[0] == '#':
                            continue
                        elif os.path.isdir(os.path.join(path, pattern)):
                            if pattern not in folder["folder_exclude_patterns"]:
                                folder["folder_exclude_patterns"].append(pattern)
                        else:
                            if pattern not in folder["file_exclude_patterns"]:
                                folder["file_exclude_patterns"].append(pattern)
        self.view.window().set_project_data(data)


# called by GitWindowCommand
class GitScratchOutputCommand(sublime_plugin.TextCommand):
    def run(self, edit, output='', output_file=None, clear=False):
        if clear:
            region = sublime.Region(0, self.view.size())
            self.view.erase(edit, region)
        self.view.insert(edit, 0, output)
