FROM docker.io/debian:sid-slim
LABEL maintainer="jelmer@jelmer.uk"

RUN apt -y update && apt --no-install-recommends -y install prometheus-alertmanager python3-pip

COPY . .
RUN pip3 install .

EXPOSE 9199

CMD ["/usr/bin/python3", "-m", "prometheus_xmpp", "--config", "/config.yaml"]
