from django.conf import settings
from .maps import MapProviderBase, OpenStreetMapAdapter
from .payment import PaymentProviderBase, SandboxPaymentAdapter
from .sms import ConsoleSMSAdapter, SMSProviderBase

PAYMENT_PROVIDERS = {
    "sandbox": SandboxPaymentAdapter,
}

SMS_PROVIDERS = {
    "console": ConsoleSMSAdapter,
}

MAP_PROVIDERS = {
    "osm": OpenStreetMapAdapter,
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


def get_map_provider(provider_key: str | None = None) -> MapProviderBase:
    key = provider_key or getattr(settings, "ACTIVE_MAP_PROVIDER", "osm")
    cls = MAP_PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"Unknown map provider: {key}")
    return cls()
