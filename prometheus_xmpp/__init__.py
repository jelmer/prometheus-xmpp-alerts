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


__version__ = (0, 1)
version_string = '.'.join(map(str, __version__))


def create_message(message):
    """Create the message to deliver."""
    for i, alert in enumerate(message['alerts']):
        yield '%s, %d/%d, %s, %s' % (
            message['status'].upper(), i + 1, len(message['alerts']),
            alert['startsAt'], alert['annotations']['summary'])
