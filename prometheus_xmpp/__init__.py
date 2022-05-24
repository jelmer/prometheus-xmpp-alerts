#!/usr/bin/python3
# Simple HTTP web server that forwards prometheus alerts over XMPP.
#
# To use, configure a web hook in alertmanager. E.g.:
#
# receivers:
# - name: 'jelmer-pager'
#   webhook_configs:
#   - url: 'http://192.168.2.1:9199/alert'
#
# Edit xmpp-alerts.yml.example, then run:
# $ python3 prometheus-xmpp-alerts --config=xmpp-alerts.yml.example

import re
from datetime import datetime
import subprocess


__version__ = (0, 5, 4)
version_string = '.'.join(map(str, __version__))


def parse_timestring(ts):
    # strptime doesn't understand nanoseconds, so discard the last three digits
    ts = re.sub(r'\.([0-9]{6})([0-9]*)([^0-9])', r'.\1\3', ts)
    return datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f%z')


def create_message_short(message):
    """Create the short form message to deliver."""
    for alert in message['alerts']:
        try:
            summary = alert['annotations']['summary']
        except KeyError:
            summary = alert['labels']['alertname']
        yield '%s, %s, %s' % (
            alert['status'].upper(),
            parse_timestring(alert['startsAt']).isoformat(timespec='seconds'),
            summary)


def create_message_full(message):
    """Create the long form message to deliver."""
    group_labels = ''
    if 'groupLabels' in message:
        group_labels = ' ({})'.format(' '.join(
            value for key, value in message['groupLabels'].items()))

    for alert in message['alerts']:
        description = ''
        if 'description' in alert['annotations']:
            description = '\n{}'.format(alert['annotations']['description'])

        labels = ''
        if 'labels' in alert:
            for label, value in alert['labels'].items():
                labels += '\n*{}:* {}'.format(label, value)

        try:
            summary = alert['annotations']['summary']
        except KeyError:
            summary = alert['labels']['alertname']
        yield '*[{}] {}*{}{}{}'.format(
            alert['status'].upper(),
            summary,
            group_labels,
            description,
            labels)


def run_amtool(args):
    """Run amtool with the specified arguments."""
    # TODO(jelmer): Support setting the current user, e.g. for silence
    # ownership.
    ret = subprocess.run(
        ["amtool"] + args, shell=False, universal_newlines=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return ret.stdout
