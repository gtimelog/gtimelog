from datetime import time
from io import StringIO

from gtimelog.core.time import TimeLog


def make_time_window(file=None, minimum=None, maximum=None, vm=time(2)):
    if file is None:
        file = StringIO()
    return TimeLog(file, vm).window_for(minimum, maximum)
