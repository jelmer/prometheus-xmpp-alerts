prometheus-xmpp-alerts
======================

A simple web hook that forwards prometheus alerts over XMPP.

Usage
-----
#
To use, configure a web hook in alertmanager. E.g.:

```yaml
receivers:
- name: 'jelmer-xmpp'
  webhook_configs:
  - url: 'http://192.168.2.1:9199/alert'
```

Edit the configuration file (defaults to ``/etc/prometheus/xmpp-alerts.yml``):

```yaml
jid: 'alertmanager@example.com'
password: 'PASSWORD'
# Alternatively, set a 'password_command' that should write a password to
# stdout
# password_command: 'pass show xmpp-alertmanager'
to_jid: 'jelmer@example.com'
listen_address: '192.168.2.1'
listen_port: 9199

# Text message template as jinja2; defaults to html_template with tags stripped.
text_template: |
 {{ status.upper() }}: *{{ labels.alertname }}* at {{ labels.host or labels.instance }}:\
 {{ annotations.message }}. {{ generatorURL }}
```

And run the web hook::

```shell
$ python3 -m prometheus_xmpp --config=/etc/prometheus/xmpp-alerts.yaml
```

If you have [amtool](https://github.com/prometheus/alertmanager#amtool) set up,
then you can also allow ``to_jid`` to see existing alerts and manage silences.
Set the ``amtool_allowed`` option to JIDs that are allowed to use amtool.

Docker file
-----------

You can build your own docker images using the Dockerfile in this directory, or
use ``ghcr.io/jelmer/prometheus-xmpp-alerts``. Provide your configuration in
``/config.yaml``.

Message Format
--------------

The default message format looks something like this:

  > FIRING: *AlertName* at somehost: Alert Summary. https://prometheus.example.com/expr?...

The ``text_template`` option in the configuration can be used to customize the
format, using jinja2.

Testing
-------

The web hook can be accessed on three paths:

 * ``/alert``: used by Prometheus to deliver alerts, expects POST requests
   with JSON body
 * ``/test``: delivers a test message
 * ``/metrics``: exposes statistics about number of alerts received
