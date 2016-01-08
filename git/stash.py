from __future__ import absolute_import, unicode_literals, print_function, division

from . import GitWindowCommand


class GitStashCommand(GitWindowCommand):
    may_change_files = True
    command_to_run_after_list = False

    def run(self):
        self.run_command(['git', 'stash', 'list'], self.stash_list_done)

    def stash_list_done(self, result):
        # No stash list at all
        if not result:
            self.panel('No stash found')
            return

        self.results = result.rstrip().split('\n')

        # If there is only one, apply it
        if len(self.results) == 1:
            self.stash_list_panel_done()
        else:
            self.quick_panel(self.results, self.stash_list_panel_done)

    def stash_list_panel_done(self, picked=0):
        if 0 > picked < len(self.results):
            return

        # get the stash ref (e.g. stash@{3})
        stash = self.results[picked].split(':')[0]
        self.run_command(['git', 'stash'] + self.command_to_run_after_list + [stash], self.handle_command or self.generic_done, stash=stash)

    def handle_command(self, result, stash, **kw):
        return self.generic_done(result, **kw)


class GitStashListCommand(GitStashCommand):
    may_change_files = False
    command_to_run_after_list = ['show', '-p']

    def handle_command(self, result, stash, **kw):
        self.scratch(result, title=stash, syntax="Packages/Diff/Diff.tmLanguage")


class GitStashApplyCommand(GitStashCommand):
    command_to_run_after_list = ['apply']


class GitStashDropCommand(GitStashCommand):
    command_to_run_after_list = ['drop']
