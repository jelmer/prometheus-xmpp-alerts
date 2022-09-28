FROM debian:sid-slim
LABEL maintainer="jelmer@jelmer.uk"

RUN apt -y update && apt --no-install-recommends -y install python3-slixmpp python3-aiohttp python3-yaml python3-aiohttp-openmetrics prometheus-alertmanager python3-jinja2 python3-bs4

COPY ./prometheus_xmpp /prometheus_xmpp

EXPOSE 9199

CMD ["/usr/bin/python3", "-m", "prometheus_xmpp", "--config", "/config.yaml"]
