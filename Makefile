PYTHON = python3

all: check flake8

check:
	$(PYTHON) -m unittest tests.test_suite

flake8:
	flake8 prometheus_xmpp/

typing:
	mypy prometheus_xmpp/

.PHONY: all flake8 check

docker:
	buildah build -t docker.io/jvernooij/prometheus-xmpp-alerts -t ghcr.io/jelmer/prometheus-xmpp-alerts .
	buildah push docker.io/jvernooij/prometheus-xmpp-alerts
	buildah push ghcr.io/jelmer/prometheus-xmpp-alerts
