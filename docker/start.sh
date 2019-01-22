#!/bin/sh

export JID=${JID:-alertmanager@example.com}
export PASSWORD=${PASSWORD:-PASSWORD}
export LISTEN_ADDRESS=${LISTEN_ADDRESS:-0.0.0.0}
export LISTEN_PORT=${LISTEN_PORT:-9199}
export TO_JID=${TO_JID:-jelmer@example.com}

python3 /app/docker/generate_config.py 

exec prometheus-xmpp-alerts --config xmpp-alerts.yml
