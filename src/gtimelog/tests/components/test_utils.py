import doctest
import unittest

# from gtimelog.main import require_version
# require_version('Gtk', '3.0')
# require_version('Soup', '2.4')
# require_version('Secret', '1')
# from gi.repository import GLib


from gtimelog.tests.commons import Checker
# from gtimelog.ui.components.utils import do_handle_local_options, make_option, copy_properties, \
#     internationalised_format_duration, check_schema, create_data_directory


# def doctest_make_option():
#     """Tests for make_option
#
#         >>> option = make_option("test")
#         >>> option.long_name
#         'test'
#         >>> option.short_name
#         0
#         >>> option.arg
#         GLib.OptionArg.NONE
#         >>> option = make_option("test-test", short_name="test")
#         >>> option.long_name
#         'test'
#         >>> option.short_name
#         'test'
#         >>> option = make_option("testtest-", short_name="test--test")
#         >>> option.long_name
#         'testtest'
#         >>> option.short_name
#         'test'
#
#     """
#
#
# def doctest_copy_properties():
#     """Tests for copy_properties
#
#         >>> copy_properties()
#         None
#
#     """
#
#
# def doctest_internationalised_format_duration():
#     """Tests for internationalised_format_duration
#
#         >>> internationalised_format_duration()
#         None
#
#     """
#
#
# def doctest_check_schema():
#     """Tests for check_schema
#
#         >>> check_schema()
#         None
#
#     """
#
#
# def doctest_create_data_directory():
#     """Tests for do_handle_local_options
#
#         >>> create_data_directory()
#         None
#
#     """
#
#
# def doctest_do_handle_local_options(options):
#     """Tests for do_handle_local_options
#
#         >>> do_handle_local_options()
#         None
#
#     """


def additional_tests():  # for setup.py
    return doctest.DocTestSuite(optionflags=doctest.NORMALIZE_WHITESPACE,
                                checker=Checker())


def test_suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName(__name__),
        additional_tests(),
    ])
