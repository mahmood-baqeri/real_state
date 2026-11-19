# Path: backend/django_core/integrations/sms.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SMSDeliveryResult:
    accepted: bool
    provider_message_id: str
    provider_key: str


class SMSProviderBase(ABC):
    provider_key: str

    @abstractmethod
    def send_sms(
        self, phone_number: str, message: str, sender_line: Optional[str] = None
    ) -> SMSDeliveryResult:
        raise NotImplementedError

    @abstractmethod
    def send_otp(
        self, phone_number: str, template_key: str, tokens: Dict[str, str]
    ) -> SMSDeliveryResult:
        raise NotImplementedError


class ConsoleSMSAdapter(SMSProviderBase):
    provider_key = "console"

    def send_sms(
        self, phone_number: str, message: str, sender_line: Optional[str] = None
    ) -> SMSDeliveryResult:
        logger.info("[ConsoleSMS] to=%s msg=%s", phone_number, message)
        return SMSDeliveryResult(
            accepted=True,
            provider_message_id=f"console-sms-{abs(hash(phone_number + message)) % 100000}",
            provider_key=self.provider_key,
        )

    def send_otp(
        self, phone_number: str, template_key: str, tokens: Dict[str, str]
    ) -> SMSDeliveryResult:
        logger.info("[ConsoleOTP] to=%s template=%s tokens=%s", phone_number, template_key, tokens)
        return SMSDeliveryResult(
            accepted=True,
            provider_message_id=f"console-otp-{abs(hash(phone_number + template_key)) % 100000}",
            provider_key=self.provider_key,
        )
