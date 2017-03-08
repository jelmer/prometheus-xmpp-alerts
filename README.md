prometheus-xmpp-alerts
======================
Simple HTTP web server that forwards prometheus alerts over XMPP.

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

Then start this script, after editing the config dict:

```shell
$ python3 prometheus-xmpp-alerts
```
