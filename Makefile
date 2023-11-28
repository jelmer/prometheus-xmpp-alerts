PYTHON = python3

all: check ruff

check:
	$(PYTHON) -m unittest tests.test_suite

ruff:
	ruff check .

typing:
	mypy prometheus_xmpp/

.PHONY: all ruff check

docker:
	buildah build -t docker.io/jvernooij/prometheus-xmpp-alerts -t ghcr.io/jelmer/prometheus-xmpp-alerts .
	buildah push docker.io/jvernooij/prometheus-xmpp-alerts
	buildah push ghcr.io/jelmer/prometheus-xmpp-alerts
