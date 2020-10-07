from gi.repository import Gdk, GObject, Gtk

from gtimelog.core.utils import mark_time, uniq


class TaskEntry(Gtk.Entry):

    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    completion_limit = GObject.Property(
        type=int, default=1000, nick='Completion limit',
        blurb='Maximum number of items in the completion popup')

    gtk_completion_enabled = GObject.Property(
        type=bool, default=True, nick='Completion enabled',
        blurb='GTK+ completion enabled?')

    def __init__(self):
        Gtk.Entry.__init__(self)
        self.history = []
        self.filtered_history = []
        self.history_pos = 0
        self.history_undo = ''
        completion = self.gtk_completion = Gtk.EntryCompletion()
        self.completion_choices = Gtk.ListStore(str)
        self.completion_choices_as_set = set()
        completion.set_model(self.completion_choices)
        completion.set_text_column(0)
        if self.gtk_completion_enabled:
            self.set_completion(completion)
        self.connect('notify::timelog', self.timelog_changed)
        self.connect('notify::completion-limit', self.timelog_changed)
        self.connect('changed', self.on_changed)
        self.connect('notify::gtk-completion-enabled', self.gtk_completion_enabled_changed)

    def gtk_completion_enabled_changed(self, *args):
        if self.gtk_completion_enabled:
            self.set_completion(self.gtk_completion)
        else:
            self.set_completion(None)

    def timelog_changed(self, *args):
        mark_time('about to initialize history completion')
        self.completion_choices_as_set.clear()
        self.completion_choices.clear()
        if self.timelog is None:
            mark_time('no history')
            return
        self.history = [item[1] for item in self.timelog.items]
        mark_time('history prepared')
        # if there are duplicate entries, we want to keep the last one
        # e.g. if timelog.items contains [a, b, a, c], we want
        # self.completion_choices to be [b, a, c].
        entries = []
        for entry in reversed(self.history):
            if entry not in self.completion_choices_as_set:
                entries.append(entry)
                self.completion_choices_as_set.add(entry)
        mark_time('unique items selected')
        for entry in reversed(entries[:self.completion_limit]):
            self.completion_choices.append([entry])
        mark_time('history completion initialized')

    def entry_added(self):
        if self.timelog is None:
            return
        entry = self.timelog.last_entry().entry
        self.history.append(entry)
        self.history_pos = 0
        if entry not in self.completion_choices_as_set:
            self.completion_choices.append([entry])
            self.completion_choices_as_set.add(entry)

    def on_changed(self, widget):
        self.history_pos = 0

    def do_key_press_event(self, event):
        if event.keyval == Gdk.keyval_from_name('Prior'):
            self._do_history(1)
            return True
        if event.keyval == Gdk.keyval_from_name('Next'):
            self._do_history(-1)
            return True
        return Gtk.Entry.do_key_press_event(self, event)

    def _do_history(self, delta):
        """Handle movement in history."""
        if not self.history:
            return
        if self.history_pos == 0:
            self.history_undo = self.get_text()
            self.filtered_history = uniq([
                entry for entry in self.history
                if entry.startswith(self.history_undo)
            ])
        history = self.filtered_history
        new_pos = max(0, min(self.history_pos + delta, len(history)))
        if new_pos == 0:
            self.set_text(self.history_undo)
            self.set_position(-1)
        else:
            self.set_text(history[-new_pos])
            self.select_region(len(self.history_undo), -1)
        # Do this after on_changed reset history_pos to 0
        self.history_pos = new_pos
