"""
Email Delivery Service — sends CEO briefing via SMTP with attachment
(spec 007, US3 Email Delivery).

SMTP credentials are resolved in priority order:
  1. Explicit ``SMTPConfig`` passed to the constructor
  2. ``smtp`` section in ``config/briefing.yaml``
  3. Environment variables  (FTE_SMTP_SERVER, FTE_SMTP_PORT,
     FTE_SMTP_USERNAME, FTE_SMTP_PASSWORD, FTE_SMTP_FROM)

The service is a no-op (returns ``False``) when no SMTP server is
configured at all — it never raises on missing config.
"""

import mimetypes
import os
import smtplib
import ssl
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import yaml


class SMTPConfig:
    """Resolved SMTP connection settings."""

    def __init__(
        self,
        server: str,
        port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_addr: str = "fte@localhost",
        use_tls: bool = True,
    ):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.use_tls = use_tls


class EmailDeliveryService:
    """
    Send CEO briefing emails with attachments.

    Args:
        smtp_config: Pre-built SMTPConfig, or ``None`` to auto-resolve.
        config_path: Path to ``config/briefing.yaml`` (used when
                     *smtp_config* is ``None``).  Defaults to
                     ``config/briefing.yaml`` relative to CWD.
    """

    def __init__(
        self,
        smtp_config: Optional[SMTPConfig] = None,
        config_path: Optional[Path] = None,
    ):
        self._config = smtp_config or self._resolve_config(config_path)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def send_briefing_email(
        self,
        recipient: str,
        attachment_path: Path,
        period_start: datetime,
        period_end: datetime,
        highlights: Optional[list[str]] = None,
    ) -> bool:
        """
        Send briefing email with the given file as attachment.

        Args:
            recipient:        Target email address.
            attachment_path:  Path to ``.md`` or ``.pdf`` briefing file.
            period_start:     Briefing period start.
            period_end:       Briefing period end.
            highlights:       Optional bullet-point highlights for email body.

        Returns:
            ``True`` on successful delivery, ``False`` when SMTP is not
            configured or any error occurs.
        """
        if not self._config:
            return False

        subject = (
            f"Monday Morning CEO Briefing \u2014 "
            f"Week of {period_start.strftime('%b %d')}\u2013"
            f"{period_end.strftime('%b %d, %Y')}"
        )
        body_text = self._render_body(period_start, period_end, highlights or [])
        msg = self._build_message(subject, body_text, recipient, attachment_path)

        try:
            if self._config.use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self._config.server, self._config.port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    if self._config.username and self._config.password:
                        server.login(self._config.username, self._config.password)
                    server.sendmail(self._config.from_addr, [recipient], msg.as_string())
            else:
                with smtplib.SMTP(self._config.server, self._config.port, timeout=10) as server:
                    if self._config.username and self._config.password:
                        server.login(self._config.username, self._config.password)
                    server.sendmail(self._config.from_addr, [recipient], msg.as_string())
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    def _build_message(
        self, subject: str, body_text: str, recipient: str, attachment_path: Path
    ) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = self._config.from_addr
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body_text, "plain"))

        mime_type, _ = mimetypes.guess_type(str(attachment_path))
        main_type, sub_type = (mime_type or "application/octet-stream").split("/", 1)
        part = MIMEBase(main_type, sub_type)
        part.set_payload(attachment_path.read_bytes())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={attachment_path.name}",
        )
        msg.attach(part)
        return msg

    # ------------------------------------------------------------------
    # Body rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _render_body(
        period_start: datetime, period_end: datetime, highlights: list[str]
    ) -> str:
        lines = [
            "Hello,",
            "",
            f"Attached is your weekly AI Employee performance summary for the week of "
            f"{period_start.strftime('%B %d')}\u2013{period_end.strftime('%B %d, %Y')}.",
            "",
        ]
        if highlights:
            lines.append("Key highlights:")
            for h in highlights:
                lines.append(f"  - {h}")
            lines.append("")
        lines.extend([
            "Please review the full briefing for insights and recommendations.",
            "",
            "Best regards,",
            "AI Employee (FTE v1.0)",
        ])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Config resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_config(config_path: Optional[Path] = None) -> Optional[SMTPConfig]:
        """Try YAML config first, then env vars.  Returns ``None`` when no server."""
        smtp_section: dict = {}

        path = config_path or Path("config") / "briefing.yaml"
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text()) or {}
                smtp_section = raw.get("smtp", {}) or {}
            except Exception:
                pass

        server = smtp_section.get("server") or os.environ.get("FTE_SMTP_SERVER")
        if not server:
            return None

        password = os.environ.get("FTE_SMTP_PASSWORD") or smtp_section.get("password") or ""
        username = os.environ.get("FTE_SMTP_USERNAME") or smtp_section.get("username")

        return SMTPConfig(
            server=server,
            port=int(smtp_section.get("port", os.environ.get("FTE_SMTP_PORT", "587"))),
            username=username,
            password=password,
            from_addr=smtp_section.get("from", os.environ.get("FTE_SMTP_FROM", "fte@localhost")),
            use_tls=smtp_section.get("use_tls", True),
        )
