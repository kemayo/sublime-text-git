from __future__ import absolute_import, unicode_literals, print_function, division

import os
import re

import sublime
from . import GitTextCommand, GitWindowCommand, git_root
from .status import GitStatusCommand
from collections import namedtuple
from .diff import get_GitDiffRootInView


class GitAddChoiceCommand(GitStatusCommand):
    def status_filter(self, item):
        return super(GitAddChoiceCommand, self).status_filter(item) and not item[1].isspace()

    def show_status_list(self):
        self.results = [
            [" + All Files", "apart from untracked files"],
            [" + All Files", "including untracked files"],
        ] + [[a, ''] for a in self.results]
        return super(GitAddChoiceCommand, self).show_status_list()

    def panel_followup(self, picked_status, picked_file, picked_index):
        working_dir = git_root(self.get_working_dir())

        if picked_index == 0:
            command = ['git', 'add', '--update']
        elif picked_index == 1:
            command = ['git', 'add', '--all']
        else:
            command = ['git']
            picked_file = picked_file.strip('"')
            if os.path.exists(working_dir + "/" + picked_file):
                command += ['add']
            else:
                command += ['rm']
            command += ['--', picked_file]

        self.run_command(
            command, self.rerun,
            working_dir=working_dir
        )

    def rerun(self, result):
        self.run()


class GitAddSelectedHunkCommand(GitTextCommand):
    def is_gitDiffView(self, view):
        return view.name() == "Git Diff" and get_GitDiffRootInView(view) is not None

    def is_enabled(self):

        view = self.active_view()
        if self.is_gitDiffView(view):
            return True

        # First, is this actually a file on the file system?
        return super().is_enabled()

    def run(self, edit, edit_patch=False):
        if self.is_gitDiffView(self.view):
            kwargs = {}
            kwargs['working_dir'] = get_GitDiffRootInView(self.view)
            full_diff = self.view.substr(sublime.Region(0, self.view.size()))
            self.cull_diff(full_diff, edit_patch=edit_patch, direct_select=True, **kwargs)
        else:
            self.run_command(['git', 'diff', '--no-color', '-U1', self.get_file_name()], lambda result: self.cull_diff(result, edit_patch))

    def cull_diff(self, result, edit_patch=False, direct_select=False, **kwargs):
        selection = []
        for sel in self.view.sel():
            selection.append({
                "start": self.view.rowcol(sel.begin())[0] + 1,
                "end": self.view.rowcol(sel.end())[0] + 1,
            })

        # We devide the diff output into hunk groups. A file header starts a new group.
        # Each group can contain zero or more hunks.
        HunkGroup = namedtuple("HunkGroup", ["fileHeader", "hunkList"])
        section = []
        hunks = [HunkGroup(section, [])]  # Initial lines before hunks
        matcher = re.compile('^@@ -([0-9]*)(?:,([0-9]*))? \+([0-9]*)(?:,([0-9]*))? @@')
        for line_num, line in enumerate(result.splitlines(keepends=True)):  # if different line endings, patch will not apply
            if line.startswith('diff'):  # new file
                section = []
                hunks.append(HunkGroup(section, []))
            elif line.startswith('@@'):  # new hunk
                match = matcher.match(line)
                start = int(match.group(3))
                end = match.group(4)
                if end:
                    end = start + int(end)
                else:
                    end = start
                section = []
                hunks[-1].hunkList.append({"diff": section, "start": start, "end": end, "diff_start": line_num + 1, "diff_end": line_num + 1})
            elif hunks[-1].hunkList:  # new line for file header or hunk
                hunks[-1].hunkList[-1]["diff_end"] = line_num + 1  # update hunk end

            section.append(line)

        diffs = "".join(hunks[0][0])
        hunks.pop(0)
        selection_is_hunky = False
        for file_header, hunkL in hunks:
            file_header = "".join(file_header)
            file_header_added = False
            for hunk in hunkL:
                for sel in selection:
                    # In direct mode the selected view lines correspond directly to the lines of the diff file
                    # In indirect mode the selected view lines correspond to the lines in the "@@" hunk header
                    if direct_select:
                        hunk_start = hunk["diff_start"]
                        hunk_end = hunk["diff_end"]
                    else:
                        hunk_start = hunk["start"]
                        hunk_end = hunk["end"]
                    if sel["end"] < hunk_start:
                        continue
                    if sel["start"] > hunk_end:
                        continue
                    # Only print the file header once
                    if not file_header_added:
                        file_header_added = True
                        diffs += file_header
                    hunk_str = "".join(hunk["diff"])
                    diffs += hunk_str  # + "\n\nEND OF HUNK\n\n"
                    selection_is_hunky = True

        if selection_is_hunky:
            if edit_patch:  # open an input panel to modify the patch
                patch_view = self.get_window().show_input_panel(
                    "Message", diffs,
                    lambda edited_patch: self.on_input(edited_patch, **kwargs), None, None
                )
                s = sublime.load_settings("Git.sublime-settings")
                syntax = s.get("diff_syntax", "Packages/Diff/Diff.tmLanguage")
                patch_view.set_syntax_file(syntax)
                patch_view.settings().set('word_wrap', False)
            else:
                self.on_input(diffs, **kwargs)
        else:
            sublime.status_message("No selected hunk")

    def on_input(self, patch, **kwargs):
        self.run_command(['git', 'apply', '--cached'], stdin=patch, **kwargs)

# Also, sometimes we want to undo adds


class GitResetHead(object):
    def run(self, edit=None):
        self.run_command(['git', 'reset', 'HEAD', self.get_file_name()])

    def generic_done(self, result):
        pass


class GitResetHeadCommand(GitResetHead, GitTextCommand):
    pass


class GitResetHeadAllCommand(GitResetHead, GitWindowCommand):
    pass


class GitResetHardHeadCommand(GitWindowCommand):
    may_change_files = True

    def run(self):
        if sublime.ok_cancel_dialog("Warning: this will reset your index and revert all files, throwing away all your uncommitted changes with no way to recover. Consider stashing your changes instead if you'd like to set them aside safely.", "Continue"):
            self.run_command(['git', 'reset', '--hard', 'HEAD'])
