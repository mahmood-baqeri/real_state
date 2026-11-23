from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PushDeliveryResult:
    accepted: bool
    provider_key: str
    detail: str


class PushProviderBase(ABC):
    provider_key: str

    @abstractmethod
    def send_web_push(
        self,
        *,
        endpoint: str,
        p256dh: str,
        auth: str,
        title: str,
        body: str,
        url: str = "/dashboard/notifications",
    ) -> PushDeliveryResult:
        raise NotImplementedError


class SandboxPushAdapter(PushProviderBase):
    provider_key = "sandbox"

    def send_web_push(
        self,
        *,
        endpoint: str,
        p256dh: str,
        auth: str,
        title: str,
        body: str,
        url: str = "/dashboard/notifications",
    ) -> PushDeliveryResult:
        logger.info("[SandboxPush] endpoint=%s title=%s url=%s", endpoint[:48], title, url)
        return PushDeliveryResult(accepted=True, provider_key=self.provider_key, detail="sandbox_dispatched")


class WebPushVapidAdapter(PushProviderBase):
    provider_key = "vapid"

    def send_web_push(
        self,
        *,
        endpoint: str,
        p256dh: str,
        auth: str,
        title: str,
        body: str,
        url: str = "/dashboard/notifications",
    ) -> PushDeliveryResult:
        from pywebpush import webpush

        private_key = getattr(settings, "VAPID_PRIVATE_KEY", "")
        claims_email = getattr(settings, "VAPID_CLAIMS_EMAIL", "mailto:support@bonyanmelk.ir")
        if not private_key:
            raise RuntimeError("VAPID_PRIVATE_KEY is not configured.")

        payload = json.dumps({"title": title, "body": body, "url": url}, ensure_ascii=False)
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=payload,
            vapid_private_key=private_key,
            vapid_claims={"sub": claims_email},
            ttl=3600,
        )
        return PushDeliveryResult(accepted=True, provider_key=self.provider_key, detail="vapid_sent")
