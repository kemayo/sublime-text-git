import sublime_plugin
from git import GitTextCommand


class GitBranchStatusListener(sublime_plugin.EventListener):
    def on_load(self, view):
        view.run_command("git_branch_status")


class GitBranchStatusCommand(GitTextCommand):
    branch = ""

    def run(self, view):
        if self.__class__.branch:
            self.set_status(self.__class__.branch)
        else:
            self.run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], self.branch_done, show_status=False)

    def branch_done(self, result):
        self.__class__.branch = result.strip()
        self.set_status(self.__class__.branch)

    def set_status(self, branch):
        self.view.set_status("git-branch", "git branch: " + branch)
