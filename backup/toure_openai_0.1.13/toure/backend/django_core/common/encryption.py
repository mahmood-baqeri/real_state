import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings


def _get_fernet() -> Fernet:
    configured = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if configured:
        try:
            return Fernet(configured.encode("utf-8"))
        except Exception:
            pass
    # Deterministic dev-only fallback derived from SECRET_KEY
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_sensitive_value(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_sensitive_value(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
