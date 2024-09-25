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
import os
import shlex
import socket
import subprocess
import sys
import traceback
from typing import Optional, Tuple

import slixmpp
import yaml
from aiohttp import web
from aiohttp_openmetrics import Counter, Gauge
from aiohttp_openmetrics import metrics as serve_metrics

from prometheus_xmpp import (
    render_html_template,
    render_text_template,
    run_amtool,
    strip_html_tags,
)

DEFAULT_CONF_PATH = "/etc/prometheus/xmpp-alerts.yml"


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


DEPRECATED_TEXT_TEMPLATE_SHORT = """\
{{ status.upper() }}, \
{{ parse_time(startsAt).isoformat(timespec='seconds') }}, \
{{ annotations.summary or labels.alertname }}\
"""


DEPRECATED_TEXT_TEMPLATE_FULL = """\
*[{{ status.upper() }}] {{ annotations.summary or labels.alertname }}*
{{ annotations.description }}\
{% for label, value in labels.items() %}
*{{ label }}:* {{ value }}
{%- endfor %}
"""


EXAMPLE_ALERT = {
    "status": "firing",
    "labels": {
        "alertname": "Test",
        "instance": "localhost:1337",
    },
    "annotations": {
        "description": (
            "normally there would be details\n" "in this multi-line description"
        ),
        "summary": "summary for a test alert",
    },
    "startsAt": "2022-08-01T09:52:26.739266927+01:00",
    "endsAt": "0001-01-01T00:00:00Z",
    "generatorURL": "http://example.com:9090/graph?g0.expr=someexpr",
}


alert_counter = Counter("alert_count", "Total number of alerts delivered")
test_counter = Counter("test_count", "Total number of test alerts delivered")
xmpp_message_counter = Counter(
    "xmpp_message_count", "Total number of XMPP messages received."
)
online_gauge = Gauge("xmpp_online", "Connected to XMPP server.")
last_alert_message_succeeded_gauge = Gauge(
    "last_alert_message_succeeded", "Last alert message succeeded."
)


def read_password_from_command(cmd):
    """
    Read the first line of the output of `cmd` and return the stripped string.
    Args:
        cmd: The command that should be executed.
    """
    out = subprocess.check_output(cmd, shell=True).decode("utf-8")
    lines = out.split("\n")
    first_line = lines[0]

    return first_line.strip()


class XmppApp(slixmpp.ClientXMPP):
    def __init__(
        self,
        jid,
        password_cb,
        amtool_allowed=None,
        alertmanager_url=None,
    ):
        password = password_cb()

        slixmpp.ClientXMPP.__init__(self, jid, password)
        self._amtool_allowed = amtool_allowed or []
        self.alertmanager_url = alertmanager_url
        self.auto_authorize = True
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.lost)
        self.add_event_handler("failed_auth", self.failed_auth)
        self.register_plugin("xep_0071")  # XHTML-IM
        self.register_plugin("xep_0030")  # Service Discovery
        self.register_plugin("xep_0004")  # Data Forms
        self.register_plugin("xep_0060")  # PubSub
        self.register_plugin("xep_0199")  # XMPP Ping
        self.register_plugin("xep_0045")  # Multi-User Chat

    def failed_auth(self, stanza):
        logging.warning("XMPP Authentication failed: %r", stanza)

    def start(self, event):
        """Process the session_start event.

        Args:
          event: Event data (empty)
        """
        logging.info("Session started.")
        self.send_presence(ptype="available", pstatus="Active")
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
        if msg["type"] in ("chat", "normal"):
            args = shlex.split(msg["body"])
            if args == []:
                response = "No command specified"
            elif args[0].lower() in ("alert", "silence"):
                args[0] = args[0].lower()
                if msg["from"].bare in self._amtool_allowed:
                    if self.alertmanager_url:
                        args = ["--alertmanager.url", self.alertmanager_url] + args
                    response = run_amtool(args)
                else:
                    response = "Unauthorized JID."
            elif args[0].lower() == "help":
                response = "Supported commands: help, alert, silence."
            else:
                response = "Unknown command: %s" % args[0].lower()
            msg.reply(response).send()


async def serve_test(request):
    xmpp_app = request.app['xmpp_app']
    try:
        recipients = [request.match_info['to_jid']]
    except KeyError:
        recipients = request.app['recipients']
    if not recipients:
        return web.Response(
            status=500,
            text="No recipients configured. Set `recipients` in configuration, `XMPP_RECIPIENTS` in environment or use /test/TO_JID.",
        )

    test_counter.inc()
    try:
        text, html = await render_alert(
            request.app['text_template'],
            request.app['html_template'],
            EXAMPLE_ALERT)
        for to_jid in recipients:
            xmpp_app.send_message(
                mto=to_jid,
                mbody=text,
                mhtml=html,
                mtype='chat')
    except slixmpp.xmlstream.xmlstream.NotConnectedError as e:
        logging.warning("Test alert not posted since we are not online: %s", e)
        return web.Response(body="Did not send message. Not online: %s" % e)
    else:
        return web.Response(body="Sent message.")


async def render_alert(text_template: Optional[str], html_template: Optional[str], alert) -> Tuple[str, Optional[str]]:
    text: str
    html: Optional[str]
    if html_template:
        html = render_html_template(html_template, alert)
        if not text_template:
            text = strip_html_tags(html)
        else:
            text = render_text_template(text_template, alert)
    elif text_template:
        text = render_text_template(text_template, alert)
        html = None
    else:
        text = render_text_template(DEFAULT_TEXT_TEMPLATE, alert)
        html = render_html_template(DEFAULT_HTML_TEMPLATE, alert)
    return text, html


async def serve_alert(request):
    xmpp_app = request.app['xmpp_app']
    try:
        recipients = [(request.match_info['to_jid'], 'chat')]
    except KeyError:
        try:
            recipients = [(jid, 'chat') for jid in request.app['recipients']]
        except KeyError:
            recipients = [(request.app['muc_jid'], 'groupchat')]

    if request.content_type != "application/json":
        raise web.HTTPUnsupportedMediaType(
            text="Expected Content-Type: application/json"
        )

    alert_counter.inc()
    try:
        payload = await request.json()
    except json.decoder.JSONDecodeError as e:
        raise web.HTTPUnprocessableEntity(text=str(e))
    sent = 0
    for alert in payload["alerts"]:
        try:
            text, html = await render_alert(
                request.app['text_template'], request.app['html_template'],
                alert)

            try:
                for (mto, mtype) in recipients:
                    xmpp_app.send_message(
                            mto=mto,
                            mbody=text,
                            mhtml=html,
                            mtype=mtype)
            except slixmpp.xmlstream.xmlstream.NotConnectedError as e:
                logging.warning("Alert posted but we are not online: %s", e)
                last_alert_message_succeeded_gauge.set(0)
                return web.Response(body="Did not send message. Not online: %s" % e)
            else:
                last_alert_message_succeeded_gauge.set(1)
                sent += 1
        except Exception as e:
            last_alert_message_succeeded_gauge.set(0)
            traceback.print_exc()
            raise web.HTTPInternalServerError(
                text="failed to sent some messages: %s" % e
            )
    return web.Response(body="Sent %d messages" % sent)


async def serve_health(request):
    if not request.app["xmpp_app"].authenticated:
        return web.Response(status=500, text="not authenticated to server")
    return web.Response(body=b"ok")


INDEX = """\
<html>
<head>
  <title>prometheus-xmpp alerts</title>
</head>
<body>
See <a href="/test">/test</a>, <a href="/health">/health</a>, <a href="/alert">/alert</a> or <a href="/metrics">/metrics</a>.
</body>
</html>
"""


async def serve_root(request):
    return web.Response(
        content_type="text/html",
        body=INDEX)


def parse_args(argv=None, env=os.environ):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config_path',
                        type=str, default=None,
                        help='Path to configuration file.')
    parser.add_argument('--optional-config', dest='optional_config_path',
                        type=str, default=DEFAULT_CONF_PATH,
                        help=argparse.SUPPRESS)
    parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                        action="store_const", dest="loglevel",
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                        action="store_const", dest="loglevel",
                        const=logging.DEBUG, default=logging.INFO)

    args = parser.parse_args(argv)

    # Setup logging.
    logging.basicConfig(level=args.loglevel, format="%(levelname)-8s %(message)s")

    if not args.config_path and args.optional_config_path:
        if os.path.isfile(args.optional_config_path):
            args.config_path = args.optional_config_path

    if args.config_path:
        with open(args.config_path) as f:
            if getattr(yaml, "FullLoader", None):
                config = yaml.load(f, Loader=yaml.FullLoader)  # type: ignore
            else:
                # Backwards compatibility with older versions of Python
                config = yaml.load(f)  # type: ignore
    else:
        config = {}

    if 'XMPP_ID' in env:
        jid = env['XMPP_ID']
    elif 'jid' in config:
        jid = config['jid']
    else:
        parser.error('no jid set in configuration (`jid`) or environment (`XMPP_ID`)')

    hostname = socket.gethostname()
    jid = "{}/{}".format(jid, hostname)

    if 'XMPP_PASS' in env:
        def password_cb():
            return env['XMPP_PASS']
    elif config.get('password'):

        def password_cb():
            return config["password"]
    elif config.get("password_command"):

        def password_cb():
            return read_password_from_command(config["password_command"])
    else:

        def password_cb():
            return None

    if 'XMPP_RECIPIENTS' in env:
        recipients = env['XMPP_RECIPIENTS'].split(',')
    elif 'recipients' in config:
        recipients = config['recipients']
        if not isinstance(recipients, list):
            recipients = [recipients]
    elif 'to_jid' in config:
        recipients = [config['to_jid']]
    else:
        parser.error(
            'no recipients specified in configuration (`recipients` or `to_jid`) or environment (`XMPP_RECIPIENTS`)')

    if 'XMPP_AMTOOL_ALLOWED' in env:
        amtool_allowed = env['XMPP_AMTOOL_ALLOWED'].split(',')
        config['amtool_allowed'] = amtool_allowed
    elif 'amtool_allowed' in config:
        if not isinstance(config['amtool_allowed'], list):
            config['amtool_allowed'] = [config['amtool_allowed']]
    else:
        config['amtool_allowed'] = list(recipients)

    if 'ALERTMANAGER_URL' in env:
        config['alertmanager_url'] = env['ALERTMANAGER_URL']

    if config.get('format') not in ('full', 'short', None):
        parser.error("unsupport config format: %s" % config['format'])

    return (
        jid,
        password_cb,
        recipients,
        config,
    )


def main():
    (
        jid,
        password_cb,
        recipients,
        config,
    ) = parse_args()

    amtool_allowed = config.get('amtool_allowed')
    alertmanager_url = config.get('alertmanager_url')

    xmpp_app = XmppApp(
        jid, password_cb,
        amtool_allowed,
        alertmanager_url)

    # Backward compatibility
    text_template = os.environ.get('TEXT_TEMPLATE')
    html_template = os.environ.get('HTML_TEMPLATE')

    if not text_template and 'text_template' in config:
        text_template = config['text_template']

    if not html_template and 'html_template' in config:
        html_template = config['html_template']

    if not text_template and not html_template and 'format' in config:
        if config['format'] == 'full':
            text_template = DEPRECATED_TEXT_TEMPLATE_FULL
        elif config['format'] == 'short':
            text_template = DEPRECATED_TEXT_TEMPLATE_SHORT

    muc_jid = os.environ.get('MUC_JID')
    if not muc_jid and 'muc_jid' in config:
        muc_jid = config['muc_jid']

    if muc_jid:
        muc_bot_nick = os.environ.get('MUC_BOT_NICK')
        if not muc_bot_nick and 'muc_bot_nick' in config:
            muc_bot_nick = config.get("muc_bot_nick")
        if not muc_bot_nick:
            muc_bot_nick = "PrometheusAlerts"
        xmpp_app.plugin["xep_0045"].join_muc(muc_jid, muc_bot_nick)

    web_app = web.Application()
    web_app['text_template'] = text_template
    web_app['html_template'] = html_template
    web_app['recipients'] = recipients
    web_app['xmpp_app'] = xmpp_app
    web_app['muc_jid'] = muc_jid
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

    if 'WEBHOOK_HOST' in os.environ:
        listen_address = os.environ['WEBHOOK_HOST']
    elif 'listen_address' in config:
        listen_address = config['listen_address']
    else:
        listen_address = '127.0.0.1'

    if 'WEBHOOK_PORT' in os.environ:
        listen_port = int(os.environ['WEBHOOK_PORT'])
    elif 'listen_port' in config:
        listen_port = config['listen_port']
    else:
        listen_port = 8080

    xmpp_app.connect()
    web.run_app(
        web_app, host=listen_address, port=listen_port,
        loop=xmpp_app.loop)


if __name__ == "__main__":
    main()
