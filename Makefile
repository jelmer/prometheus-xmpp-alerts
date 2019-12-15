all: check flake8

check:
	python3 -m unittest prometheus_xmpp.tests.test_suite

flake8:
	flake8

.PHONY: all flake8 check
