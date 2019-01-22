#!/usr/bin/python3

import os
import yaml

d = {
  'jid': os.environ['JID'],
  'password': os.environ['PASSWORD'],
  'listen_address': os.environ['LISTEN_ADDRESS'],
  'listen_port': os.environ['LISTEN_PORT'],
  'to_jid': os.environ['TO_JID']
}

with open('xmpp-alerts.yml', 'w') as yaml_file:
  yaml.dump(d, yaml_file, default_flow_style=False)
