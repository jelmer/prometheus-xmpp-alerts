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
format: 'short'
```

And run the web hook::

```shell
$ python3 prometheus-xmpp-alerts
```

If you have [amtool](https://github.com/prometheus/alertmanager#amtool) set up,
then you can also allow ``to_jid`` to see existing alerts and manage silences.

Docker file
-----------

You can build your own docker images using the Dockerfile in this directory, or
use ``ghcr.io/jelmer/prometheus-xmpp-alerts``. Provide your configuration in
``/config.yaml``.

Password Command
----------------

Instead of hardcoding your password, you can also use a `password_command`. The
command should write the password to stdout. Only the first line (stripped of
whitespaces) is being used as password.

Message Format
--------------

If you don't set the message format option, the `short` format will be used.

* **short**
  > FIRING, 2019-05-17T18:48:18, Alert Summary

* **full**
  > **[FIRING] Alert Summary** (groupLabelValue1 groupLabelValue2)
  > This is the description of the test alert.
  > **label1**: value1
  > **label2**: value2
  > **label3**: value3


Testing
-------

The web hook can be accessed on three paths:

 * ``/alert``: used by Prometheus to deliver alerts, expects POST requests
   with JSON body
 * ``/test``: delivers a test message
 * ``/metrics``: exposes statistics about number of alerts received
