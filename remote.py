#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-08-28 00:48:42
# Filename      : remote.py
# Description   : 
import sublime
from git import GitWindowCommand

class GitRemoteCommand(GitWindowCommand):
    def is_enabled(self):
        return True

    def list_remote(self):
        self.run_command(['git', 'remote', '-v'], self.show_remote)

    def show_remote(self, result):
        _remote_hash = {}
        for line in result.strip().split('\n'):
            remote_name, remote_url = [ field.strip() for field in line.split()[:2]]
            _remote_hash[remote_name] = remote_url

        self.results = [ list(item) for item in _remote_hash.items() ]
        self.quick_panel(self.results, self.panel_done, sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        print(picked)

class GitRemoteAddCommand(GitRemoteCommand):
    def run(self):
        self.get_window().show_input_panel('Remote Name:Url', '', self.remote_add, None, None)

    def remote_add(self, remote_string):
        if ':' not in remote_string:
            sublime.status_message('Usage remote_name:remote_url')
            return

        remote_params = [ param.strip() for param in remote_string.split(':', 1)]

        self.run_command(['git', 'remote', 'add'] + remote_params)

class GitRemoteRemoveCommand(GitRemoteCommand):
    def run(self):
        self.list_remote()

    def panel_done(self, picked):
        if picked >= len(self.results) or picked < 0:
            return
        remote = self.results[picked]
        self.run_command(['git', 'remote' , 'rm', remote[0]])

class GitRemoteShowCommand(GitRemoteCommand):
    def run(self):
        self.list_remote()
    
