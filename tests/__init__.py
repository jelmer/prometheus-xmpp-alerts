# __init__.py -- The tests for prometheus_xmpp
# Copyright (C) 2018 Jelmer Vernooij <jelmer@jelmer.uk>
#

import unittest
from datetime import datetime

import pytz

from prometheus_xmpp import parse_timestring, render_text_template
from prometheus_xmpp.__main__ import (
    DEPRECATED_TEXT_TEMPLATE_SHORT,
    DEPRECATED_TEXT_TEMPLATE_FULL,
)


class CreateMessageTests(unittest.TestCase):
    message = {
        "version": "4",
        "groupKey": "test",
        "status": "firing",
        "receiver": "xmpp",
        "groupLabels": {
            "groupLabel1": "groupLabelValue1",
            "groupLabel2": "groupLabelValue2",
        },
        "commonLabels": {
            "commonLabel1": "commonLabelValue1",
            "commonLabel2": "commonLabelValue2",
        },
        "commonAnnotations": {
            "commonAnnotation1": "commonAnnotationValue1",
            "commonAnnotation2": "commonAnnotationValue2",
        },
        "externalURL": "https://alertmanager.example.com",
        "alerts": [
            {
                "status": "firing",
                "labels": {"test": "true", "severity": "test"},
                "annotations": {
                    "summary": "Test Alert",
                    "description": "This is just a test alert.",
                },
                "startsAt": "2019-04-12T23:20:50.123456789Z",
                "endsAt": "2019-04-12T23:20:50.123456789Z",
                "generatorURL": "curl",
            }
        ],
    }

    def test_create_message_short(self):
        self.assertEqual(
            'FIRING, 2019-04-12T23:20:50+00:00, Test Alert',
            render_text_template(
                DEPRECATED_TEXT_TEMPLATE_SHORT, self.message['alerts'][0]))

    def test_create_message_full(self):
        self.assertEqual(
            '*[FIRING] Test Alert*'
                + '\nThis is just a test alert.'
                + '\n*test:* true'
                + '\n*severity:* test',
            render_text_template(
                DEPRECATED_TEXT_TEMPLATE_FULL, self.message['alerts'][0]))


class ParseTimestringTests(unittest.TestCase):
    def test_parse_with_nanoseconds(self):
        self.assertEqual(
            datetime(2019, 4, 27, 5, 33, 35, 739602, pytz.utc),
            parse_timestring("2019-04-27T05:33:35.739602132Z"),
        )

    def test_parse_with_microseconds(self):
        self.assertEqual(
            datetime(2019, 4, 27, 5, 33, 35, 739602, pytz.utc),
            parse_timestring("2019-04-27T05:33:35.739602Z"),
        )

    def test_parse_with_timezone(self):
        self.assertEqual(
            datetime(2019, 4, 27, 5, 33, 35, 739602, pytz.utc),
            parse_timestring("2019-04-27T05:33:35.739602+00:00"),
        )


def test_suite():
    module_names = ["tests"]
    loader = unittest.TestLoader()
    return loader.loadTestsFromNames(module_names)
