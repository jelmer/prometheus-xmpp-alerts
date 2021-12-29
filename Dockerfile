FROM python:3.7-alpine AS build-env

RUN apk add --no-cache \
  gcc \
  musl-dev \
  libffi-dev

RUN pip install \
  slixmpp \
  aiohttp \
  pyyaml \
  prometheus_client

FROM python:3.7-alpine
LABEL maintainer="jelmer@jelmer.uk"

COPY --from=build-env /usr/local/lib/python3.7/site-packages/ /usr/local/lib/python3.7/site-packages/

RUN apk add --no-cache alertmanager

ADD ./prometheus-xmpp-alerts /prometheus-xmpp-alerts
ADD ./prometheus_xmpp /prometheus_xmpp

RUN sed -i 's/yaml.load(f)/yaml.load(f, Loader=yaml.FullLoader)/' /prometheus-xmpp-alerts

EXPOSE 9199

CMD ["/usr/local/bin/python", "/prometheus-xmpp-alerts", "--config", "/config.yaml"]
