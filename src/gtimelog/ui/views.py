import datetime
import re
from gettext import gettext as _
from io import StringIO

from gi.repository import GLib, GObject, Gtk, Pango

from gtimelog.core.reports import ReportRecord, Reports
from gtimelog.core.settings import Settings
from gtimelog.core.utils import different_days
from gtimelog.main import mark_time
from gtimelog.ui.utils import REPORT_KINDS, internationalised_format_duration


class LogView(Gtk.TextView):
    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    date = GObject.Property(
        type=object, default=None, nick='Date',
        blurb='Date to show (None tracks today)')

    showing_today = GObject.Property(
        type=bool, default=True, nick='Showing today',
        blurb='Currently visible time range includes today')

    detail_level = GObject.Property(
        type=str, default='chronological', nick='Detail level',
        blurb='Detail level to show (chronological/grouped/summary)')

    time_range = GObject.Property(
        type=str, default='day', nick='Time range',
        blurb='Time range to show (day/week/month)')

    hours = GObject.Property(
        type=float, default=0, nick='Hours',
        blurb='Target number of work hours per day')

    office_hours = GObject.Property(
        type=float, default=0, nick='Office Hours',
        blurb='Target number of office hours per day')

    current_task = GObject.Property(
        type=str, nick='Current task',
        blurb='Current task in progress')

    now = GObject.Property(
        type=object, default=None, nick='Now',
        blurb='Current date and time')

    filter_text = GObject.Property(
        type=str, default='', nick='Filter text',
        blurb='Show only tasks matching this substring')

    def __init__(self):
        Gtk.TextView.__init__(self)
        self._extended_footer = False
        self._footer_mark = None
        self._update_pending = False
        self._footer_update_pending = False
        self.set_up_tabs()
        self.set_up_tags()
        self.connect('notify::timelog', self.queue_update)
        self.connect('notify::date', self.queue_update)
        self.connect('notify::showing-today', self.queue_update)
        self.connect('notify::detail-level', self.queue_update)
        self.connect('notify::time-range', self.queue_update)
        self.connect('notify::hours', self.queue_footer_update)
        self.connect('notify::office-hours', self.queue_footer_update)
        self.connect('notify::current-task', self.queue_footer_update)
        self.connect('notify::now', self.queue_footer_update)
        self.connect('notify::filter-text', self.queue_update)

    def queue_update(self, *args):
        if not self._update_pending:
            self._update_pending = True
            GLib.idle_add(self.populate_log)

    def queue_footer_update(self, *args):
        if not self._footer_update_pending:
            self._footer_update_pending = True
            GLib.idle_add(self.update_footer)

    def set_up_tabs(self):
        pango_context = self.get_pango_context()
        em = pango_context.get_font_description().get_size()
        tabs = Pango.TabArray.new(2, False)
        tabs.set_tab(0, Pango.TabAlign.LEFT, 9 * em)
        tabs.set_tab(1, Pango.TabAlign.LEFT, 12.5 * em)
        self.set_tabs(tabs)

    def set_up_tags(self):
        buffer = self.get_buffer()
        buffer.create_tag('today', foreground='#204a87')  # Tango dark blue
        buffer.create_tag('duration', foreground='#ce5c00')  # Tango dark orange
        buffer.create_tag('time', foreground='#4e9a06')  # Tango dark green
        buffer.create_tag('highlight', foreground='#4e9a06')  # Tango dark green
        buffer.create_tag('slacking', foreground='gray')

    def get_time_window(self):
        assert self.timelog is not None
        if self.time_range == 'day':
            return self.timelog.window_for_day(self.date)
        elif self.time_range == 'week':
            return self.timelog.window_for_week(self.date)
        elif self.time_range == 'month':
            return self.timelog.window_for_month(self.date)

    def get_last_time(self):
        assert self.timelog is not None
        return self.timelog.window.last_time()

    def get_current_task_time(self):
        last_time = self.get_last_time()
        if last_time is None:
            return datetime.timedelta(0)
        else:
            return self.now - last_time

    def get_current_task_work_time(self):
        if '**' in self.current_task:
            return datetime.timedelta(0)
        else:
            return self.get_current_task_time()

    def time_left_at_work(self, total_work):
        total_time = total_work + self.get_current_task_work_time()
        return datetime.timedelta(hours=self.hours) - total_time

    def populate_log(self):
        self._update_pending = False
        self.get_buffer().set_text('')
        if self.timelog is None:
            return  # not loaded yet
        window = self.get_time_window()
        total = datetime.timedelta(0)
        if self.detail_level == 'chronological':
            prev = None
            for item in window.all_entries():
                first_of_day = prev is None or different_days(prev, item.start, self.timelog.virtual_midnight)
                if first_of_day and prev is not None:
                    self.w("\n")
                if self.time_range != 'day' and first_of_day:
                    self.w(_("{0:%A, %Y-%m-%d}\n").format(item.start))
                if self.filter_text in item.entry:
                    self.write_item(item)
                    total += item.duration
                prev = item.start
        elif self.detail_level == 'grouped':
            work, slack = window.grouped_entries()
            for start, entry, duration in work + slack:
                if self.filter_text in entry:
                    self.write_group(entry, duration)
                    total += duration
        elif self.detail_level == 'summary':
            entries, totals = window.categorized_work_entries()
            no_cat = totals.pop(None, None)
            categories = sorted(totals.items())
            if no_cat is not None:
                categories = [('no category', no_cat)] + categories
            for category, duration in categories:
                if self.filter_text in category:
                    self.write_group(category, duration)
                    total += duration
        else:
            return  # bug!
        if self.filter_text:
            self.w('\n')
            args = [
                (self.filter_text, 'highlight'),
                (internationalised_format_duration(total), 'duration'),
            ]
            if self.time_range != 'day':
                work_days = window.count_days() or 1
                per_diem = total / work_days
                args.append((internationalised_format_duration(per_diem), 'duration'))
                self.wfmt(_('Total for {0}: {1} ({2} per day)'), *args)
            else:
                weekly_window = self.timelog.window_for_week(self.date)
                work_days_in_week = weekly_window.count_days() or 1
                week_work, week_slacking = weekly_window.totals(
                    filter_text=self.filter_text)
                week_total = week_work + week_slacking
                args.append((internationalised_format_duration(week_total), 'duration'))
                per_diem = week_total / work_days_in_week
                args.append((internationalised_format_duration(per_diem), 'duration'))
                self.wfmt(_('Total for {0}: {1} ({2} this week, {3} per day)'), *args)
            self.w('\n')
        self.reposition_cursor()
        self.add_footer()
        self.scroll_to_end()

    def entry_added(self, same_day):
        if (self.detail_level == 'chronological' and same_day
                and not self.filter_text):
            self.delete_footer()
            self.write_item(self.timelog.last_entry())
            self.add_footer()
            self.scroll_to_end()
        else:
            self.populate_log()

    def reposition_cursor(self):
        where = self.get_buffer().get_end_iter()
        where.backward_cursor_position()
        self.get_buffer().place_cursor(where)

    def scroll_to_end(self):
        # If I do the scrolling immediately, it won't scroll to the end, usually.
        # If I delay the scrolling, it works every time.
        # I only wish I knew how to disable the scroll animation.
        GLib.idle_add(self._scroll_to_end)

    def _scroll_to_end(self):
        buffer = self.get_buffer()
        self.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 0)

    def write_item(self, item):
        self.w(internationalised_format_duration(item.duration), 'duration')
        self.w('\t')
        period = _('({0:%H:%M}-{1:%H:%M})').format(item.start, item.stop)
        self.w(period, 'time')
        self.w('\t')
        tag = ('slacking' if '**' in item.entry else None)
        self.w(item.entry + '\n', tag)

    def write_group(self, entry, duration):
        self.w(internationalised_format_duration(duration), 'duration')
        tag = ('slacking' if '**' in entry else None)
        self.w('\t' + entry + '\n', tag)

    def w(self, text, tag=None):
        """Write some text at the end of the log buffer."""
        buffer = self.get_buffer()
        if tag:
            buffer.insert_with_tags_by_name(buffer.get_end_iter(), text, tag)
        else:
            buffer.insert(buffer.get_end_iter(), text)

    def wfmt(self, fmt, *args):
        """Write formatted text at the end of the log buffer.

        Accepts the same kind of format string as Python's str.format(),
        e.g. "Hello, {0}".

        Each argument should be a tuple (value, tag_name).
        """
        for bit in re.split(r'({\d+(?::[^}]*)?})', fmt):
            if bit.startswith('{'):
                spec = bit[1:-1]
                idx, colon, fmt = spec.partition(':')
                value, tag = args[int(idx)]
                if fmt:
                    value = format(value, fmt)
                self.w(value, tag)
            else:
                self.w(bit)

    def should_have_extended_footer(self):
        return self.showing_today and self.time_range == 'day'

    def update_footer(self):
        self._footer_update_pending = False
        if self._footer_mark is None:
            return
        if self._extended_footer or self.should_have_extended_footer():
            # Update "time left to work"/"at office today"
            self.delete_footer()
            self.add_footer()

    def delete_footer(self):
        buffer = self.get_buffer()
        buffer.delete(
            buffer.get_iter_at_mark(self._footer_mark), buffer.get_end_iter())
        buffer.delete_mark(self._footer_mark)
        self._footer_mark = None

    def add_footer(self):
        buffer = self.get_buffer()
        self._footer_mark = buffer.create_mark(
            'footer', buffer.get_end_iter(), True)
        window = self.get_time_window()
        total_work, total_slacking = window.totals()

        self.w('\n')
        if self.time_range == 'day':
            fmt1 = _('Total work done: {0} ({1} this week, {2} per day)')
            fmt2 = _('Total work done: {0} ({1} this week)')
        elif self.time_range == 'week':
            fmt1 = _('Total work done this week: {0} ({1} per day)')
            fmt2 = _('Total work done this week: {0}')
        elif self.time_range == 'month':
            fmt1 = _('Total work done this month: {0} ({1} per day)')
            fmt2 = _('Total work done this month: {0}')
        args = [(internationalised_format_duration(total_work), 'duration')]
        if self.time_range == 'day':
            weekly_window = self.timelog.window_for_week(self.date)
            week_total_work, week_total_slacking = weekly_window.totals()
            work_days = weekly_window.count_days()
            args.append((internationalised_format_duration(week_total_work), 'duration'))
            per_diem = week_total_work / max(1, work_days)
        else:
            work_days = window.count_days()
            per_diem = total_work / max(1, work_days)
        if work_days:
            args.append((internationalised_format_duration(per_diem), 'duration'))
            self.wfmt(fmt1, *args)
        else:
            self.wfmt(fmt2, *args)

        self.w('\n')
        if self.time_range == 'day':
            fmt1 = _('Total slacking: {0} ({1} this week, {2} per day)')
            fmt2 = _('Total slacking: {0} ({1} this week)')
        elif self.time_range == 'week':
            fmt1 = _('Total slacking this week: {0} ({1} per day)')
            fmt2 = _('Total slacking this week: {0}')
        elif self.time_range == 'month':
            fmt1 = _('Total slacking this month: {0} ({1} per day)')
            fmt2 = _('Total slacking this month: {0}')
        args = [(internationalised_format_duration(total_slacking), 'duration')]
        if self.time_range == 'day':
            args.append((internationalised_format_duration(week_total_slacking), 'duration'))
            per_diem = week_total_slacking / max(1, work_days)
        else:
            per_diem = total_slacking / max(1, work_days)
        if work_days:
            args.append((internationalised_format_duration(per_diem), 'duration'))
            self.wfmt(fmt1, *args)
        else:
            self.wfmt(fmt2, *args)

        if not self.should_have_extended_footer():
            self._extended_footer = False
            return

        self._extended_footer = True

        if self.hours:
            self.w('\n')
            time_left = self.time_left_at_work(total_work)
            time_to_leave = self.now + time_left
            if time_left < datetime.timedelta(0):
                fmt = _("Time left at work: {0} (should've finished at {1:%H:%M}, overtime of {2} until now)")
                real_time_left = datetime.timedelta(0)
                self.wfmt(
                    fmt,
                    (internationalised_format_duration(real_time_left), 'duration'),
                    (time_to_leave, 'time'),
                    (internationalised_format_duration(-time_left), 'duration'),
                )
            else:
                fmt = _('Time left at work: {0} (till {1:%H:%M})')
                self.wfmt(
                    fmt,
                    (internationalised_format_duration(time_left), 'duration'),
                    (time_to_leave, 'time'),
                )

        if self.office_hours:
            self.w('\n')
            hours = datetime.timedelta(hours=self.office_hours)
            total = total_slacking + total_work
            total += self.get_current_task_time()
            if total > hours:
                self.wfmt(
                    _('At office today: {0} ({1} overtime)'),
                    (internationalised_format_duration(total), 'duration'),
                    (internationalised_format_duration(total - hours), 'duration'),
                )
            else:
                self.wfmt(
                    _('At office today: {0} ({1} left)'),
                    (internationalised_format_duration(total), 'duration'),
                    (internationalised_format_duration(hours - total), 'duration'),
                )


class ReportView(Gtk.TextView):
    timelog = GObject.Property(
        type=object, default=None, nick='Time log',
        blurb='Time log object')

    name = GObject.Property(
        type=str, nick='Name',
        blurb='Name of report sender')

    sender = GObject.Property(
        type=str, nick='Sender email',
        blurb='Email of the report sender')

    recipient = GObject.Property(
        type=str, nick='Recipient email',
        blurb='Email of the report recipient')

    date = GObject.Property(
        type=object, default=None, nick='Date',
        blurb='Date to show (None tracks today)')

    time_range = GObject.Property(
        type=str, default='day', nick='Time range',
        blurb='Time range to show (day/week/month)')

    report_style = GObject.Property(
        type=str, nick='Report style',
        blurb='Style of the report (plain/categorized)')

    body = GObject.Property(
        type=str, nick='Report body',
        blurb='Report body text')

    report_status = GObject.Property(
        type=str, default='not-sent', nick='Report status',
        blurb='Status of this particular report (not-sent/sent/sent-elsewhere)')

    report_sent_to = GObject.Property(
        type=str, nick='Report was sent to',
        blurb='Who already received this report (other than the current recipient?)')

    def __init__(self):
        Gtk.TextView.__init__(self)
        self._update_pending = False
        self._subject = ''
        self.connect('notify::timelog', self.queue_update)
        self.connect('notify::name', self.update_subject)
        self.connect('notify::date', self.queue_update)
        self.connect('notify::time-range', self.queue_update)
        self.connect('notify::report-style', self.queue_update)
        self.connect('notify::visible', self.queue_update)
        self.connect('notify::recipient', self.update_already_sent_indication)
        self.bind_property('body', self.get_buffer(), 'text',
                           GObject.BindingFlags.BIDIRECTIONAL)
        # GTK+ themes other than Adwaita ignore the 'monospace' property and
        # use a proportional font for text widgets.
        self.override_font(Pango.FontDescription.from_string("Monospace"))

        filename = Settings().get_report_log_file()
        self.record = ReportRecord(filename)

    def queue_update(self, *args):
        if not self._update_pending:
            self._update_pending = True
            GLib.idle_add(self.populate_report)

    def get_time_window(self):
        assert self.timelog is not None
        if self.time_range == 'day':
            return self.timelog.window_for_day(self.date)
        elif self.time_range == 'week':
            return self.timelog.window_for_week(self.date)
        elif self.time_range == 'month':
            return self.timelog.window_for_month(self.date)

    @GObject.Property(type=str, nick='Name', blurb='Report subject')
    def subject(self):
        return self._subject

    def update_subject(self, *args):
        self._subject = ''
        if self.timelog is None or not self.get_visible():
            self.notify('subject')
            return  # not loaded yet
        window = self.get_time_window()
        reports = Reports(window)
        name = self.name
        if self.time_range == 'day':
            self._subject = reports.daily_report_subject(name)
        elif self.time_range == 'week':
            self._subject = reports.weekly_report_subject(name)
        elif self.time_range == 'month':
            self._subject = reports.monthly_report_subject(name)
        self.notify('subject')

    def populate_report(self):
        self._update_pending = False
        self.update_subject()
        if self.timelog is None or not self.get_visible():
            self.get_buffer().set_text('')
            return  # not loaded yet
        window = self.get_time_window()
        reports = Reports(window, email_headers=False, style=self.report_style)
        output = StringIO()
        recipient = self.recipient
        name = self.name
        if self.time_range == 'day':
            reports.daily_report(output, recipient, name)
        elif self.time_range == 'week':
            reports.weekly_report(output, recipient, name)
        elif self.time_range == 'month':
            reports.monthly_report(output, recipient, name)
        textbuf = self.get_buffer()
        textbuf.set_text(output.getvalue())
        textbuf.place_cursor(textbuf.get_start_iter())
        self.update_already_sent_indication()

    def update_already_sent_indication(self, *args):
        if not self.date:
            return
        report_kind = REPORT_KINDS[self.time_range]
        recipients = self.record.get_recipients(report_kind, self.date)
        self.report_sent_to = ', '.join(sorted(set(recipients) - {self.recipient}))
        if not recipients:
            self.report_status = 'not-sent'
        elif self.recipient in recipients:
            self.report_status = 'sent'
        else:
            self.report_status = 'sent-elsewhere'


class TaskListView(Gtk.TreeView):
    tasks = GObject.Property(
        type=object, nick='Tasks',
        blurb='The task list (an instance of TaskList)')

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.task_store = Gtk.TreeStore(str, str)
        self.set_model(self.task_store)
        column = Gtk.TreeViewColumn(_('Tasks'), Gtk.CellRendererText(), text=0)
        self.append_column(column)
        self.connect('notify::tasks', self.tasks_changed)

    def get_task_for_row(self, path):
        return self.task_store[path][1]

    def tasks_changed(self, *args):
        mark_time('loading task list')
        self.task_store.clear()
        if self.tasks is None:
            mark_time('task list empty')
            return
        for group_name, group_items in self.tasks.groups:
            if group_name == self.tasks.other_title:
                t = self.task_store.append(None, [_("Other"), ""])
            else:
                t = self.task_store.append(None, [group_name, group_name + ': '])
            for item in group_items:
                if group_name == self.tasks.other_title:
                    task = item
                else:
                    task = group_name + ': ' + item
                self.task_store.append(t, [item, task])
        self.expand_all()
        mark_time('task list loaded')
