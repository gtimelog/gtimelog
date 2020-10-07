import codecs

from gtimelog.core.utils import get_mtime


class TaskList(object):
    """Task list.

    You can have a list of common tasks in a text file that looks like this

        Arrived **
        Reading mail
        Project1: do some task
        Project2: do some other task
        Project1: do yet another task

    These tasks are grouped by their common prefix (separated with ':').
    Tasks without a ':' are grouped under "Other".

    A TaskList has an attribute 'groups' which is a list of tuples
    (group_name, list_of_group_items).
    """

    other_title = 'Other'

    loading_callback = None
    loaded_callback = None
    error_callback = None

    def __init__(self, filename):
        self.filename = filename
        self.load()

    def check_reload(self):
        """Look at the mtime of tasks.txt, and reload it if necessary.

        Returns True if the file was reloaded.
        """
        mtime = get_mtime(self.filename)
        if mtime != self.last_mtime:
            self.load()
            return True
        else:
            return False

    def load(self):
        """Load task list from a file named self.filename."""
        groups = {}
        self.last_mtime = get_mtime(self.filename)
        try:
            with codecs.open(self.filename, encoding='UTF-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line:
                        group, task = [s.strip() for s in line.split(':', 1)]
                    else:
                        group, task = self.other_title, line
                    groups.setdefault(group, []).append(task)
        except IOError:
            pass  # the file's not there, so what?
        self.groups = sorted(groups.items())

    def reload(self):
        """Reload the task list."""
        self.load()
