from __future__ import absolute_import, unicode_literals, print_function, division

import functools
import os

import sublime
import sublime_plugin
from . import GitTextCommand


class GitIgnoreEventListener(sublime_plugin.EventListener):
    def is_enabled(self):
        # So, is_enabled isn't actually part of the API for event listeners. But...
        s = sublime.load_settings("Git.sublime-settings")
        return s.get("gitignore_sync")

    def on_activated(self, view):
        if self.is_enabled():
            view.run_command("git_update_ignore")

    def on_post_save(self, view):
        if self.is_enabled():
            view.run_command("git_update_ignore")


class GitUpdateIgnoreCommand(GitTextCommand):
    def run(self, edit):
        data = self.view.window().project_data()
        project_file_name = self.view.window().project_file_name()
        for index, folder in enumerate(data['folders']):
            path = folder['path']
            if project_file_name:
                path = os.path.join(os.path.dirname(project_file_name), path)

            callback = functools.partial(self.ignored_files_found, folder_index=index)
            self.run_command(
                ['git', 'clean', '-ndX'],
                callback=callback,
                working_dir=path,
                error_suppresses_output=True
            )

    def ignored_files_found(self, result, folder_index):
        if not result or result.isspace():
            return

        data = self.view.window().project_data()
        folder = data['folders'][folder_index]

        if not folder:
            return

        exclude_folders = set()
        exclude_files = set()

        paths = [line.replace('Would remove ', '') for line in result.strip().split('\n')]
        for path in paths:
            if os.path.isdir(os.path.join(folder['path'], path)):
                exclude_folders.add(path)
            else:
                exclude_files.add(path)

        old_exclude_folders = set(folder.get('folder_exclude_patterns', []))
        old_exclude_files = set(folder.get('file_exclude_patterns', []))

        if exclude_folders != old_exclude_folders or exclude_files != old_exclude_files:
            print('Git: updating project exclusions', folder['path'], exclude_folders, exclude_files)
            folder['folder_exclude_patterns'] = list(exclude_folders)
            folder['file_exclude_patterns'] = list(exclude_files)
            self.view.window().set_project_data(data)
