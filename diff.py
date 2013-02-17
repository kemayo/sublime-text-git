import sublime
from git import GitTextCommand, GitWindowCommand


class GitDiff (object):
    def run(self, edit=None):
        command = ['git', 'log', '--name-only', '--pretty=%s\a%h %an <%aE>\a%ad (%ar)',
            '--date=local', '--max-count=9000']
        file_name = self.get_file_name()
        if file_name:
            command.extend(['--follow', '--', file_name])
        self.run_command(
            command,
            self.show_done)

    def show_done(self, result):
        # GitLog Copy-Past
        import os
        self.results = []
        self.files = {}
        relative = None
        for r in result.strip().split('\n'):
            if r:
                _result = r.strip().split('\a', 2)
                if len(_result) == 1:
                    if relative is None:
                        # Find relative path
                        relative = os.sep.join(['..'] * (len(os.path.normpath(_result[0]).split(os.sep)) - 1))
                        if relative:
                            relative += os.sep
                    ref = result[1].split(' ', 1)[0]
                    self.files[ref] = relative + _result[0]
                else:
                    result = _result
                    ref = result[1].split(' ', 1)
                    result[0] = u"%s - %s" % (ref[0], result[0])
                    result[1] = ref[1]
                    self.results.append(result)
        self.quick_panel(self.results, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]
        # the commit hash is the first thing on the second line
        ref = item[0].split(' ', 1)[0]
        command = ['git', 'diff', '-C', '--no-color', ref, '--']
        command.extend(set(self.files.values() + [self.get_file_name()]))
        self.run_command(
            command,
            self.diff_done,
            ref=ref)

    def diff_done(self, result, ref):
        if not result.strip():
            self.panel("No output")
            return
        s = sublime.load_settings("Git.sublime-settings")
        if s.get('diff_panel'):
            view = self.panel(result)
        else:
            view = self.scratch(result, title="Git Diff")

        lines_inserted = view.find_all(r'^\+[^+]{2} ')
        lines_deleted = view.find_all(r'^-[^-]{2} ')

        view.add_regions("inserted", lines_inserted, "markup.inserted.diff", "dot", sublime.HIDDEN)
        view.add_regions("deleted", lines_deleted, "markup.deleted.diff", "dot", sublime.HIDDEN)


class GitDiffCommit (object):
    def run(self, edit=None):
        self.run_command(['git', 'diff', '-C', '--no-color', '--cached'],
            self.diff_done)

    def diff_done(self, result):
        if not result.strip():
            self.panel("No output")
            return
        s = sublime.load_settings("Git.sublime-settings")
        if s.get('diff_panel'):
            self.panel(result)
        else:
            self.scratch(result, title="Git Diff")


class GitDiffCommand(GitDiff, GitTextCommand):
    pass


class GitDiffAllCommand(GitDiff, GitWindowCommand):
    pass


class GitDiffCommitCommand(GitDiffCommit, GitWindowCommand):
    pass


class GitDiffTool(object):
    def run(self, edit=None):
        self.run_command(['git', 'difftool', '--', self.get_file_name()])


class GitDiffToolCommand(GitDiffTool, GitTextCommand):
    pass


class GitDiffToolAll(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'difftool'])
