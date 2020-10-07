import os
import shutil
import tempfile


def restore_env(envvar, value):
    if value is not None:
        os.environ[envvar] = value
    else:
        os.environ.pop(envvar, None)


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
        with open(filename, 'w', encoding='UTF-8') as f:
            f.write(content)
        return filename
