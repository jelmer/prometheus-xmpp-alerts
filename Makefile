PYTHON = python3

all: check flake8

check:
	$(PYTHON) -m unittest prometheus_xmpp.tests.test_suite

flake8:
	flake8

.PHONY: all flake8 check

docker:
	docker build -t jvernooij/prometheus-xmpp-alerts -t ghcr.io/jelmer/prometheus-xmpp-alerts .
	docker push ghcr.io/jelmer/prometheus-xmpp-alerts
