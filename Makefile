all: check

check:
	python3 -m unittest prometheus_xmpp.tests.test_suite
