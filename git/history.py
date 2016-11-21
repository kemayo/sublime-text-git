from __future__ import absolute_import, unicode_literals, print_function, division

import functools
import re
import os
import os.path

import sublime
import sublime_plugin
from . import GitTextCommand, GitWindowCommand, plugin_file, git_root


class GitBlameCommand(GitTextCommand):
    def run(self, edit):
        # somewhat custom blame command:
        # -w: ignore whitespace changes
        # -M: retain blame when moving lines
        # -C: retain blame when copying lines between files
        command = ['git', 'blame', '-w', '-M', '-C']
        line_ranges = [self.get_lines(selection) for selection in self.view.sel() if not selection.empty()]

        if line_ranges:
            for line_range in line_ranges:
                command.extend(('-L', str(line_range[0]) + ',' + str(line_range[1])))
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

    def get_lines(self, selection):
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

class GitLogMulti(GitLog):
    def log_results(self, refs):
        for ref in refs:
            self.log_result(ref)

    def get_hash_region(self):
        return None

    def run(self, edit=None):
        hashes = []
        view = self.active_view();
        for s in self.get_hash_region():
            hs = view.substr(s);
            if hs.strip("0"):
                hashes.append(hs)
        return self.log_results(hashes)

class GitLogMultiFromSels(GitLogMulti):
    def get_hash_region(self):
        view = self.active_view()
        return [(s if not s.empty else view.word(s)) for s in view.sel()]

class GitLogMultiFromLines(GitLogMulti):
    def get_contained_region_in_lines(self, regions, lines):
        if len(lines) <= 0:
            return None
        whole_lines = lines[0]
        for line in lines:
            whole_lines = whole_lines.cover(line)
        contained_regions = []
        for region in regions:
            if not whole_lines.contains(region):
                continue
            for line in lines:
                if line.contains(region):
                    contained_regions.append(region)
                    break
        return contained_regions

    def get_sels(self):
        return self.active_view().sel()

    def get_hash_region(self):
        view = self.active_view();
        regions = view.find_by_selector("string.sha")
        lines = [view.line(sel) for sel in self.get_sels()]
        return self.get_contained_region_in_lines(regions, lines)

class GitGotoCommit(GitLogMultiFromLines):
    def get_sels(self):
        return [sel.a for sel in self.active_view().sel()] # for the collections of first line at each selection

class GitLogMultiTextCommand(GitTextCommand):
    def get_working_dir(self):
        # git_log_graph_location is used to show commit of the only file that lead to "Git: Graph Current File"
        # git_root_dir is not work for above case
        # also git_root_dir may be None when "Git: Graph All"
        path = self.view.settings().get("git_log_graph_location")
        if path:
            return os.path.realpath(os.path.dirname(path))
        return self.view.settings().get("git_root_dir")
    def get_file_name(self):
        path = self.view.settings().get("git_log_graph_location")
        return os.path.basename(path) if path else None
    def is_enabled(self):
        view = self.view
        selection = view.sel()[0]
        return bool(
            view.match_selector(selection.a, "text.git-blame")
            or view.match_selector(selection.a, "text.git-graph")
        )

class GitLogMultiFromSelsCommand(GitLogMultiFromSels, GitLogMultiTextCommand):
    pass

class GitLogMultiFromLinesCommand(GitLogMultiFromLines, GitLogMultiTextCommand):
    pass

class GitGotoCommitCommand(GitGotoCommit, GitLogMultiTextCommand):
    pass

class GitLogAsOneDiff(GitLogMultiFromLines):
    def log_results(self, refs):
        n = len(refs)
        if ( n < 1 ):
            return

        self.files = set()
        for ref in refs:
            self.log_result(ref)
        self.run_command(
            ['git', 'diff', refs[n-1]+'~1', refs[0], '--', self.get_file_name()],
            self.as_one_diff_done)

    def details_done(self, result):
        for s in result.split('\n'):
            mm = re.search(r'^[+]{3} b(.*)', s.strip())
            if ( mm ):
                self.files.add(mm.group(1))

    def as_one_diff_done(self, result):
        poslist = []
        pos = 0
        diffTag = 'diff --git'
        while True:
            pos = result.find(diffTag, pos)
            if pos < 0:
                break
            if (0 == pos) or ('\n' == result[pos-1]) or ('\a' == result[pos-1]):
                poslist.append(pos)
            pos += len(diffTag)
        poslist.append(len(result))

        results = []
        for i in range(0,len(poslist)-1):
            for filename in self.files:
                pos = result.find(filename, poslist[i], poslist[i+1])
                if 0 <= pos :
                    results.append(result[poslist[i]:poslist[i+1]])
                    break

        self.scratch(''.join(results), title="Git One Diff Details", syntax=plugin_file("syntax/Git Commit View.tmLanguage"))

class GitLogAsOneDiffCommand(GitLogAsOneDiff, GitLogMultiTextCommand):
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
            ['git', 'show', '%s:%s' % (ref, self.get_relative_file_path())],
            self.details_done,
            ref=ref)

    def details_done(self, result, ref):
        syntax = self.view.settings().get('syntax')
        self.scratch(result, title="%s:%s" % (ref, self.get_file_name()), syntax=syntax)


class GitShowCommand(GitShow, GitTextCommand):
    pass


class GitShowAllCommand(GitShow, GitWindowCommand):
    pass


class GitShowCommitCommand(GitWindowCommand):
    def run(self, edit=None):
        self.window.show_input_panel("Commit to show:", "", self.input_done, None, None)

    def input_done(self, commit):
        commit = commit.strip()

        self.run_command(['git', 'show', commit, '--'], self.show_done, commit=commit)

    def show_done(self, result, commit):
        if result.startswith('fatal:'):
            self.panel(result)
            return
        self.scratch(result, title="Git Commit: %s" % commit,
                     syntax=plugin_file("syntax/Git Commit View.tmLanguage"))


class GitGraph(object):
    def run(self, edit=None):
        filename = self.get_file_name()
        self.run_command(
            ['git', 'log', '--graph', '--pretty=%h -%d (%cr) (%ci) <%an> %s', '--abbrev-commit', '--no-color', '--decorate', '--date=relative', '--follow' if filename else None, '--', filename],
            self.log_done
        )

    def log_done(self, result):
        location = self.get_working_dir() + "/" + self.get_file_name()
        view = self.scratch(result, title="Git Log Graph", syntax=plugin_file("syntax/Git Graph.tmLanguage"))
        view.settings().set("git_log_graph_location", location)


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

