# __init__.py -- The tests for prometheus_xmpp
# Copyright (C) 2018, 2025 Jelmer Vernooij <jelmer@jelmer.uk>
#

import logging
import os
import tempfile
import unittest
from unittest import IsolatedAsyncioTestCase
from prometheus_xmpp.__main__ import (
    parse_args,
    render_alert,
    DEFAULT_HTML_TEMPLATE,
    DEFAULT_TEXT_TEMPLATE,
    EXAMPLE_ALERT,
)
from prometheus_xmpp import render_html_template, render_text_template, strip_html_tags


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


class TestRenderTextTemplate(unittest.TestCase):
    def test_render_text_template_basic(self):
        """Test basic text template rendering with simple alert."""
        template = "{{ status.upper() }}: {{ labels.alertname }}"
        alert = {
            "status": "firing",
            "labels": {"alertname": "TestAlert"},
            "annotations": {},
        }
        result = render_text_template(template, alert)
        self.assertEqual(result, "FIRING: TestAlert")

    def test_render_text_template_with_annotations(self):
        """Test text template rendering with annotations."""
        template = "{{ annotations.message }}"
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {"message": "Test message"},
        }
        result = render_text_template(template, alert)
        self.assertEqual(result, "Test message")

    def test_render_text_template_with_host(self):
        """Test text template rendering with host label."""
        template = "{{ labels.alertname }} at {{ labels.host }}"
        alert = {
            "status": "firing",
            "labels": {"alertname": "HostDown", "host": "server1.example.com"},
            "annotations": {},
        }
        result = render_text_template(template, alert)
        self.assertEqual(result, "HostDown at server1.example.com")

    def test_render_text_template_with_instance(self):
        """Test text template rendering with instance label."""
        template = "{{ labels.alertname }} at {{ labels.instance }}"
        alert = {
            "status": "firing",
            "labels": {"alertname": "ServiceDown", "instance": "localhost:8080"},
            "annotations": {},
        }
        result = render_text_template(template, alert)
        self.assertEqual(result, "ServiceDown at localhost:8080")

    def test_render_text_template_multiline_annotation(self):
        """Test text template with multiline annotation."""
        template = "{{ annotations.description }}"
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {"description": "Line 1\nLine 2\nLine 3"},
        }
        result = render_text_template(template, alert)
        self.assertEqual(result, "Line 1\nLine 2\nLine 3")

    def test_render_text_template_default_template(self):
        """Test rendering with default text template."""
        result = render_text_template(DEFAULT_TEXT_TEMPLATE, EXAMPLE_ALERT)
        expected = """FIRING:*Test*at localhost:1337

normally there would be details
in this multi-line description

Link: http://example.com:9090/graph?g0.expr=someexpr"""
        self.assertEqual(result, expected)

    def test_render_text_template_resolved_status(self):
        """Test text template rendering with resolved status."""
        template = "{{ status.upper() }}: {{ labels.alertname }}"
        alert = {
            "status": "resolved",
            "labels": {"alertname": "TestAlert"},
            "annotations": {},
        }
        result = render_text_template(template, alert)
        self.assertEqual(result, "RESOLVED: TestAlert")

    def test_render_text_template_invalid_syntax(self):
        """Test text template rendering with invalid syntax returns error message."""
        template = "{{ invalid syntax"
        alert = {"status": "firing", "labels": {}, "annotations": {}}
        with self.assertLogs(level=logging.WARNING) as cm:
            result = render_text_template(template, alert)
        self.assertIn("Failed to render text template", result)
        self.assertEqual(len(cm.output), 1)
        self.assertIn("Alert that failed to render", cm.output[0])


class TestRenderHtmlTemplate(unittest.TestCase):
    def test_render_html_template_basic(self):
        """Test basic HTML template rendering."""
        template = "<strong>{{ status.upper() }}</strong>"
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {},
        }
        result = render_html_template(template, alert)
        self.assertEqual(result, "<strong>FIRING</strong>")

    def test_render_html_template_with_link(self):
        """Test HTML template rendering with link."""
        template = '<a href="{{ generatorURL }}">Alert</a>'
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {},
            "generatorURL": "http://example.com/alert",
        }
        result = render_html_template(template, alert)
        self.assertEqual(result, '<a href="http://example.com/alert">Alert</a>')

    def test_render_html_template_with_severity_color(self):
        """Test HTML template rendering with severity-based coloring."""
        template = '<span style="color:{% if labels.severity == "warning" %}#ffc107{% else %}#dc3545{% endif %}">{{ labels.severity.upper() }}</span>'
        alert = {
            "status": "firing",
            "labels": {"severity": "warning"},
            "annotations": {},
        }
        result = render_html_template(template, alert)
        self.assertEqual(result, '<span style="color:#ffc107">WARNING</span>')

    def test_render_html_template_with_line_breaks(self):
        """Test HTML template with line break replacement."""
        template = '{{ annotations.message.replace("\\n", "<br/>") }}'
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {"message": "Line 1\nLine 2"},
        }
        result = render_html_template(template, alert)
        self.assertEqual(result, "Line 1<br/>Line 2")

    def test_render_html_template_default_template(self):
        """Test rendering with default HTML template."""
        result = render_html_template(DEFAULT_HTML_TEMPLATE, EXAMPLE_ALERT)
        expected = """
<strong><span style="color:#dc3545
">FIRING:</span></strong>

<i>Test</i>
at localhost:1337

<br/>normally there would be details
in this multi-line description
<br/><a href="http://example.com:9090/graph?g0.expr=someexpr">Alert link</a>"""
        self.assertEqual(result, expected)

    def test_render_html_template_resolved_status(self):
        """Test HTML template rendering with resolved status."""
        template = """{% if status == 'resolved' %}<span style="color:green">RESOLVED</span>{% endif %}"""
        alert = {
            "status": "resolved",
            "labels": {},
            "annotations": {},
        }
        result = render_html_template(template, alert)
        self.assertEqual(result, '<span style="color:green">RESOLVED</span>')

    def test_render_html_template_invalid_syntax(self):
        """Test HTML template rendering with invalid syntax returns error message."""
        template = "{{ invalid syntax"
        alert = {"status": "firing", "labels": {}, "annotations": {}}
        with self.assertLogs(level=logging.WARNING) as cm:
            result = render_html_template(template, alert)
        self.assertIn("Failed to render HTML template", result)
        self.assertEqual(len(cm.output), 1)
        self.assertIn("Alert that failed to render", cm.output[0])

    def test_render_html_template_invalid_html(self):
        """Test HTML template rendering with invalid HTML returns error message."""
        template = "<div>unclosed div"
        alert = {"status": "firing", "labels": {}, "annotations": {}}
        result = render_html_template(template, alert)
        self.assertIn("Failed to render HTML", result)
        self.assertIn("unclosed div", result)


class TestStripHtmlTags(unittest.TestCase):
    def test_strip_html_tags_simple(self):
        """Test stripping simple HTML tags."""
        html = "<strong>Bold text</strong>"
        result = strip_html_tags(html)
        self.assertEqual(result, "Bold text")

    def test_strip_html_tags_multiple_tags(self):
        """Test stripping multiple HTML tags."""
        html = "<p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>"
        result = strip_html_tags(html)
        self.assertEqual(result, "Paragraph with bold and italic text.")

    def test_strip_html_tags_with_links(self):
        """Test stripping HTML tags including links."""
        html = 'Visit <a href="http://example.com">this link</a> for more info.'
        result = strip_html_tags(html)
        self.assertEqual(result, "Visit this link for more info.")

    def test_strip_html_tags_with_br(self):
        """Test stripping HTML tags with line breaks."""
        html = "Line 1<br/>Line 2<br/>Line 3"
        result = strip_html_tags(html)
        self.assertEqual(result, "Line 1Line 2Line 3")


class TestRenderAlert(IsolatedAsyncioTestCase):
    async def test_render_alert_both_templates(self):
        """Test render_alert with both HTML and text templates."""
        text_template = "TEXT: {{ status.upper() }}"
        html_template = "<strong>HTML: {{ status.upper() }}</strong>"
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {},
        }

        text, html = await render_alert(text_template, html_template, alert)

        self.assertEqual(text, "TEXT: FIRING")
        self.assertEqual(html, "<strong>HTML: FIRING</strong>")

    async def test_render_alert_html_only(self):
        """Test render_alert with only HTML template (text is stripped HTML)."""
        html_template = "<strong>FIRING</strong>: Alert message"
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {},
        }

        text, html = await render_alert(None, html_template, alert)

        self.assertEqual(html, "<strong>FIRING</strong>: Alert message")
        self.assertEqual(text, "FIRING: Alert message")

    async def test_render_alert_text_only(self):
        """Test render_alert with only text template."""
        text_template = "TEXT: {{ status.upper() }}"
        alert = {
            "status": "firing",
            "labels": {},
            "annotations": {},
        }

        text, html = await render_alert(text_template, None, alert)

        self.assertEqual(text, "TEXT: FIRING")
        self.assertIsNone(html)

    async def test_render_alert_no_templates(self):
        """Test render_alert with no templates (uses defaults)."""
        alert = EXAMPLE_ALERT

        text, html = await render_alert(None, None, alert)

        expected_text = """FIRING:*Test*at localhost:1337

normally there would be details
in this multi-line description

Link: http://example.com:9090/graph?g0.expr=someexpr"""
        expected_html = """
<strong><span style="color:#dc3545
">FIRING:</span></strong>

<i>Test</i>
at localhost:1337

<br/>normally there would be details
in this multi-line description
<br/><a href="http://example.com:9090/graph?g0.expr=someexpr">Alert link</a>"""

        self.assertEqual(text, expected_text)
        self.assertEqual(html, expected_html)

    async def test_render_alert_with_severity_warning(self):
        """Test render_alert with warning severity."""
        alert = {
            "status": "firing",
            "labels": {"severity": "warning", "alertname": "WarningAlert"},
            "annotations": {"message": "This is a warning"},
            "generatorURL": "http://example.com",
        }

        text, html = await render_alert(None, None, alert)

        expected_text = """FIRING:*WarningAlert*
This is a warning


Link: http://example.com"""
        expected_html = """
<strong><span style="color:#ffc107
">FIRING:</span></strong>

<i>WarningAlert</i>

<br/>This is a warning

<br/><a href="http://example.com">Alert link</a>"""

        self.assertEqual(text, expected_text)
        self.assertEqual(html, expected_html)

    async def test_render_alert_with_description(self):
        """Test render_alert with description annotation."""
        alert = {
            "status": "firing",
            "labels": {"alertname": "TestAlert"},
            "annotations": {"description": "Detailed description here"},
            "generatorURL": "http://example.com",
        }

        text, html = await render_alert(None, None, alert)

        expected_text = """FIRING:*TestAlert*

Detailed description here

Link: http://example.com"""
        expected_html = """
<strong><span style="color:#dc3545
">FIRING:</span></strong>

<i>TestAlert</i>


<br/>Detailed description here
<br/><a href="http://example.com">Alert link</a>"""

        self.assertEqual(text, expected_text)
        self.assertEqual(html, expected_html)
