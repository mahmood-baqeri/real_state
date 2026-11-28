from django.conf import settings
from .ai import AIProviderBase, GapGPTAdapter
from .analytics import AnalyticsProviderBase, InternalAnalyticsAdapter
from .email import ConsoleEmailAdapter, EmailProviderBase, SMTPEmailAdapter
from .maps import (
    CartoPositronAdapter,
    CustomTileMapAdapter,
    MapProviderBase,
    NeshanMapAdapter,
    OpenStreetMapAdapter,
)
from .payment import (
    IDPayPaymentAdapter,
    PaymentProviderBase,
    SandboxPaymentAdapter,
    ZarinpalPaymentAdapter,
    ZibalPaymentAdapter,
)
from .push import PushProviderBase, SandboxPushAdapter, WebPushVapidAdapter
from .sms import (
    ConsoleSMSAdapter,
    KavenegarSMSAdapter,
    MelipayamakSMSAdapter,
    SMSIrSMSAdapter,
    SMSProviderBase,
)
from .storage import LocalSecureStorageAdapter, StorageProviderBase

PAYMENT_PROVIDERS = {
    "sandbox": SandboxPaymentAdapter,
    "zarinpal": ZarinpalPaymentAdapter,
    "zibal": ZibalPaymentAdapter,
    "idpay": IDPayPaymentAdapter,
}

SMS_PROVIDERS = {
    "console": ConsoleSMSAdapter,
    "kavenegar": KavenegarSMSAdapter,
    "melipayamak": MelipayamakSMSAdapter,
    "smsir": SMSIrSMSAdapter,
}

EMAIL_PROVIDERS = {
    "console": ConsoleEmailAdapter,
    "smtp": SMTPEmailAdapter,
}

MAP_PROVIDERS = {
    "osm": OpenStreetMapAdapter,
    "carto": CartoPositronAdapter,
    "neshan": NeshanMapAdapter,
    "custom_tile": CustomTileMapAdapter,
}

AI_PROVIDERS = {
    "gapgpt": GapGPTAdapter,
}

STORAGE_PROVIDERS = {
    "local": LocalSecureStorageAdapter,
}

PUSH_PROVIDERS = {
    "sandbox": SandboxPushAdapter,
    "vapid": WebPushVapidAdapter,
}

ANALYTICS_PROVIDERS = {
    "internal": InternalAnalyticsAdapter,
}


def get_payment_provider(provider_key: str | None = None) -> PaymentProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_PAYMENT_PROVIDER", "sandbox")
    cls = PAYMENT_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown payment provider: {key}")
    return cls()


def get_sms_provider(provider_key: str | None = None) -> SMSProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_SMS_PROVIDER", "console")
    cls = SMS_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown SMS provider: {key}")
    return cls()


def get_email_provider(provider_key: str | None = None) -> EmailProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_EMAIL_PROVIDER", "console")
    cls = EMAIL_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown Email provider: {key}")
    return cls()


def get_map_provider(provider_key: str | None = None) -> MapProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_MAP_PROVIDER", "osm")
    cls = MAP_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown map provider: {key}")
    return cls()


def get_ai_provider(provider_key: str | None = None) -> AIProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_AI_PROVIDER", "gapgpt")
    cls = AI_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown AI provider: {key}")
    return cls()


def get_storage_provider(provider_key: str | None = None) -> StorageProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_STORAGE_PROVIDER", "local")
    cls = STORAGE_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown storage provider: {key}")
    return cls()


def get_push_provider(provider_key: str | None = None) -> PushProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_PUSH_PROVIDER", "sandbox")
    cls = PUSH_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown push provider: {key}")
    return cls()


def get_analytics_provider(provider_key: str | None = None) -> AnalyticsProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_ANALYTICS_PROVIDER", "internal")
    cls = ANALYTICS_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown analytics provider: {key}")
    return cls()
