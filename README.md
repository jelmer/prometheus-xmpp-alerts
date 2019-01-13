prometheus-xmpp-alerts
======================

A simple web hook that forwards prometheus alerts over XMPP.

Usage
-----
#
To use, configure a web hook in alertmanager. E.g.:

```yaml
receivers:
- name: 'jelmer-pager'
  webhook_configs:
  - url: 'http://192.168.2.1:9199/alert'
```

Edit the configuration file (defaults to ``/etc/prometheus/xmpp-alerts.yml``):

```yaml
jid: 'alertmanager@example.com'
password: 'PASSWORD'
to_jid: 'jelmer@example.com'
listen_address: '192.168.2.1'
listen_port: 9199
```

And run the web hook::

```shell
$ python3 prometheus-xmpp-alerts
```

If you have [amtool](https://github.com/prometheus/alertmanager#amtool) set up,
then you can also allow ``to_jid`` to see existing alerts and manage silences.

Testing
-------

The web hook can be accessed on two paths:

 * ``/alerts``: used by Prometheus to deliver alerts, expects POST requests
   with JSON body
 * ``/test``: delivers a test message
