import sublime

from .git import GitWindowCommand

class GitHubflowCommand(GitWindowCommand):
    def is_visible(self):
        s = sublime.load_settings("Git.sublime-settings")
        return s.get('hubflow', False)

class GitHubflowFeatureStartCommand(GitHubflowCommand):
    def run(self):
        self.get_window().show_input_panel('Enter Feature Name:', '', self.on_done, None, None)

    def on_done(self, feature_name):
        self.run_command(['git', 'hf', 'feature', 'start', feature_name])


class GitHubflowFeatureFinishCommand(GitHubflowCommand):
    def run(self):
        self.run_command(['git', 'hf', 'feature'], self.feature_done)

    def feature_done(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_feature = self.results[picked]
        if picked_feature.startswith("*"):
            picked_feature = picked_feature.strip("*")
        picked_feature = picked_feature.strip()
        self.run_command(['git', 'hf', 'feature', 'finish', picked_feature])


class GitHubflowReleaseStartCommand(GitHubflowCommand):
    def run(self):
        self.get_window().show_input_panel('Enter Version Number:', '', self.on_done, None, None)

    def on_done(self, release_name):
        self.run_command(['git', 'hf', 'release', 'start', release_name])


class GitHubflowReleaseFinishCommand(GitHubflowCommand):
    def run(self):
        self.run_command(['git', 'hf', 'release'], self.release_done)

    def release_done(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_release = self.results[picked]
        if picked_release.startswith("*"):
            picked_release = picked_release.strip("*")
        picked_release = picked_release.strip()
        self.run_command(['git', 'hf', 'release', 'finish', picked_release])


class GitHubflowHotfixStartCommand(GitHubflowCommand):
    def run(self):
        self.get_window().show_input_panel('Enter hotfix name:', '', self.on_done, None, None)

    def on_done(self, hotfix_name):
        self.run_command(['git', 'hf', 'hotfix', 'start', hotfix_name])


class GitHubflowHotfixFinishCommand(GitHubflowCommand):
    def run(self):
        self.run_command(['git', 'hf', 'hotfix'], self.hotfix_done)

    def hotfix_done(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_hotfix = self.results[picked]
        if picked_hotfix.startswith("*"):
            picked_hotfix = picked_hotfix.strip("*")
        picked_hotfix = picked_hotfix.strip()
        self.run_command(['git', 'hf', 'hotfix', 'finish', picked_hotfix])


class GitHubflowPushCommand(GitHubflowCommand):
    def run(self):
        self.run_command(['git', 'hf', 'push'])

class GitHubflowPullCommand(GitHubflowCommand):
    def run(self):
        self.run_command(['git', 'hf', 'pull'])

class GitHubflowUpdateCommand(GitHubflowCommand):
    def run(self):
        self.run_command(['git', 'hf', 'update'])

