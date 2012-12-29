import sublime
import re
from .git import GitTextCommand, GitWindowCommand
import functools

# Stores the path related to a "Git Diff" view.
git_diff_path = {}


def do_when(conditional, callback, *args, **kwargs):
    if conditional():
        return callback(*args, **kwargs)
    sublime.set_timeout(functools.partial(do_when, conditional, callback, *args, **kwargs), 50)


def goto_xy(view, line, col):
    view.run_command("goto_line", {"line": line})
    for i in range(col):
        view.run_command("move", {"by": "characters", "forward": True})


class GitDiffListener(sublime_plugin.EventListener):
    def on_close(self, view):
        global git_diff_path
        if view.name() != "Git Diff":
            return
        git_diff_path.pop(view.id())


class GitDiff (object):
    def run(self, edit=None):
        self.run_command(['git', 'diff', '--no-color', '--', self.get_file_name()],
                         self.diff_done)

    def diff_done(self, result):
        global git_diff_path

        if not result.strip():
            self.panel("No output")
            return
        s = sublime.load_settings("Git.sublime-settings")
        syntax = s.get("diff_syntax", "Packages/Diff/Diff.tmLanguage")
        if s.get('diff_panel'):
            view = self.panel(result, syntax=syntax)
        else:
            view = self.scratch(result, title="Git Diff", syntax=syntax)

        lines_inserted = view.find_all(r'^\+[^+]{2} ')
        lines_deleted = view.find_all(r'^-[^-]{2} ')

        view.add_regions("inserted", lines_inserted, "markup.inserted.diff", "dot", sublime.HIDDEN)
        view.add_regions("deleted", lines_deleted, "markup.deleted.diff", "dot", sublime.HIDDEN)

        git_diff_path[view.id()] = self.get_working_dir()


class GitDiffCommit (object):
    def run(self, edit=None):
        self.run_command(['git', 'diff', '--cached', '--no-color'],
            self.diff_done)

    def diff_done(self, result):
        if not result.strip():
            self.panel("No output")
            return
        s = sublime.load_settings("Git.sublime-settings")
        syntax = s.get("diff_syntax", "Packages/Diff/Diff.tmLanguage")
        self.scratch(result, title="Git Diff", syntax=syntax)


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


class GitGotoDiff(sublime_plugin.TextCommand):
    def run(self, edit):
        v = self.view
        if v.name() != "Git Diff":
            return

        beg = v.sel()[0].a     # Current position in selection
        pt = v.line(beg).a     # First position in the current diff line
        column = beg - pt - 1  # The current column (-1 because the first char in diff file)

        file_name = None
        hunk_line = None
        line_offset = 0

        while pt > 0:
            line = v.line(pt)
            lineContent = v.substr(line)
            if lineContent.startswith("@@"):
                if not hunk_line:
                    hunk_line = lineContent
            elif lineContent.startswith("+++ b/"):
                file_name = v.substr(sublime.Region(line.a+6, line.b))
                break
            elif not hunk_line and not lineContent.startswith("-"):
                line_offset = line_offset+1

            pt = v.line(pt-1).a

        hunk = re.match(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*", hunk_line)
        if not hunk:
            sublime.status_message("No hunk info")
            return

        hunk_start_line = hunk.group(3)
        goto_line = int(hunk_start_line) + line_offset - 1

        file_name = os.path.join(git_diff_path[v.id()], file_name)

        new_view = self.view.window().open_file(file_name)
        do_when(lambda: not new_view.is_loading(),
                lambda: goto_xy(new_view, goto_line, column))
