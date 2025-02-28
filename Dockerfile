FROM docker.io/debian:sid-slim
LABEL maintainer="jelmer@jelmer.uk"

RUN apt -y update && apt --no-install-recommends -y dist-upgrade
RUN apt -y update && apt --no-install-recommends -y install prometheus-alertmanager python3-pip python3-slixmpp python3-aiohttp python3-pytz python3-yaml python3-aiohttp-openmetrics python3-jinja2 python3-bs4

COPY . .
RUN pip3 install --break-system-packages .

EXPOSE 9199

CMD ["/usr/bin/python3", "-m", "prometheus_xmpp", "--optional-config", "/config.yaml"]
