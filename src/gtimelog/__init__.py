import logging
import sys

__version__ = '0.12.0.dev0'
DEBUG = '--debug' in sys.argv
root_logger = logging.getLogger()
root_logger.addHandler(logging.StreamHandler())
if DEBUG:
    root_logger.setLevel(logging.DEBUG)
else:
    root_logger.setLevel(logging.INFO)
