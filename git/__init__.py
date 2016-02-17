from __future__ import absolute_import, unicode_literals, print_function, division

import os
import re
import sublime
import sublime_plugin
import threading
import subprocess
import functools
import os.path
import time


git_root_cache = {}
_has_warned = False


# Goal is to get: "Packages/Git", allowing for people who rename things
def find_plugin_directory():
    if ".sublime-package" in __file__:
        # zipped package, all we care about is the bit right before .sublime-package
        match = re.search(r"([^\\/]+)\.sublime-package", __file__)
        if match:
            return "Packages/" + match.group(1)
    if __file__.startswith('./'):
        # ST2, we get "./git/__init__.py" which is pretty useless since we want the part above that
        # However, os.getcwd() is the plugin directory!
        full = os.getcwd()
    else:
        # In a complete inversion, in ST3 when a plugin is loaded we
        # actually can trust __file__. It'll be something like:
        # /Users/dlynch/Library/Application Support/Sublime Text 3/Packages/Git/git/__init__.py
        full = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
    dirname = os.path.split(full)[-1]
    return "Packages/" + dirname.replace(".sublime-package", "")
PLUGIN_DIRECTORY = find_plugin_directory()


def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)


def open_url(url):
    sublime.active_window().run_command('open_url', {"url": url})


def git_root(directory):
    global git_root_cache

    retval = False
    leaf_dir = directory

    if leaf_dir in git_root_cache and git_root_cache[leaf_dir]['expires'] > time.time():
        return git_root_cache[leaf_dir]['retval']

    while directory:
        if os.path.exists(os.path.join(directory, '.git')):
            retval = directory
            break
        parent = os.path.realpath(os.path.join(directory, os.path.pardir))
        if parent == directory:
            # /.. == /
            retval = False
            break
        directory = parent

    git_root_cache[leaf_dir] = {
        'retval': retval,
        'expires': time.time() + 5
    }

    return retval


# for readability code
def git_root_exist(directory):
    return git_root(directory)


def view_contents(view):
    region = sublime.Region(0, view.size())
    return view.substr(region)


def plugin_file(name):
    return PLUGIN_DIRECTORY + '/' + name


def do_when(conditional, command, *args, **kwargs):
    if conditional():
        return command(*args, **kwargs)
    sublime.set_timeout(functools.partial(do_when, conditional, command, *args, **kwargs), 50)


def goto_xy(view, line, col):
    view.run_command("goto_line", {"line": line})
    for i in range(col):
        view.run_command("move", {"by": "characters", "forward": True})


def _make_text_safeish(text, fallback_encoding, method='decode'):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal... and there's no way to tell what's coming out of
    # git in output. So...
    try:
        unitext = getattr(text, method)('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        unitext = getattr(text, method)(fallback_encoding)
    except AttributeError:
        # strongly implies we're already unicode, but just in case let's cast
        # to string
        unitext = str(text)
    return unitext


def _test_paths_for_executable(paths, test_file):
    for directory in paths:
        file_path = os.path.join(directory, test_file)
        if os.path.exists(file_path) and os.access(file_path, os.X_OK):
            return file_path


def find_binary(cmd):
    # It turns out to be difficult to reliably run git, with varying paths
    # and subprocess environments across different platforms. So. Let's hack
    # this a bit.
    # (Yes, I could fall back on a hardline "set your system path properly"
    # attitude. But that involves a lot more arguing with people.)
    path = os.environ.get('PATH', '').split(os.pathsep)
    if os.name == 'nt':
        cmd = cmd + '.exe'

    path = _test_paths_for_executable(path, cmd)

    if not path:
        # /usr/local/bin:/usr/local/git/bin
        if os.name == 'nt':
            extra_paths = (
                os.path.join(os.environ.get("ProgramFiles", ""), "Git", "bin"),
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Git", "bin"),
            )
        else:
            extra_paths = (
                '/usr/local/bin',
                '/usr/local/git/bin',
            )
        path = _test_paths_for_executable(extra_paths, cmd)
    return path
GIT = find_binary('git')
GITK = find_binary('gitk')


class CommandThread(threading.Thread):
    command_lock = threading.Lock()

    def __init__(self, command, on_done, working_dir="", fallback_encoding="", error_suppresses_output=False, **kwargs):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir
        if "stdin" in kwargs:
            self.stdin = kwargs["stdin"].encode()
        else:
            self.stdin = None
        if "stdout" in kwargs:
            self.stdout = kwargs["stdout"]
        else:
            self.stdout = subprocess.PIPE
        self.fallback_encoding = fallback_encoding
        self.error_suppresses_output = error_suppresses_output
        self.kwargs = kwargs

    def run(self):
        # Ignore directories that no longer exist
        if not os.path.isdir(self.working_dir):
            return

        self.command_lock.acquire()
        output = ''
        callback = self.on_done
        try:
            if self.working_dir != "":
                os.chdir(self.working_dir)
            # Windows needs startupinfo in order to start process in background
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            env = os.environ.copy()

            shell = False
            if sublime.platform() == 'windows':
                shell = True
                if 'HOME' not in env:
                    env[str('HOME')] = str(env['USERPROFILE'])

            # universal_newlines seems to break `log` in python3
            proc = subprocess.Popen(self.command,
                stdout=self.stdout, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE, startupinfo=startupinfo,
                shell=shell, universal_newlines=False,
                env=env)
            output = proc.communicate(self.stdin)[0]
            if self.error_suppresses_output and proc.returncode is not None and proc.returncode > 0:
                output = False
            if not output:
                output = ''
            output = _make_text_safeish(output, self.fallback_encoding)
        except subprocess.CalledProcessError as e:
            if self.error_suppresses_output:
                output = ''
            else:
                output = e.returncode
        except OSError as e:
            callback = sublime.error_message
            if e.errno == 2:
                global _has_warned
                if not _has_warned:
                    _has_warned = True
                    output = "{cmd} binary could not be found in PATH\n\nConsider using the {cmd_setting}_command setting for the Git plugin\n\nPATH is: {path}".format(cmd=self.command[0], cmd_setting=self.command[0].replace('-', '_'), path=os.environ['PATH'])
            else:
                output = e.strerror
        finally:
            self.command_lock.release()
            main_thread(callback, output, **self.kwargs)


# A base for all commands
class GitCommand(object):
    may_change_files = False

    def run_command(self, command, callback=None, show_status=True,
            filter_empty_args=True, no_save=False, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs[str('working_dir')] = str(self.get_working_dir())
        if 'fallback_encoding' not in kwargs and self.active_view() and self.active_view().settings().get('fallback_encoding'):
            kwargs[str('fallback_encoding')] = str(self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0])

        s = sublime.load_settings("Git.sublime-settings")
        if s.get('save_first') and self.active_view() and self.active_view().is_dirty() and not no_save:
            self.active_view().run_command('save')
        if command[0] == 'git':
            us = sublime.load_settings('Preferences.sublime-settings')
            if s.get('git_command') or us.get('git_binary'):
                command[0] = s.get('git_command') or us.get('git_binary')
            elif GIT:
                command[0] = GIT
        if command[0] == 'gitk' and s.get('gitk_command'):
            if s.get('gitk_command'):
                command[0] = s.get('gitk_command')
            elif GITK:
                command[0] = GITK
        if command[0] == 'git' and command[1] == 'flow' and s.get('git_flow_command'):
            command[0] = s.get('git_flow_command')
            del(command[1])
        if not callback:
            callback = self.generic_done

        thread = CommandThread(command, callback, **kwargs)
        thread.start()

        if show_status:
            message = kwargs.get('status_message', False) or ' '.join(command)
            sublime.status_message(message)

    def generic_done(self, result, **kw):
        if self.may_change_files and self.active_view() and self.active_view().file_name():
            if self.active_view().is_dirty():
                result = "WARNING: Current view is dirty.\n\n"
            else:
                # just asking the current file to be re-opened doesn't do anything
                print("reverting")
                position = self.active_view().viewport_position()
                self.active_view().run_command('revert')
                do_when(lambda: not self.active_view().is_loading(), lambda: self.active_view().set_viewport_position(position, False))
                # self.active_view().show(position)

        view = self.active_view()
        if view and view.settings().get('live_git_annotations'):
            view.run_command('git_annotate')

        if not result.strip():
            return
        self.panel(result)

    def _output_to_view(self, output_file, output, clear=False,
            syntax="Packages/Diff/Diff.tmLanguage", **kwargs):
        output_file.set_syntax_file(syntax)
        args = {
            'output': output,
            'clear': clear
        }
        output_file.run_command('git_scratch_output', args)

    def scratch(self, output, title=False, focused_line=1, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        self.record_git_root_to_view(scratch_file)
        scratch_file.settings().set('word_wrap', False)
        scratch_file.run_command('goto_line', {'line': focused_line})
        return scratch_file

    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().get_output_panel("git")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.record_git_root_to_view(self.output_view)
        self.get_window().run_command("show_panel", {"panel": "output.git"})

    def quick_panel(self, *args, **kwargs):
        self.get_window().show_quick_panel(*args, **kwargs)

    def record_git_root_to_view(self, view):
        # Store the git root directory in the view so we can resolve relative paths
        # when the user wants to navigate to the source file.
        if self.get_working_dir():
            root = git_root(self.get_working_dir())
        else:
            root = self.active_view().settings().get("git_root_dir")
        view.settings().set("git_root_dir", root)


# A base for all git commands that work with the entire repository
class GitWindowCommand(GitCommand, sublime_plugin.WindowCommand):
    def active_view(self):
        return self.window.active_view()

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    @property
    def fallback_encoding(self):
        if self.active_view() and self.active_view().settings().get('fallback_encoding'):
            return self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

    # If there's no active view or the active view is not a file on the
    # filesystem (e.g. a search results view), we can infer the folder
    # that the user intends Git commands to run against when there's only
    # only one.
    def is_enabled(self):
        if self._active_file_name() or len(self.window.folders()) == 1:
            return bool(git_root(self.get_working_dir()))
        return False

    def get_file_name(self):
        return ''

    def get_relative_file_name(self):
        return ''

    # If there is a file in the active view use that file's directory to
    # search for the Git root.  Otherwise, use the only folder that is
    # open.
    def get_working_dir(self):
        file_name = self._active_file_name()
        if file_name:
            return os.path.realpath(os.path.dirname(file_name))
        try:  # handle case with no open folder
            return self.window.folders()[0]
        except IndexError:
            return ''

    def get_window(self):
        return self.window


# A base for all git commands that work with the file in the active view
class GitTextCommand(GitCommand, sublime_plugin.TextCommand):
    def active_view(self):
        return self.view

    def is_enabled(self):
        # First, is this actually a file on the file system?
        if self.view.file_name() and len(self.view.file_name()) > 0:
            return bool(git_root(self.get_working_dir()))
        return False

    def get_file_name(self):
        return os.path.basename(self.view.file_name())

    def get_relative_file_name(self):
        working_dir = self.get_working_dir()
        file_path = working_dir.replace(git_root(working_dir), '')[1:]
        file_name = os.path.join(file_path, self.get_file_name())
        return file_name.replace('\\', '/')  # windows issues

    def get_working_dir(self):
        file_name = self.view.file_name()
        if file_name:
            return os.path.realpath(os.path.dirname(file_name))
        return ''

    def get_window(self):
        # Fun discovery: if you switch tabs while a command is working,
        # self.view.window() is None. (Admittedly this is a consequence
        # of my deciding to do async command processing... but, hey,
        # got to live with that now.)
        # I did try tracking the window used at the start of the command
        # and using it instead of view.window() later, but that results
        # panels on a non-visible window, which is especially useless in
        # the case of the quick panel.
        # So, this is not necessarily ideal, but it does work.
        return self.view.window() or sublime.active_window()
