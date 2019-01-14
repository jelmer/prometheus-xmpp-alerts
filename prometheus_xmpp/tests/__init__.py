# __init__.py -- The tests for prometheus_xmpp
# Copyright (C) 2018 Jelmer Vernooij <jelmer@jelmer.uk>
#

import unittest

from prometheus_xmpp import create_message


class CreateMessageTests(unittest.TestCase):

    def test_create_message(self):
        message = {
            'alerts': [
                {
                    'startsAt': '2018-12-12',
                    'annotations': {
                        'summary': 'Something',
                    },
                }
            ],
            'status': 'firing',
            }
        self.assertEqual(
            ['FIRING, 1/1, 2018-12-12, Something'],
            list(create_message(message)))


def test_suite():
    module_names = ['prometheus_xmpp.tests']
    loader = unittest.TestLoader()
    return loader.loadTestsFromNames(module_names)
