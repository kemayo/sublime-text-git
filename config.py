import os
import re

import sublime
from git import GitWindowCommand, git_root


class GitOpenConfigFileCommand(GitWindowCommand):
    def run(self):
        working_dir = git_root(self.get_working_dir())
        config_file = os.path.join(working_dir, '.git/config')
        if os.path.exists(config_file):
            self.window.open_file(config_file)
        else:
            sublime.status_message("No config found")


class GitOpenConfigUrlCommand(GitWindowCommand):
    def run(self, url_param):
        self.run_command(['git', 'config', url_param], self.url_done)

    def url_done(self, result):
        results = [r for r in result.rstrip().split('\n') if r.startswith("http")]
        if len(results):
            url = results[0]
            user_end = url.index('@')
            if user_end > -1:
                # Remove user and pass from url
                user_start = url.index('//') + 1
                user = url[user_start+1:user_end+1]
                url = url.replace(user, '')
            self.window.run_command('open_url', {"url": url})
        else:
            sublime.status_message("No url to open")
