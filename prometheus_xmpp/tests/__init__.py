# __init__.py -- The tests for prometheus_xmpp
# Copyright (C) 2018 Jelmer Vernooij <jelmer@jelmer.uk>
#

from datetime import datetime
import unittest

from prometheus_xmpp import create_message, parse_timestring


class CreateMessageTests(unittest.TestCase):

    def test_create_message(self):
        message = {
            'alerts': [
                {
                    'startsAt': '2019-04-27T05:33:35.739602132Z',
                    'annotations': {
                        'summary': 'Something',
                    },
                }
            ],
            'status': 'firing',
            }
        self.assertEqual(
            ['FIRING, 2019-04-27T05:33:35, Something'],
            list(create_message(message)))


class ParseTimestringTests(unittest.TestCase):

    def test_parse_with_nanoseconds(self):
        self.assertEqual(
            datetime.strptime(
                '2019-04-27T05:33:35.739602Z', '%Y-%m-%dT%H:%M:%S.%fZ'),
            parse_timestring('2019-04-27T05:33:35.739602132Z'))

    def test_parse_with_microseconds(self):
        self.assertEqual(
            datetime.strptime(
                '2019-04-27T05:33:35.739602Z', '%Y-%m-%dT%H:%M:%S.%fZ'),
            parse_timestring('2019-04-27T05:33:35.739602Z'))


def test_suite():
    module_names = ['prometheus_xmpp.tests']
    loader = unittest.TestLoader()
    return loader.loadTestsFromNames(module_names)
