PYTHON = python3

all: check flake8

check:
	$(PYTHON) -m unittest prometheus_xmpp.tests.test_suite

flake8:
	flake8

.PHONY: all flake8 check
