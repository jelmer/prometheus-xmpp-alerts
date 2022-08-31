PYTHON = python3

all: check flake8

check:
	$(PYTHON) -m unittest prometheus_xmpp.tests.test_suite

flake8:
	flake8

.PHONY: all flake8 check

docker:
	buildah build -t docker.io/jvernooij/prometheus-xmpp-alerts -t ghcr.io/jelmer/prometheus-xmpp-alerts .
	buildah push docker.io/jvernooij/prometheus-xmpp-alerts
	buildah push ghcr.io/jelmer/prometheus-xmpp-alerts
