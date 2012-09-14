import sublime
import sublime_plugin
from git import GitTextCommand


class GitBranchStatusListener(sublime_plugin.EventListener):
    def on_activated(self, view):
        view.run_command("git_branch_status")


class GitBranchStatusCommand(GitTextCommand):
    def run(self, view):
        s = sublime.load_settings("Git.sublime-settings")
        if s.get("statusbar_branch"):
            self.run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], self.branch_done, show_status=False)
        else:
            self.view.set_status("git-branch", "")

    def branch_done(self, result):
        self.view.set_status("git-branch", "git branch: " + result.strip())
