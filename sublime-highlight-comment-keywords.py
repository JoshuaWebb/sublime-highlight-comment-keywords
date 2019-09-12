import sublime
import sublime_plugin
import logging
import re
from threading import Timer

DEFAULT_LOG_LEVEL = logging.INFO
l = logging.getLogger(__name__)

PLUGIN_KEY = 'HighlightCommentKeywords'

# TODO: find out if there's a limit on the length of an region_key
REGION_KEY_PREFIX = PLUGIN_KEY
KEYWORD_PAIRS_KEY = 'highlight_comment_keywords'
ENABLED_SETTING_KEY = 'highlight_comment_keywords_enabled'

PREVIOUS_KEYWORDS_PER_VIEW = {}

class ToggleHighlightCommentKeywords(sublime_plugin.TextCommand):
	def run(self, edit):
		_toggle_view_setting(self.view, ENABLED_SETTING_KEY);

def _toggle_view_setting(view, setting):
	settings = view.settings()
	value = settings.get(setting)
	settings.set(setting, not value)

def highlight_keywords(view):
	l.debug(str(view.id()) + ' highlight_keywords')
	pairs = view.settings().get(KEYWORD_PAIRS_KEY, {})
	enabled = view.settings().get(ENABLED_SETTING_KEY, False)

	# We need to clear out all the highlighted regions once.
	if(not enabled):
		pairs = {}

	# Unhighlight any regions for keywords that have been removed
	previous_keywords = PREVIOUS_KEYWORDS_PER_VIEW.setdefault(view.id(), set())
	removed_keywords = [k for k in previous_keywords - set(pairs.keys())]
	for keyword in removed_keywords:
		l.debug(str(view.id()) + ': ' 'Removed keyword: ' + keyword)
		region_key = REGION_KEY_PREFIX + keyword
		view.erase_regions(region_key)

	previous_keywords.clear()
	if(not enabled):
		return

	for keyword, scope in pairs.items():
		previous_keywords.add(keyword)
		region_key = REGION_KEY_PREFIX + keyword

		keyword_matches = view.find_all('\\b' + re.escape(keyword) + '\\b')
		comment_keyword_matches = [r for r in keyword_matches if 'comment' in view.scope_name(r.a)]

		# NOTE: This overrides existing regions so we don't need to clear them first.
		view.add_regions(region_key, comment_keyword_matches, scope, '', sublime.DRAW_EMPTY)

class HighlightCommentKeywords(sublime_plugin.EventListener):
	delay_in_seconds = 1
	registered_views = set()

	def __init__(self):
		self.timer = None
		self.regions = None

	def on_modified_async(self, view):
		if self.timer is not None:
			self.timer.cancel()

		self.timer = Timer(self.delay_in_seconds, highlight_keywords, [view])
		self.timer.start()

	def on_activated_async(self, view):
		if view.id() not in self.registered_views:
			l.debug('registering ' + str(view.id()))
			settings = view.settings()
			settings.clear_on_change(PLUGIN_KEY)
			settings.add_on_change(PLUGIN_KEY, lambda: highlight_keywords(view))
			self.registered_views.add(view.id())

		highlight_keywords(view)

	def on_pre_close(self, view):
		l.debug('removing view ' + str(view.id()))
		self.registered_views.remove(view.id())

	def on_load_async(self, view):
		highlight_keywords(view)

def plugin_loaded():
	pl = logging.getLogger(__package__)
	for handler in pl.handlers[:]:
		pl.removeHandler(handler)

	handler = logging.StreamHandler()
	formatter = logging.Formatter(fmt="{asctime} [{name}] {levelname}: {message}",
								  style='{')
	handler.setFormatter(formatter)
	pl.addHandler(handler)

	pl.setLevel(DEFAULT_LOG_LEVEL)
	l.debug('plugin_loaded')
