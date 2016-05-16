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
    def path(self, folderpath):
        project_file_name = self.view.window().project_file_name()
        if project_file_name:
            return os.path.join(os.path.dirname(project_file_name), folderpath)
        return folderpath

    def run(self, edit):
        self.count = 0
        self.excludes = {}

        data = self.view.window().project_data()
        for index, folder in enumerate(data['folders']):
            self.count += 2
            self.excludes[index] = {
                'files': set(),
                'folders': set(),
            }

            path = self.path(folder['path'])
            callback = functools.partial(self.ignored_files_found, folder_index=index)
            self.run_command(
                ['git', 'status', '--ignored', '--porcelain'],
                callback=callback,
                working_dir=path,
                error_suppresses_output=True,
                show_status=False
            )
            self.run_command(
                ['git', 'submodule', 'foreach', 'git status --ignored --porcelain'],
                callback=callback,
                working_dir=path,
                error_suppresses_output=True,
                show_status=False
            )

    def ignored_files_found(self, result, folder_index):
        self.count -= 1

        self.process_ignored_files(result, folder_index)

        if self.count == 0:
            self.all_ignored_files_found()

    def process_ignored_files(self, result, folder_index):
        data = self.view.window().project_data()
        folder = data['folders'][folder_index]

        if not folder:
            return
        if not result or result.isspace():
            return

        root = self.path(folder['path'])
        exclude_folders = self.excludes[folder_index]['folders']
        exclude_files = self.excludes[folder_index]['files']

        subroot = ''
        for line in result.strip().split('\n'):
            if line.startswith('Entering'):
                subroot = line.replace('Entering ', '').replace('\'', '')
            if not line.startswith('!!'):
                continue
            path = os.path.join(subroot, line.replace('!! ', ''))

            if os.path.isdir(os.path.join(root, path)):
                exclude_folders.add(path.rstrip('\\/'))
            else:
                exclude_files.add(path)

        return exclude_files, exclude_folders

    def all_ignored_files_found(self):
        data = self.view.window().project_data()
        changed = False
        for index, folder in enumerate(data['folders']):
            exclude_folders = self.excludes[index]['folders']
            exclude_files = self.excludes[index]['files']

            old_exclude_folders = set(folder.get('folder_exclude_patterns', []))
            old_exclude_files = set(folder.get('file_exclude_patterns', []))

            if exclude_folders != old_exclude_folders or exclude_files != old_exclude_files:
                print('Git: updating project exclusions', folder['path'], exclude_folders, exclude_files)
                folder['folder_exclude_patterns'] = list(exclude_folders)
                folder['file_exclude_patterns'] = list(exclude_files)
                changed = True
        if changed:
            self.view.window().set_project_data(data)
