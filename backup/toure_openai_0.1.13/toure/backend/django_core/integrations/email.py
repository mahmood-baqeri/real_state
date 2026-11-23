from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage
import logging
import os
import smtplib
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailDeliveryResult:
    accepted: bool
    provider_message_id: str
    provider_key: str


class EmailProviderBase(ABC):
    provider_key: str

    @abstractmethod
    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> EmailDeliveryResult:
        raise NotImplementedError


class ConsoleEmailAdapter(EmailProviderBase):
    provider_key = "console"

    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> EmailDeliveryResult:
        logger.info("[ConsoleEmail] to=%s subject=%s", to_email, subject)
        return EmailDeliveryResult(
            accepted=True,
            provider_message_id=f"console-mail-{abs(hash(to_email + subject)) % 1000000}",
            provider_key=self.provider_key,
        )


class SMTPEmailAdapter(EmailProviderBase):
    provider_key = "smtp"

    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> EmailDeliveryResult:
        host = os.environ.get("EMAIL_HOST", "")
        port = int(os.environ.get("EMAIL_PORT", "587"))
        user = os.environ.get("EMAIL_HOST_USER", "")
        password = os.environ.get("EMAIL_HOST_PASSWORD", "")
        sender = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@bonyanmelk.ir")
        if not host:
            raise RuntimeError("SMTP host is not configured.")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)

        return EmailDeliveryResult(
            accepted=True,
            provider_message_id=f"smtp-{abs(hash(to_email + subject)) % 1000000}",
            provider_key=self.provider_key,
        )
