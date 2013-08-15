import sublime, sublime_plugin

import functools, threading

class Progress():

	def __init__(self, thread, message, message_done):
		self.thread = thread
		self.message = message
		self.message_done = message_done
		self.add = 1
		self.size = 8
		sublime.set_timeout(lambda: self.run(0), 100)

	def run(self, i):
		if not self.thread.is_alive():
			sublime.status_message(self.message_done)
			return

		before = i % self.size
		after = self.size - (before + 1)

		if not after:
			self.add = -1
		elif not before:
			self.add = 1

		sublime.status_message('%s [%s=%s]' % (self.message, ' ' * before, ' ' * after))
		sublime.set_timeout(lambda: self.run(i+self.add), 100)
