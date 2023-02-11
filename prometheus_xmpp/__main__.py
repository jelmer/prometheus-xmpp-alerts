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
import argparse
import json
import logging
import shlex
import socket
import subprocess
import sys
import traceback

import slixmpp
import yaml
from aiohttp import web
from aiohttp_openmetrics import Counter, Gauge
from aiohttp_openmetrics import metrics as serve_metrics

from prometheus_xmpp import (create_message_full, create_message_short,
                             render_html_template, render_text_template,
                             run_amtool, strip_html_tags)

DEFAULT_CONF_PATH = '/etc/prometheus/xmpp-alerts.yml'


DEFAULT_HTML_TEMPLATE = """\
{% macro color(severity) -%}
{% if severity == 'warning' -%}#ffc107
{% elif severity == 'none' -%}#17a2b8
{% else -%}#dc3545
{% endif -%}
{% endmacro -%}
{% if status == 'firing' %}
<strong>\
<span style="color:{{ color(labels.severity) }}">FIRING:</span></strong>
{% elif status == 'resolved' %}
<strong>span style="color:#33cc33">RESOLVED:</span></strong>
{% else %}
{{ status.upper() }}:
{% endif %}
{% if labels.alertname %}<i>{{ labels.alertname }}</i>{% endif %}
{% if labels.host or labels.instance %}\
at {{ labels.host or labels.instance }}{% endif %}
{% if annotations.message %}<br/>\
{{ annotations.message.replace("\\n", "<br/>") }}{% endif %}
{% if annotations.description %}<br/>{{ annotations.description }}{% endif %}
<br/><a href="{{ generatorURL }}">Alert link</a>
"""

DEFAULT_TEXT_TEMPLATE = """\
{{ status.upper() }}:\
{% if labels.alertname %}*{{ labels.alertname }}*{% endif %}\
{% if labels.host or labels.instance %}\
at {{ labels.host or labels.instance }}{% endif %}\
{% if annotations.message %}
{{ annotations.message }}{% endif %}
{% if annotations.description %}
{{ annotations.description }}{% endif %}

Link: {{ generatorURL }}
"""


EXAMPLE_ALERT = {
  "status": "firing",
  "labels": {
    "alertname": "Test",
    "instance": "localhost:1337",
  },
  "annotations": {
    "description": (
        "normally there would be details\n"
        "in this multi-line description"),
    "summary": "summary for a test alert",
  },
  "startsAt": "2022-08-01T09:52:26.739266927+01:00",
  "endsAt": "0001-01-01T00:00:00Z",
  "generatorURL": "http://example.com:9090/graph?g0.expr=someexpr"
}


alert_counter = Counter('alert_count', 'Total number of alerts delivered')
test_counter = Counter('test_count', 'Total number of test alerts delivered')
xmpp_message_counter = Counter(
    'xmpp_message_count', 'Total number of XMPP messages received.')
online_gauge = Gauge(
    'xmpp_online', 'Connected to XMPP server.')
last_alert_message_succeeded_gauge = Gauge(
    'last_alert_message_succeeded', 'Last alert message succeeded.')


def read_password_from_command(cmd):
    """
    Read the first line of the output of `cmd` and return the stripped string.
    Args:
        cmd: The command that should be executed.
    """
    out = subprocess.check_output(cmd, shell=True).decode('utf-8')
    lines = out.split('\n')
    first_line = lines[0]

    return first_line.strip()


class XmppApp(slixmpp.ClientXMPP):

    def __init__(self, jid, password_cb,
                 amtool_allowed=None, alertmanager_url=None):

        password = password_cb()

        slixmpp.ClientXMPP.__init__(self, jid, password)
        self._amtool_allowed = amtool_allowed or []
        self.alertmanager_url = alertmanager_url
        self.auto_authorize = True
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.lost)
        self.add_event_handler("failed_auth", self.failed_auth)
        self.register_plugin('xep_0071')  # XHTML-IM
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0004')  # Data Forms
        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0199')  # XMPP Ping

    def failed_auth(self, stanza):
        logging.warning("XMPP Authentication failed: %r", stanza)

    def start(self, event):
        """Process the session_start event.

        Args:
          event: Event data (empty)
        """
        logging.info("Session started.")
        self.send_presence(ptype='available', pstatus='Active')
        self.get_roster()
        online_gauge.set(1)
        last_alert_message_succeeded_gauge.set(1)

    def lost(self, event):
        online_gauge.set(0)
        logging.info("Connection lost, exiting.")
        sys.exit(1)

    def message(self, msg):
        """Handle an incoming message.

        Args:
            msg: The received message stanza.
        """
        if msg['type'] in ('chat', 'normal'):
            args = shlex.split(msg['body'])
            if args == []:
                response = "No command specified"
            elif args[0].lower() in ('alert', 'silence'):
                args[0] = args[0].lower()
                if msg['from'].bare in self._amtool_allowed:
                    if self.alertmanager_url:
                        args = [
                            '--alertmanager.url', self.alertmanager_url] + args
                    response = run_amtool(args)
                else:
                    response = "Unauthorized JID."
            elif args[0].lower() == 'help':
                response = "Supported commands: help, alert, silence."
            else:
                response = "Unknown command: %s" % args[0].lower()
            msg.reply(response).send()


async def serve_test(request):
    xmpp_app = request.app['xmpp_app']
    to_jid = request.match_info.get('to_jid', request.app['config']['to_jid'])
    test_counter.inc()
    try:
        text, html = await render_alert(request.app['config'], EXAMPLE_ALERT)
        xmpp_app.send_message(
            mto=to_jid,
            mbody=text,
            mhtml=html,
            mtype='chat')
    except slixmpp.xmlstream.xmlstream.NotConnectedError as e:
        logging.warning('Test alert not posted since we are not online: %s', e)
        return web.Response(
            body='Did not send message. Not online: %s' % e)
    else:
        return web.Response(body='Sent message.')


async def render_alert(config, alert):
    # format is here just for backwards compatibility
    if 'format' in config and config['format'] == 'full':
        text = '\n--\n'.join(create_message_full(alert))
        html = None
    elif 'format' in config and config['format'] == 'short':
        text = '\n'.join(create_message_short(alert))
        html = None
    elif 'html_template' in config:
        html = render_html_template(config['html_template'], alert)
        if 'text_template' in config:
            text = render_text_template(config['text_template'], alert)
        else:
            text = strip_html_tags(html)
    elif 'text_template' in config:
        text = render_text_template(config['text_template'], alert)
        html = None
    else:
        text = render_text_template(DEFAULT_TEXT_TEMPLATE, alert)
        html = render_html_template(DEFAULT_HTML_TEMPLATE, alert)
    return text, html


async def serve_alert(request):
    config = request.app['config']
    xmpp_app = request.app['xmpp_app']
    to_jid = request.match_info.get('to_jid', config['to_jid'])
    alert_counter.inc()
    try:
        payload = await request.json()
    except json.decoder.JSONDecodeError as e:
        raise web.HTTPUnprocessableEntity(text=str(e))
    sent = 0
    for alert in payload['alerts']:
        try:
            text, html = await render_alert(config, alert)

            try:
                xmpp_app.send_message(
                        mto=to_jid,
                        mbody=text,
                        mhtml=html,
                        mtype='chat')
            except slixmpp.xmlstream.xmlstream.NotConnectedError as e:
                logging.warning('Alert posted but we are not online: %s', e)
                last_alert_message_succeeded_gauge.set(0)
                return web.Response(
                    body='Did not send message. Not online: %s' % e)
            else:
                last_alert_message_succeeded_gauge.set(1)
                sent += 1
        except Exception as e:
            last_alert_message_succeeded_gauge.set(0)
            traceback.print_exc()
            raise web.HTTPInternalServerError(
                text='failed to sent some messages: %s' % e)
    return web.Response(body='Sent %d messages' % sent)


async def serve_health(request):
    if not request.app['xmpp_app'].authenticated:
        return web.Response(status=500, text='not authenticated to server')
    return web.Response(body=b'ok')


async def serve_root(request):
    return web.Response(body='See /test, /health, /alert or /metrics')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config_path',
                        type=str, default=DEFAULT_CONF_PATH,
                        help='Path to configuration file.')
    parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                        action="store_const", dest="loglevel",
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                        action="store_const", dest="loglevel",
                        const=logging.DEBUG, default=logging.INFO)

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(
        level=args.loglevel, format='%(levelname)-8s %(message)s')

    with open(args.config_path) as f:
        if getattr(yaml, 'FullLoader', None):
            config = yaml.load(f, Loader=yaml.FullLoader)  # type: ignore
        else:
            # Backwards compatibility with older versions of Python
            config = yaml.load(f)  # type: ignore

    hostname = socket.gethostname()
    jid = "{}/{}".format(config['jid'], hostname)

    if config.get('password'):
        def password_cb():
            return config['password']
    elif config.get('password_command'):
        def password_cb():
            return read_password_from_command(config['password_command'])
    else:
        def password_cb():
            return None

    xmpp_app = XmppApp(
        jid, password_cb,
        config.get('amtool_allowed', [config['to_jid']]),
        config.get('alertmanager_url', None))

    web_app = web.Application()
    web_app['config'] = config
    web_app['xmpp_app'] = xmpp_app
    web_app.add_routes([
        web.get('/', serve_root),
        web.get('/test', serve_test),
        web.get('/test/{to_jid}', serve_test),
        web.post('/test', serve_test),
        web.post('/test/{to_jid}', serve_test),
        web.get('/alert', serve_alert),
        web.get('/alert/{to_jid}', serve_alert),
        web.post('/alert', serve_alert),
        web.post('/alert/{to_jid}', serve_alert),
        web.get('/metrics', serve_metrics),
        web.get('/health', serve_health),
    ])

    xmpp_app.connect()
    web.run_app(
        web_app, host=config['listen_address'], port=config['listen_port'],
        loop=xmpp_app.loop)


if __name__ == '__main__':
    main()
