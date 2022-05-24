#!/usr/bin/python3
# encoding: utf-8
# Setup file for prometheus-xmpp-alerts
# Copyright (C) 2016-2018 Jelmer Vernooĳ <jelmer@jelmer.uk>

from setuptools import setup

setup(name='prometheus-xmpp-alerts',
      author="Jelmer Vernooij",
      author_email="jelmer@jelmer.uk",
      url="https://jelmer.uk/code/prometheus-xmpp-alerts",
      description="Prometheus XMPP Alerts hook",
      version='0.5.4',
      license='Apachev2',
      project_urls={
          "Bug Tracker":
              "https://github.com/jelmer/prometheus-xmpp-alerts/issues",
          "Repository": "https://www.jelmer.uk/code/prometheus-xmpp-alerts",
          "GitHub": "https://github.com/jelmer/prometheus-xmpp-alerts",
      },
      keywords="prometheus xmpp jabber",
      packages=['prometheus_xmpp'],
      scripts=['prometheus-xmpp-alerts'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Operating System :: POSIX',
          'Operating System :: Microsoft :: Windows',
          'Topic :: Software Development :: Version Control',
      ],
      install_requires=[
          'slixmpp',
          'aiohttp',
          'pytz',
          'pyyaml',
          'prometheus_client',
      ],
      tests_require=['pytz'],
      )
