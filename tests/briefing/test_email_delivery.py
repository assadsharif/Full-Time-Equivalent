"""Tests for email delivery service (spec 007 US3)."""

import smtplib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.briefing.email_delivery import EmailDeliveryService, SMTPConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def smtp_cfg():
    return SMTPConfig(
        server="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secret",
        from_addr="fte@example.com",
        use_tls=True,
    )


@pytest.fixture
def svc(smtp_cfg):
    return EmailDeliveryService(smtp_config=smtp_cfg)


@pytest.fixture
def briefing_md(tmp_path):
    p = tmp_path / "briefing_2026-01-29.md"
    p.write_text("# Weekly CEO Briefing\n\nSome content here.\n")
    return p


@pytest.fixture
def briefing_pdf(tmp_path):
    p = tmp_path / "briefing_2026-01-29.pdf"
    p.write_bytes(b"%PDF-1.4 fake pdf content for testing")
    return p


def _period():
    return (
        datetime(2026, 1, 22, tzinfo=timezone.utc),
        datetime(2026, 1, 28, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


class TestSMTPConfigResolution:
    def test_no_config_no_env_returns_none(self, tmp_path):
        svc = EmailDeliveryService(config_path=tmp_path / "nonexistent.yaml")
        assert svc._config is None

    def test_config_from_yaml(self, tmp_path):
        cfg = tmp_path / "briefing.yaml"
        cfg.write_text(
            "smtp:\n"
            "  server: smtp.test.com\n"
            "  port: 465\n"
            "  username: u\n"
            "  from: hello@test.com\n"
            "  use_tls: false\n"
        )
        svc = EmailDeliveryService(config_path=cfg)
        assert svc._config.server == "smtp.test.com"
        assert svc._config.port == 465
        assert svc._config.use_tls is False

    def test_env_var_overrides_password(self, tmp_path, monkeypatch):
        cfg = tmp_path / "briefing.yaml"
        cfg.write_text("smtp:\n  server: smtp.x.com\n  password: yaml_pass\n")
        monkeypatch.setenv("FTE_SMTP_PASSWORD", "env_pass")
        svc = EmailDeliveryService(config_path=cfg)
        assert svc._config.password == "env_pass"

    def test_env_var_server_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FTE_SMTP_SERVER", "env.smtp.com")
        svc = EmailDeliveryService(config_path=tmp_path / "none.yaml")
        assert svc._config.server == "env.smtp.com"


# ---------------------------------------------------------------------------
# No-op when unconfigured
# ---------------------------------------------------------------------------


class TestNoSmtpNoOp:
    def test_send_returns_false_when_no_config(self, briefing_md):
        svc = EmailDeliveryService(smtp_config=None, config_path=Path("/nonexistent"))
        start, end = _period()
        assert svc.send_briefing_email("x@y.com", briefing_md, start, end) is False


# ---------------------------------------------------------------------------
# Body rendering
# ---------------------------------------------------------------------------


class TestBodyRendering:
    def test_render_body_with_highlights(self):
        start, end = _period()
        body = EmailDeliveryService._render_body(
            start, end, ["47 tasks completed", "100% SLA"]
        )
        assert "47 tasks completed" in body
        assert "100% SLA" in body
        assert "January 22" in body
        assert "January 28" in body

    def test_render_body_no_highlights(self):
        start, end = _period()
        body = EmailDeliveryService._render_body(start, end, [])
        assert "Key highlights" not in body
        assert "AI Employee (FTE v1.0)" in body


# ---------------------------------------------------------------------------
# SMTP send (mocked)
# ---------------------------------------------------------------------------


def _mock_smtp(mock_smtp_cls):
    """Wire mock_smtp_cls so the context-manager pattern works."""
    server = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
    return server


def _decode_subject(raw_msg: str) -> str:
    """Decode an RFC2047 Subject header from the raw MIME string."""
    from email import message_from_string
    from email.header import decode_header

    msg = message_from_string(raw_msg)
    parts = decode_header(msg["Subject"])
    return " ".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in parts
    )


def _decode_text_body(raw_msg: str) -> str:
    """Extract and decode the text/plain body from a MIME message."""
    from email import message_from_string

    msg = message_from_string(raw_msg)
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            return part.get_payload(decode=True).decode("utf-8")
    return ""


class TestSMTPSend:
    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_send_md_returns_true(self, mock_smtp_cls, svc, briefing_md):
        _mock_smtp(mock_smtp_cls)
        start, end = _period()
        assert svc.send_briefing_email("ceo@x.com", briefing_md, start, end) is True

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_send_contains_attachment_name(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_md, start, end)
        sent_msg = server.sendmail.call_args[0][2]
        assert briefing_md.name in sent_msg

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_send_pdf_attachment(self, mock_smtp_cls, svc, briefing_pdf):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_pdf, start, end)
        sent_msg = server.sendmail.call_args[0][2]
        assert briefing_pdf.name in sent_msg

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_subject_contains_briefing_title(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_md, start, end)
        subject = _decode_subject(server.sendmail.call_args[0][2])
        assert "Monday Morning CEO Briefing" in subject

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_subject_contains_date_range(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_md, start, end)
        subject = _decode_subject(server.sendmail.call_args[0][2])
        assert "Jan 22" in subject

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_highlights_appear_in_body(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email(
            "ceo@x.com",
            briefing_md,
            start,
            end,
            highlights=["47 tasks done", "100% SLA"],
        )
        body = _decode_text_body(server.sendmail.call_args[0][2])
        assert "47 tasks done" in body
        assert "100% SLA" in body

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_returns_false_on_smtp_error(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        server.sendmail.side_effect = smtplib.SMTPRecipientsRefused(
            {"x@y.com": (550, b"rejected")}
        )
        start, end = _period()
        assert svc.send_briefing_email("x@y.com", briefing_md, start, end) is False

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_tls_calls_starttls_and_login(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_md, start, end)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("user@example.com", "secret")

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_no_tls_skips_starttls(self, mock_smtp_cls, briefing_md):
        cfg = SMTPConfig(server="smtp.x.com", port=25, use_tls=False)
        svc = EmailDeliveryService(smtp_config=cfg)
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_md, start, end)
        server.starttls.assert_not_called()

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_from_addr_used_as_sender(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_md, start, end)
        # First positional arg to sendmail is the from address
        assert server.sendmail.call_args[0][0] == "fte@example.com"

    @patch("src.briefing.email_delivery.smtplib.SMTP")
    def test_recipient_in_to_header(self, mock_smtp_cls, svc, briefing_md):
        server = _mock_smtp(mock_smtp_cls)
        start, end = _period()
        svc.send_briefing_email("ceo@x.com", briefing_md, start, end)
        sent_msg = server.sendmail.call_args[0][2]
        assert "ceo@x.com" in sent_msg
