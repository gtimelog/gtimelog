import codecs
import doctest
import os
import re
import shutil
import tempfile


class Checker(doctest.OutputChecker):
    """Doctest output checker that can deal with unicode literals."""

    def check_output(self, want, got, optionflags):
        # u'...' -> '...'; u"..." -> "..."
        got = re.sub(r'''\bu('[^']*'|"[^"]*")''', r'\1', got)
        # Python 3.7: datetime.timedelta(seconds=1860) ->
        # Python < 3.7: datetime.timedelta(0, 1860)
        got = re.sub(r'datetime[.]timedelta[(]seconds=(\d+)[)]',
                     r'datetime.timedelta(0, \1)', got)
        return doctest.OutputChecker.check_output(self, want, got, optionflags)


class Mixins(object):

    tempdir = None

    def mkdtemp(self):
        if self.tempdir is None:
            self.tempdir = tempfile.mkdtemp(prefix='gtimelog-test-')
            self.addCleanup(shutil.rmtree, self.tempdir)
        return self.tempdir

    def tempfile(self, filename='timelog.txt'):
        return os.path.join(self.mkdtemp(), filename)

    def write_file(self, filename, content):
        filename = os.path.join(self.mkdtemp(), filename)
        with codecs.open(filename, 'w', encoding='UTF-8') as f:
            f.write(content)
        return filename
