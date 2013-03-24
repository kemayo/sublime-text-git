from __future__ import absolute_import, unicode_literals, print_function, division

import functools
import re

import sublime
import sublime_plugin
from . import GitTextCommand, GitWindowCommand, plugin_file


class GitBlameCommand(GitTextCommand):
    def run(self, edit):
        # somewhat custom blame command:
        # -w: ignore whitespace changes
        # -M: retain blame when moving lines
        # -C: retain blame when copying lines between files
        command = ['git', 'blame', '-w', '-M', '-C']

        lines = self.get_lines()
        if lines:
            command.extend(('-L', str(lines[0]) + ',' + str(lines[1])))
            callback = self.blame_done
        else:
            callback = functools.partial(self.blame_done,
                                         focused_line=self.get_current_line())

        command.append(self.get_file_name())
        self.run_command(command, callback)

    def get_current_line(self):
        (current_line, column) = self.view.rowcol(self.view.sel()[0].a)
        # line is 1 based
        return current_line + 1

    def get_lines(self):
        selection = self.view.sel()[0]  # todo: multi-select support?
        if selection.empty():
            return False
        # just the lines we have a selection on
        begin_line, begin_column = self.view.rowcol(selection.begin())
        end_line, end_column = self.view.rowcol(selection.end())
        # blame will fail if last line is empty and is included in the selection
        if end_line > begin_line and end_column == 0:
            end_line -= 1
        # add one to each, to line up sublime's index with git's
        return begin_line + 1, end_line + 1

    def blame_done(self, result, focused_line=1):
        view = self.scratch(result, title="Git Blame", focused_line=focused_line,
                            syntax=plugin_file("syntax/Git Blame.tmLanguage"))


class GitLog(object):
    def run(self, edit=None):
        fn = self.get_file_name()
        return self.run_log(fn != '', '--', fn)

    def run_log(self, follow, *args):
        # the ASCII bell (\a) is just a convenient character I'm pretty sure
        # won't ever come up in the subject of the commit (and if it does then
        # you positively deserve broken output...)
        # 9000 is a pretty arbitrarily chosen limit; picked entirely because
        # it's about the size of the largest repo I've tested this on... and
        # there's a definite hiccup when it's loading that
        command = ['git', 'log', '--no-color', '--pretty=%s (%h)\a%an <%aE>\a%ad (%ar)',
            '--date=local', '--max-count=9000', '--follow' if follow else None]
        command.extend(args)
        self.run_command(
            command,
            self.log_done)

    def log_done(self, result):
        self.results = [r.split('\a', 2) for r in result.strip().split('\n')]
        self.quick_panel(self.results, self.log_panel_done)

    def log_panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]
        # the commit hash is the last thing on the first line, in brackets
        ref = item[0].split(' ')[-1].strip('()')
        self.log_result(ref)

    def log_result(self, ref):
        # I'm not certain I should have the file name here; it restricts the
        # details to just the current file. Depends on what the user expects...
        # which I'm not sure of.
        self.run_command(
            ['git', 'log', '--no-color', '-p', '-1', ref, '--', self.get_file_name()],
            self.details_done)

    def details_done(self, result):
        self.scratch(result, title="Git Commit Details",
                     syntax=plugin_file("syntax/Git Commit View.tmLanguage"))


class GitLogCommand(GitLog, GitTextCommand):
    pass


class GitLogAllCommand(GitLog, GitWindowCommand):
    pass


class GitShow(object):
    def run(self, edit=None):
        # GitLog Copy-Past
        self.run_command(
            ['git', 'log', '--no-color', '--pretty=%s (%h)\a%an <%aE>\a%ad (%ar)',
            '--date=local', '--max-count=9000', '--', self.get_file_name()],
            self.show_done)

    def show_done(self, result):
        # GitLog Copy-Past
        self.results = [r.split('\a', 2) for r in result.strip().split('\n')]
        self.quick_panel(self.results, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]
        # the commit hash is the last thing on the first line, in brackets
        ref = item[0].split(' ')[-1].strip('()')
        self.run_command(
            ['git', 'show', '%s:%s' % (ref, self.get_relative_file_name())],
            self.details_done,
            ref=ref)

    def details_done(self, result, ref):
        syntax = self.view.settings().get('syntax')
        self.scratch(result, title="%s:%s" % (ref, self.get_file_name()), syntax=syntax)


class GitShowCommand(GitShow, GitTextCommand):
    pass


class GitShowAllCommand(GitShow, GitWindowCommand):
    pass


class GitGraph(object):
    def run(self, edit=None):
        filename = self.get_file_name()
        self.run_command(
            ['git', 'log', '--graph', '--pretty=%h -%d (%cr) (%ci) <%an> %s', '--abbrev-commit', '--no-color', '--decorate', '--date=relative', '--follow' if filename else None, '--', filename],
            self.log_done
        )

    def log_done(self, result):
        self.scratch(result, title="Git Log Graph", syntax=plugin_file("syntax/Git Graph.tmLanguage"))


class GitGraphCommand(GitGraph, GitTextCommand):
    pass


class GitGraphAllCommand(GitGraph, GitWindowCommand):
    pass


class GitOpenFileCommand(GitLog, GitWindowCommand):
    def run(self):
        self.run_command(['git', 'branch', '-a', '--no-color'], self.branch_done)

    def branch_done(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.branch_panel_done,
            sublime.MONOSPACE_FONT)

    def branch_panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.branch = self.results[picked].split(' ')[-1]
        self.run_log(False, self.branch)

    def log_result(self, result_hash):
        self.ref = result_hash
        self.run_command(
            ['git', 'ls-tree', '-r', '--full-tree', self.ref],
            self.ls_done)

    def ls_done(self, result):
        # Last two items are the ref and the file name
        # p.s. has to be a list of lists; tuples cause errors later
        self.results = [[match.group(2), match.group(1)] for match in re.finditer(r"\S+\s(\S+)\t(.+)", result)]

        self.quick_panel(self.results, self.ls_panel_done)

    def ls_panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]

        self.filename = item[0]
        self.fileRef = item[1]

        self.run_command(
            ['git', 'show', self.fileRef],
            self.show_done)

    def show_done(self, result):
        self.scratch(result, title="%s:%s" % (self.fileRef, self.filename))


class GitDocumentCommand(GitBlameCommand):
    def get_lines(self):
        selection = self.view.sel()[0]  # todo: multi-select support?
        # just the lines we have a selection on
        begin_line, begin_column = self.view.rowcol(selection.begin())
        end_line, end_column = self.view.rowcol(selection.end())
        # blame will fail if last line is empty and is included in the selection
        if end_line > begin_line and end_column == 0:
            end_line -= 1
        # add one to each, to line up sublime's index with git's
        return begin_line + 1, end_line + 1

    def blame_done(self, result, focused_line=1):
        shas = set((sha for sha in re.findall(r'^[0-9a-f]+', result, re.MULTILINE) if not re.match(r'^0+$', sha)))
        command = ['git', 'show', '-s', '-z', '--no-color', '--date=iso']
        command.extend(shas)

        self.run_command(command, self.show_done)

    def show_done(self, result):
        commits = []
        for commit in result.split('\0'):
            match = re.search(r'^Date:\s+(.+)$', commit, re.MULTILINE)
            if match:
                commits.append((match.group(1), commit))
        commits.sort(reverse=True)
        commits = [commit for d, commit in commits]

        self.scratch('\n\n'.join(commits), title="Git Commit Documentation",
                     syntax=plugin_file("syntax/Git Commit View.tmLanguage"))


class GitGotoCommit(GitTextCommand):
    def run(self, edit):
        view = self.view
        line = view.substr(view.line(view.sel()[0].a))
        commit = line.split(" ")[0]
        if not commit or commit == "00000000":
            return
        working_dir = view.settings().get("git_root_dir")
        self.run_command(['git', 'show', commit], self.show_done, working_dir=working_dir)

    def show_done(self, result):
        self.scratch(result, title="Git Commit View",
                     syntax=plugin_file("syntax/Git Commit View.tmLanguage"))

    def is_enabled(self):
        return True
