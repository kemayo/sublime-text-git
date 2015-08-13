import os
import sublime
import sublime_plugin
import threading
import subprocess
import functools
import os.path
import time

# In a complete inversion from ST2, in ST3 when a plugin is loaded we
# actually can trust __file__.
# Goal is to get: "Packages/Git", allowing for people who rename things

git_root_cache = {}

def find_plugin_directory(f):
    dirname = os.path.split(os.path.dirname(f))[-1]
    return "Packages/" + dirname.replace(".sublime-package", "")
PLUGIN_DIRECTORY = find_plugin_directory(__file__)


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
def find_git():
    # It turns out to be difficult to reliably run git, with varying paths
    # and subprocess environments across different platforms. So. Let's hack
    # this a bit.
    # (Yes, I could fall back on a hardline "set your system path properly"
    # attitude. But that involves a lot more arguing with people.)
    path = os.environ.get('PATH', '').split(os.pathsep)
    if os.name == 'nt':
        git_cmd = 'git.exe'
    else:
        git_cmd = 'git'

    git_path = _test_paths_for_executable(path, git_cmd)

    if not git_path:
        # /usr/local/bin:/usr/local/git/bin
        if os.name == 'nt':
            extra_paths = (
                os.path.join(os.environ["ProgramFiles"], "Git", "bin"),
                os.path.join(os.environ["ProgramFiles(x86)"], "Git", "bin"),
            )
        else:
            extra_paths = (
                '/usr/local/bin',
                '/usr/local/git/bin',
            )
        git_path = _test_paths_for_executable(extra_paths, git_cmd)
    return git_path
GIT = find_git()

commands_working = 0
def are_commands_working():
    return commands_working != 0

class CommandThread(threading.Thread):
    def __init__(self, command, on_done, max_tries, working_dir="", fallback_encoding="", **kwargs):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.max_tries = max_tries
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
        self.kwargs = kwargs

    def run(self):
        global commands_working
        # Ignore directories that no longer exist
        if not os.path.isdir(self.working_dir):
            return

        commands_working = commands_working + 1
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

            shell = False
            if sublime.platform() == 'windows':
                shell = True

            env = os.environ.copy()
            if sublime.platform() == 'windows' and 'HOME' not in env:
                env['HOME'] = env['USERPROFILE']

            returncode = 128
            tries = 0
            while returncode == 128 and tries < self.max_tries:
                if tries > 0:
                    print("retrying", self.command, tries)
                # universal_newlines seems to break `log` in python3
                proc = subprocess.Popen(self.command,
                    stdout=self.stdout, stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE, startupinfo=startupinfo,
                    shell=shell, universal_newlines=False,
                    env=env)
                output = proc.communicate(self.stdin)[0]
                returncode = proc.returncode
                tries += 1

            if not output:
                output = ''
            output = _make_text_safeish(output, self.fallback_encoding)
        except subprocess.CalledProcessError as e:
            output = e.returncode
        except OSError as e:
            callback = sublime.error_message
            if e.errno == 2:
                output = "Git binary could not be found in PATH\n\nConsider using the git_command setting for the Git plugin\n\nPATH is: %s" % os.environ['PATH']
            else:
                output = e.strerror
        finally:
            commands_working = commands_working - 1
            main_thread(callback, output, **self.kwargs)

class GitScratchOutputCommand(sublime_plugin.TextCommand):
    def run(self, edit, output = '', output_file = None, clear = False):
        if clear:
            region = sublime.Region(0, self.view.size())
            self.view.erase(edit, region)
        self.view.insert(edit, 0, output)


# A base for all commands
class GitCommand(object):
    may_change_files = False
    max_tries = 5

    def run_command(self, command, callback=None, show_status=True,
            filter_empty_args=True, no_save=False, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_working_dir()
        if 'fallback_encoding' not in kwargs and self.active_view() and self.active_view().settings().get('fallback_encoding'):
            kwargs['fallback_encoding'] = self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

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
            command[0] = s.get('gitk_command')
        if command[0] == 'git-flow' and s.get('git_flow_command'):
            command[0] = s.get('git_flow_command')
        if not callback:
            callback = self.generic_done

        thread = CommandThread(command, callback, self.max_tries, **kwargs)
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
            self.view.run_command('git_annotate')

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

    def scratch(self, output, title=False, position=None, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        if position:
            sublime.set_timeout(lambda: scratch_file.set_viewport_position(position), 0)
        return scratch_file

    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().get_output_panel("git")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.get_window().run_command("show_panel", {"panel": "output.git"})

    def quick_panel(self, *args, **kwargs):
        self.get_window().show_quick_panel(*args, **kwargs)


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
        else:
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
        return os.path.realpath(os.path.dirname(self.view.file_name()))

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


# A few miscellaneous commands


class GitCustomCommand(GitWindowCommand):
    may_change_files = True

    def run(self):
        self.get_window().show_input_panel("Git command", "",
            self.on_input, None, None)

    def on_input(self, command):
        command = str(command)  # avoiding unicode
        if command.strip() == "":
            self.panel("No git command provided")
            return
        import shlex
        command_splitted = ['git'] + shlex.split(command)
        print(command_splitted)
        self.run_command(command_splitted)


class GitRawCommand(GitWindowCommand):
    may_change_files = True

    def run(self, **args):
        self.command = str(args.get('command', ''))
        show_in = str(args.get('show_in', 'pane_below'))

        if self.command.strip() == "":
            self.panel("No git command provided")
            return
        import shlex
        command_split = shlex.split(self.command)

        if args.get('append_current_file', False) and self._active_file_name():
            command_split.extend(('--', self._active_file_name()))

        print(command_split)

        self.may_change_files = bool(args.get('may_change_files', True))

        if show_in == 'pane_below':
            self.run_command(command_split)
        elif show_in == 'quick_panel':
            self.run_command(command_split, self.show_in_quick_panel)
        elif show_in == 'new_tab':
            self.run_command(command_split, self.show_in_new_tab)
        elif show_in == 'suppress':
            self.run_command(command_split, self.do_nothing)

    def show_in_quick_panel(self, result):
        self.results = list(result.rstrip().split('\n'))
        if len(self.results):
            self.quick_panel(self.results,
                self.do_nothing, sublime.MONOSPACE_FONT)
        else:
            sublime.status_message("Nothing to show")

    def do_nothing(self, picked):
        return

    def show_in_new_tab(self, result):
        msg = self.window.new_file()
        msg.set_scratch(True)
        msg.set_name(self.command)
        self._output_to_view(msg, result)
        msg.sel().clear()
        msg.sel().add(sublime.Region(0, 0))


class GitGuiCommand(GitTextCommand):
    def run(self, edit):
        command = ['git', 'gui']
        self.run_command(command)


class GitGitkCommand(GitTextCommand):
    def run(self, edit):
        command = ['gitk']
        self.run_command(command)


class GitUpdateIgnoreCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        data = self.view.window().project_data()
        project_file_name = self.view.window().project_file_name()
        for folder in data['folders']:
            path = folder['path']
            if project_file_name:
                path = os.path.join(os.path.dirname(project_file_name), path)
            gitignore = os.path.join(path, ".gitignore")
            print("gitignore path", gitignore)
            if (os.path.exists(gitignore)):
                with open(gitignore) as gitignore_file:
                    if not "folder_exclude_patterns" in folder:
                        folder["folder_exclude_patterns"] = []
                    if not "file_exclude_patterns" in folder:
                        folder["file_exclude_patterns"] = []
                    for pattern in gitignore_file:
                        pattern = pattern.strip()
                        if os.path.isdir(os.path.join(path, pattern)):
                            if not pattern in folder["folder_exclude_patterns"]:
                                folder["folder_exclude_patterns"].append(pattern)
                        else:
                            if not pattern in folder["file_exclude_patterns"]:
                                folder["file_exclude_patterns"].append(pattern)
        self.view.window().set_project_data(data)
