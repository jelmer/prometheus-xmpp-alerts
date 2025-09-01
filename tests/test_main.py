# __init__.py -- The tests for prometheus_xmpp
# Copyright (C) 2018, 2025 Jelmer Vernooij <jelmer@jelmer.uk>
#

import os
import tempfile
import unittest
from prometheus_xmpp.__main__ import parse_args


class TestParseArgs(unittest.TestCase):
    def test_parse_args_env(self):
        (jid, password_cb, recipients, config) = parse_args(
            [],
            env={
                "XMPP_ID": "foo@bar",
                "XMPP_PASS": "baz",
                "XMPP_AMTOOL_ALLOWED": "jelmer@jelmer.uk",
                "XMPP_RECIPIENTS": "foo@bar.com",
            },
        )

        self.assertTrue(jid.startswith("foo@bar/"))
        self.assertEqual(password_cb(), "baz")
        self.assertEqual(recipients, [("foo@bar.com", "chat")])
        self.assertEqual(config["amtool_allowed"], ["jelmer@jelmer.uk"])

    def test_parse_args_config(self):
        f = tempfile.NamedTemporaryFile(delete=False)
        self.addCleanup(os.remove, f.name)
        f.write(b"""\
jid: foo@bar
password: baz
to_jid: jelmer@jelmer.uk
amtool_allowed: foo@example.com
""")
        f.flush()
        f.close()
        (jid, password_cb, recipients, config) = parse_args(
            ["--config", f.name], env={}
        )

        self.assertTrue(jid.startswith("foo@bar/"))
        self.assertEqual(password_cb(), "baz")
        self.assertEqual(recipients, [("jelmer@jelmer.uk", "chat")])
        self.assertEqual(config["amtool_allowed"], ["foo@example.com"])
