import commands, os
# importing actual sublime code
import sublime, sublime_plugin

from git import GitWindowCommand, git_root
# defining command here, command will be git_grep
class GitGrepCommand(GitWindowCommand):
  # init, setup some default object properties
  def __init__(self, window):
    self.last_query = ''
    self.last_ignore = 'vendor'
    self.last_subdir = '.'
    # http://docs.python.org/library/functions.html#hasattr
    if hasattr(sublime_plugin.WindowCommand, '__init__'):
            sublime_plugin.WindowCommand.__init__(self, window)

  # this is first executed with window.run_command("git_grep") or key shortcut
  def run(self):
    self.window.show_input_panel('git grep', self.last_query, self.on_grep_done, self.on_change, self.on_cancel)
  def on_grep_done(self,query):
    self.last_query = query
    self.window.show_input_panel('ignore files(use | to specify more)', self.last_ignore, self.on_subdir_done, self.on_change, self.on_cancel)
  def on_subdir_done(self,ignore):
    self.last_ignore = ignore
    self.window.show_input_panel('subdirs to search', self.last_subdir, self.on_done, self.on_change, self.on_cancel)

  def on_done(self, subdir):
    self.last_subdir = subdir
    # git grep options used, -I skip binary files, -i ignore case, -n return numbers
    print 'git grep --full-name -Iin "%s" "%s/%s"|grep -Ev "%s"' % (self.last_query, git_root(self.get_working_dir()),self.last_subdir, self.last_ignore)
    status, out = commands.getstatusoutput('git grep --full-name -Iin "%s" "%s/%s"|grep -Ev "%s"' % (self.last_query, git_root(self.get_working_dir()),self.last_subdir, self.last_ignore))

    # decod utf 8 and split to line array
    self.out_list = out.decode('ascii', 'ignore').split("\n")
    print self.out_list
    if(self.out_list==[""]):
      sublime.message_dialog("""Can't find "%s" \n in git repo based in: %s\n """ % (query, git_root(self.get_working_dir()) ))
      return

    def split(l):
        # split line on 3 parts, what if I have : in actual line?
        # problem here, if nothing returned from git grep, I can't split empty line on 3 parts
        # Return a list of the words in the string, using sep as the delimiter string.
        # If maxsplit is given, at most maxsplit splits are done (thus, the list will have at most maxsplit+1 elements).
        fname, line, match = l.split(":", 2)
        return [match.strip()[0:100], ":".join([fname, line])]
    # http://docs.python.org/library/functions.html#map
    # Apply function to every item of iterable and return a list of the results.
    items = map(split, self.out_list)
    print items
    # sublime function show_quick_panel(items, on_done, <flags>)
    self.window.show_quick_panel(items, self.on_done_sel)
  def on_change(self, arg):
        return
  def on_cancel(self):
        return
  def on_done_sel(self,index):
      if index == -1:
          return
      # out list we already parsed in on_done
      line = self.out_list[index]
      filename, lineno, match = line.split(":", 2)

      path = git_root(self.get_working_dir())
      self.window.open_file(os.path.join(path, filename) + ':' + lineno, sublime.ENCODED_POSITION)