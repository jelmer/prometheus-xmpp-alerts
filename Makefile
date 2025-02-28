PYTHON ?= python3
DOCKER ?= docker

all: check ruff

check:
	$(PYTHON) -m unittest tests.test_suite

ruff:
	ruff check .

typing:
	mypy prometheus_xmpp/

.PHONY: all ruff check

docker:
	$(DOCKER) build -t docker.io/jvernooij/prometheus-xmpp-alerts -t ghcr.io/jelmer/prometheus-xmpp-alerts .
	$(DOCKER) push docker.io/jvernooij/prometheus-xmpp-alerts
	$(DOCKER) push ghcr.io/jelmer/prometheus-xmpp-alerts
