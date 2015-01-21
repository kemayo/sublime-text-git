import os

import sublime
from .git import GitWindowCommand, git_root_exist, git_root


class GitInit(object):
    def git_init(self, directory):
        if os.path.exists(directory):
            self.run_command(['git', 'init'], self.git_inited, working_dir=directory)
        else:
            sublime.status_message("Directory does not exist.")

    def git_inited(self, result):
        sublime.status_message(result)


class GitInitCommand(GitInit, GitWindowCommand):
    def run(self):
        self.get_window().show_input_panel("Git directory", self.get_working_dir(), self.git_init, None, None)

    def is_enabled(self):
        if not git_root_exist(self.get_working_dir()):
            return True
        else:
            return False


class GitBranchCommand(GitWindowCommand):
    may_change_files = True
    command_to_run_after_branch = ['checkout']
    extra_flags = []

    def run(self):
        self.close_removed = sublime.load_settings("Git.sublime-settings").get("close_removed_on_checkout")
        self.run_command(['git', 'branch', '--no-color'] + self.extra_flags, self.branch_done)

    def branch_done(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_branch = self.results[picked]
        if picked_branch.startswith("*"):
            return
        picked_branch = picked_branch.strip()
        self.delfiles = []
        if self.close_removed:
            self.run_command(['git', 'diff', '--name-only', '--diff-filter=D'] + ['..'+picked_branch], self.manage_diffs, branch=picked_branch)
        else:
            self.do_checkout(picked_branch)

    def do_checkout(self, branch):
        self.run_command(['git'] + self.command_to_run_after_branch + [branch], self.update_status)

    def manage_diffs(self, result, branch):
        if result:
            self.delfiles = result.strip().split('\n')
        self.do_checkout(branch)

    def update_status(self, result):
        if result.startswith("error: "):
            sublime.error_message(result[7:])
            return
        if len(self.delfiles) > 0:
            working_dir = self.get_working_dir()
            root = git_root(working_dir)
            views = self.window.views()
            for f in self.delfiles:
                fullf = os.path.join(root, f)
                for v in views:
                    if not v.is_dirty() and v.file_name() == fullf:
                        v.close()
        global branch
        branch = ""
        for view in self.window.views():
            view.run_command("git_branch_status")


class GitMergeCommand(GitBranchCommand):
    command_to_run_after_branch = ['merge']
    extra_flags = ['--no-merge']


class GitDeleteBranchCommand(GitBranchCommand):
    command_to_run_after_branch = ['branch', '-d']


class GitNewBranchCommand(GitWindowCommand):
    def run(self):
        self.get_window().show_input_panel("Branch name", "",
            self.on_input, None, None)

    def on_input(self, branchname):
        if branchname.strip() == "":
            self.panel("No branch name provided")
            return
        self.run_command(['git', 'checkout', '-b', branchname])


class GitNewTagCommand(GitWindowCommand):
    def run(self):
        self.get_window().show_input_panel("Tag name", "", self.on_input, None, None)

    def on_input(self, tagname):
        if not tagname.strip():
            self.panel("No branch name provided")
            return
        self.run_command(['git', 'tag', tagname])


class GitDeleteTagCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'tag'], self.fetch_tag)

    def fetch_tag(self, result):
        if result.strip() == "":
            sublime.status_message("No Tags provided.")
            return
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_tag = self.results[picked]
        picked_tag = picked_tag.strip()
        if sublime.ok_cancel_dialog("Delete \"%s\" Tag?" % picked_tag, "Delete"):
            self.run_command(['git', 'tag', '-d', picked_tag])


class GitShowTagsCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'tag'], self.fetch_tag)

    def fetch_tag(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_tag = self.results[picked]
        picked_tag = picked_tag.strip()
        self.run_command(['git', 'show', picked_tag])


class GitCheckoutTagCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'tag'], self.fetch_tag)

    def fetch_tag(self, result):
        if result.strip() == "":
            sublime.status_message("No Tags provided.")
            return
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_tag = self.results[picked]
        picked_tag = picked_tag.strip()
        self.run_command(['git', 'checkout', "tags/%s" % picked_tag])


class GitPullCurrentBranchCommand(GitWindowCommand):
    command_to_run_after_describe = 'pull'

    def run(self):
        self.run_command(['git', 'describe', '--contains', '--all', 'HEAD'], callback=self.describe_done)

    def describe_done(self, result):
        self.current_branch = result.strip()
        self.run_command(['git', 'remote'], callback=self.remote_done)

    def remote_done(self, result):
        self.remotes = result.rstrip().split('\n')
        if len(self.remotes) == 1:
            self.panel_done()
        else:
            self.quick_panel(self.remotes, self.panel_done, sublime.MONOSPACE_FONT)

    def panel_done(self, picked=0):
        if picked < 0 or picked >= len(self.remotes):
            return
        self.picked_remote = self.remotes[picked]
        self.picked_remote = self.picked_remote.strip()
        self.run_command(['git', self.command_to_run_after_describe, self.picked_remote, self.current_branch])


class GitPushCurrentBranchCommand(GitPullCurrentBranchCommand):
    command_to_run_after_describe = 'push'
