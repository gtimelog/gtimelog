#!/usr/bin/python
"""
A Gtk+ application for keeping track of time.
"""

import re
import os
import datetime
import tempfile
import gobject
import gtk
import gtk.glade


virtual_midnight = datetime.time(2, 0)


def format_duration(duration):
    """Format a datetime.timedelta with minute precision."""
    h, m = divmod((duration.days * 24 * 60 + duration.seconds // 60), 60)
    return '%d h %d min' % (h, m)


def format_duration_long(duration):
    """Format a datetime.timedelta with minute precision, long format."""
    h, m = divmod((duration.days * 24 * 60 + duration.seconds // 60), 60)
    if h and m:
        return '%d hour%s %d min' % (h, h != 1 and "s" or "", m)
    elif h:
        return '%d hour%s' % (h, h != 1 and "s" or "")
    else:
        return '%d min' % m


def parse_datetime(dt):
    """Parse a datetime instance from 'YYYY-MM-DD HH:MM' formatted string."""
    m = re.match(r'^(\d+)-(\d+)-(\d+) (\d+):(\d+)$', dt)
    if not m:
        raise ValueError('bad date time: ', dt)
    year, month, day, hour, min = map(int, m.groups())
    return datetime.datetime(year, month, day, hour, min)


def virtual_day(dt):
    if dt.time() < virtual_midnight:     # assign to previous day
        return dt.date() - datetime.timedelta(1)
    return dt.date()


def different_days(dt1, dt2):
    return virtual_day(dt1) != virtual_day(dt2)


class TimeLog(object):
    """Time log."""

    def __init__(self, filename):
        self.filename = filename
        self.items = []
        self.history = []
        self.read_today()
        self.need_space = False

    def read_today(self):
        today = datetime.date.today()
        min = datetime.datetime.combine(today, virtual_midnight)
        max = min + datetime.timedelta(1)
        try:
            f = open(self.filename)
        except IOError:
            return
        line = ''
        for line in f:
            if ': ' not in line:
                continue
            time, entry = line.split(': ', 1)
            try:
                time = parse_datetime(time)
            except ValueError:
                continue
            else:
                entry = entry.strip()
                self.history.append(entry)
                if min <= time < max:
                    self.items.append((time, entry))
        self.need_space = not line.strip()
        f.close()

    def raw_append(self, line):
        f = open(self.filename, "a")
        if self.need_space:
            self.need_space = False
            print >> f
        print >> f, line
        f.close()

    def append(self, entry):
        now = datetime.datetime.now()
        last = self.last_time()
        if last and different_days(now, last):
            self.need_space = True
        self.items.append((now, entry))
        line = '%s: %s' % (now.strftime("%Y-%m-%d %H:%M"), entry)
        self.raw_append(line)
        return now

    def last_time(self):
        if not self.items:
            return None
        return self.items[-1][0]

    def all_items(self):
        stop = None
        for item in self.items:
            start = stop
            stop = item[0].replace(second=0, microsecond=0)
            entry = item[1]
            if start is None:
                start = stop
            duration = stop - start
            yield start, stop, duration, entry

    def grouped(self, skip_first=True):
        work = {}
        slack = {}
        for start, stop, duration, entry in self.all_items():
            if skip_first:
                skip_first = False
                continue
            if '**' in entry:
                entries = slack
            else:
                entries = work
            if entry in entries:
                old_start, old_entry, old_duration = entries[entry]
                start = min(start, old_start)
                duration += old_duration
            entries[entry] = (start, entry, duration)
        work = work.values()
        work.sort()
        slack = slack.values()
        slack.sort()
        return work, slack

    def last_item(self):
        if not self.items:
            return None
        stop = self.items[-1][0].replace(second=0, microsecond=0)
        entry = self.items[-1][1]
        if len(self.items) == 1:
            start = stop
        else:
            start = self.items[-2][0].replace(second=0, microsecond=0)
        duration = stop - start
        return start, stop, duration, entry

    def totals(self):
        total_work = total_slacking = datetime.timedelta(0)
        for start, stop, duration, entry in self.all_items():
            if '**' in entry:
                total_slacking += duration
            else:
                total_work += duration
        return total_work, total_slacking

    def daily_report(self, output):
        weekday = datetime.date.today().strftime('%A')
        week = datetime.date.today().strftime('%V')
        print >> output, "To: activity@pov.lt"
        print >> output, "Subject: %s report for Marius (week %s)" % (weekday,
                                                                      week)
        print >> output
        items = list(self.all_items())
        if not items:
            print >> output, "No work done today."
            return
        start, stop, duration, entry = items[0]
        entry = entry[:1].upper() + entry[1:]
        print >> output, "%s at %s" % (entry, start.strftime('%H:%M'))
        print >> output
        work, slack = self.grouped()
        total_work, total_slacking = self.totals()
        if work:
            for start, entry, duration in work:
                entry = entry[:1].upper() + entry[1:]
                print >> output, "%-62s  %s" % (entry,
                                                format_duration_long(duration))
            print >> output
        print >> output, "Total work done: %s" % format_duration_long(total_work)
        print >> output
        if slack:
            for start, entry, duration in slack:
                entry = entry[:1].upper() + entry[1:]
                print >> output, "%-62s  %s" % (entry,
                                                format_duration_long(duration))
            print >> output
        print >> output, "Time spent slacking: %s" % format_duration_long(total_slacking)
        print >> output
        now = datetime.datetime.now().strftime('%H:%M')
        print >> output, "Time now: %s" % now


class MainWindow(object):
    """Main application window."""

    chronological = True
    footer_mark = None

    # Try to prevent timer routines mucking with the buffer while we're
    # mucking with the buffer.  Not sure if it is necessary.
    lock = False

    def __init__(self, timelog):
        """Create the main window."""
        self.timelog = timelog
        tree = gtk.glade.XML("gtimelog.glade")
        tree.signal_autoconnect(self)
        self.about_dialog = tree.get_widget("about_dialog")
        self.about_dialog_ok_btn = tree.get_widget("ok_button")
        self.about_dialog_ok_btn.connect("clicked", self.close_about_dialog)
        main_window = tree.get_widget("main_window")
        main_window.connect("delete_event", self.delete_event)
        self.log_view = tree.get_widget("log_view")
        self.time_label = tree.get_widget("time_label")
        self.task_entry = tree.get_widget("task_entry")
        self.task_entry.connect("changed", self.task_entry_changed)
        self.task_entry.connect("key_press_event", self.task_entry_key_press)
        self.add_button = tree.get_widget("add_button")
        self.add_button.connect("clicked", self.add_entry)
        buffer = self.log_view.get_buffer()
        self.log_buffer = buffer
        buffer.create_tag('today', foreground='blue')
        buffer.create_tag('duration', foreground='red')
        buffer.create_tag('time', foreground='green')
        buffer.create_tag('slacking', foreground='gray')
        self.set_up_history()
        self.set_up_completion()
        self.populate_log()
        self.tick()
        gobject.timeout_add(1000, self.tick)

    def w(self, text, tag=None):
        """Write some text at the end of the log buffer."""
        buffer = self.log_buffer
        if tag:
            buffer.insert_with_tags_by_name(buffer.get_end_iter(), text, tag)
        else:
            buffer.insert(buffer.get_end_iter(), text)

    def populate_log(self):
        """Populate the log."""
        self.lock = True
        buffer = self.log_buffer
        buffer.set_text("")
        if self.footer_mark is not None:
            buffer.delete_mark(self.footer_mark)
            self.footer_mark = None
        today = datetime.date.today().strftime('%A, %Y-%m-%d (week %V)')
        self.w(today + '\n\n', 'today')
        if self.chronological:
            for item in self.timelog.all_items():
                self.write_item(item)
        else:
            work, slack = self.timelog.grouped()
            for start, entry, duration in work + slack:
                self.write_group(entry, duration)
            where = buffer.get_end_iter()
            where.backward_cursor_position()
            buffer.place_cursor(where)
        self.add_footer()
        self.scroll_to_end()
        self.lock = False

    def delete_footer(self):
        buffer = self.log_buffer
        buffer.delete(buffer.get_iter_at_mark(self.footer_mark),
                      buffer.get_end_iter())
        buffer.delete_mark(self.footer_mark)
        self.footer_mark = None

    def add_footer(self):
        buffer = self.log_buffer
        self.footer_mark = buffer.create_mark('footer', buffer.get_end_iter(),
                                              gtk.TRUE)
        total_work, total_slacking = self.timelog.totals()
        self.w('\n')
        self.w('Total work done: ')
        self.w(format_duration(total_work), 'duration')
        self.w('\n')
        self.w('Total slacking: ')
        self.w(format_duration(total_slacking), 'duration')
        self.w('\n')
        last_time = self.timelog.last_time()
        if last_time is not None:
            now = datetime.datetime.now()
            current_task = self.task_entry.get_text()
            current_task_time = now - last_time
            if '**' in current_task:
                total_time = total_work
            else:
                total_time = total_work + current_task_time
            time_left = datetime.timedelta(hours=8) - total_time
            time_to_leave = now + time_left
            if time_left < datetime.timedelta(0):
                time_left = datetime.timedelta(0)
            self.w('Time left at work: ')
            self.w(format_duration(time_left), 'duration')
            self.w(' (till ')
            self.w(time_to_leave.strftime('%H:%M'), 'time')
            self.w(')')

    def write_item(self, item):
        buffer = self.log_buffer
        start, stop, duration, entry = item
        self.w(format_duration(duration), 'duration')
        period = '\t(%s-%s)\t' % (start.strftime('%H:%M'),
                                  stop.strftime('%H:%M'))
        self.w(period, 'time')
        tag = '**' in entry and 'slacking' or None
        self.w(entry + '\n', tag)
        where = buffer.get_end_iter()
        where.backward_cursor_position()
        buffer.place_cursor(where)

    def write_group(self, entry, duration):
        self.w(format_duration(duration), 'duration')
        tag = '**' in entry and 'slacking' or None
        self.w('\t' + entry + '\n', tag)

    def scroll_to_end(self):
        buffer = self.log_view.get_buffer()
        end_mark = buffer.create_mark('end', buffer.get_end_iter())
        self.log_view.scroll_to_mark(end_mark, 0)
        buffer.delete_mark(end_mark)

    def set_up_history(self):
        """Set up history."""
        self.history = self.timelog.history
        self.filtered_history = []
        self.history_pos = 0
        self.history_undo = ''

    def set_up_completion(self):
        """Set up autocompletion."""
        self.have_completion = hasattr(gtk, 'EntryCompletion')
        if not self.have_completion:
            return
        self.completion_choices = gtk.ListStore(str)
        completion = gtk.EntryCompletion()
        completion.set_model(self.completion_choices)
        completion.set_text_column(0)
        self.task_entry.set_completion(completion)

    def add_history(self, entry):
        """Add an entry to history."""
        self.history.append(entry)
        self.history_pos = 0
        if not self.have_completion:
            return
        if entry not in [row[0] for row in self.completion_choices]:
            self.completion_choices.append([entry])

    def delete_event(self, widget, data=None):
        """Try to close the window."""
        gtk.main_quit()
        return gtk.FALSE

    def close_about_dialog(self, widget):
        """Ok clicked in the about dialog."""
        self.about_dialog.hide()

    def on_quit_activate(self, widget):
        """File -> Quit selected"""
        gtk.main_quit()

    def on_about_activate(self, widget):
        """Help -> About selected"""
        self.about_dialog.show()

    def on_chronological_activate(self, widget):
        """View -> Chronological"""
        self.chronological = True
        self.populate_log()

    def on_grouped_activate(self, widget):
        """View -> Grouped"""
        self.chronological = False
        self.populate_log()

    def on_daily_report_activate(self, widget):
        """File -> Daily Report"""
        draftfn = tempfile.mktemp(suffix='gtimelog') # XXX
        draft = open(draftfn, 'w')
        self.timelog.daily_report(draft)
        draft.close()
        os.system("x-terminal-emulator -e mutt -H %s &" % draftfn)
        # XXX rm draftfn when done

    def task_entry_changed(self, widget):
        """Reset history position when the task entry is changed."""
        self.history_pos = 0

    def task_entry_key_press(self, widget, event):
        """Handle key presses in task entry."""
        if event.keyval == gtk.gdk.keyval_from_name('Up'):
            self._do_history(1)
            return gtk.TRUE
        if event.keyval == gtk.gdk.keyval_from_name('Down'):
            self._do_history(-1)
            return gtk.TRUE
        return gtk.FALSE

    def _do_history(self, delta):
        """Handle movement in history."""
        if not self.history:
            return
        if self.history_pos == 0:
            self.history_undo = self.task_entry.get_text()
            self.filtered_history = [l for l in self.history
                                     if l.startswith(self.history_undo)]
        history = self.filtered_history
        new_pos = max(0, min(self.history_pos + delta, len(history)))
        if new_pos == 0:
            self.task_entry.set_text(self.history_undo)
            self.task_entry.set_position(-1)
        else:
            self.task_entry.set_text(history[-new_pos])
            self.task_entry.select_region(0, -1)
        # Do this after task_entry_changed reset history_pos to 0
        self.history_pos = new_pos

    def add_entry(self, widget, data=None):
        """Add the task entry to the log."""
        entry = self.task_entry.get_text()
        if not entry:
            return
        self.add_history(entry)
        self.timelog.append(entry)
        if self.chronological:
            self.delete_footer()
            self.write_item(self.timelog.last_item())
            self.add_footer()
            self.scroll_to_end()
        else:
            self.populate_log()
        self.task_entry.set_text("")
        self.task_entry.grab_focus()

    def tick(self):
        """Tick every second."""
        now = datetime.datetime.now()
        last_time = self.timelog.last_time()
        if last_time is None:
            self.time_label.set_text(now.strftime("%H:%M"))
        else:
            self.time_label.set_text(format_duration(now - last_time))
            # Update "time left to work"
            if not self.lock:
                self.delete_footer()
                self.add_footer()
        return gtk.TRUE


def main():
    """Run the program."""
    timelog = TimeLog('timelog.txt')
    main_window = MainWindow(timelog)
    try:
        gtk.main()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
