import base64
import hashlib
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _derive_legacy_key(secret: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest()).decode("ascii")


def _get_fernet() -> MultiFernet:
    active = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    fallback = list(getattr(settings, "FIELD_ENCRYPTION_FALLBACK_KEYS", []) or [])
    legacy_secrets = list(getattr(settings, "FIELD_ENCRYPTION_LEGACY_SECRET_KEYS", []) or [])
    if not active:
        if getattr(settings, "DEBUG", False):
            active = _derive_legacy_key(settings.SECRET_KEY)
        else:
            raise ImproperlyConfigured("DJANGO_FIELD_ENCRYPTION_KEY is required.")
    try:
        keys = [Fernet(active.encode("ascii"))]
        keys.extend(Fernet(key.encode("ascii")) for key in fallback)
        keys.extend(Fernet(_derive_legacy_key(secret).encode("ascii")) for secret in legacy_secrets)
        return MultiFernet(keys)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured("A configured field-encryption key is invalid.") from exc


def encrypt_sensitive_value(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_sensitive_value(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise InvalidToken("Ciphertext cannot be decrypted with active or fallback keys.") from exc


def rotate_sensitive_ciphertext(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _get_fernet().rotate(ciphertext.encode("ascii")).decode("ascii")
    except InvalidToken as exc:
        raise InvalidToken("Ciphertext cannot be rotated; configure the previous key as fallback.") from exc
