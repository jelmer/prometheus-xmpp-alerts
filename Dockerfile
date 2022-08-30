FROM debian:sid-slim
LABEL maintainer="jelmer@jelmer.uk"

RUN apt -y update && apt --no-install-recommends -y install python3-slixmpp python3-aiohttp python3-yaml python3-aiohttp-openmetrics prometheus-alertmanager

COPY ./prometheus-xmpp-alerts /prometheus-xmpp-alerts
COPY ./prometheus_xmpp /prometheus_xmpp

EXPOSE 9199

CMD ["/usr/bin/python3", "/prometheus-xmpp-alerts", "--config", "/config.yaml"]
