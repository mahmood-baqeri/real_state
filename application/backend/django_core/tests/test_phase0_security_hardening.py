from django.test import override_settings
from django.core.exceptions import PermissionDenied
from cryptography.fernet import Fernet
import pytest

from common.exceptions import ValidationDomainError
from common.tenant.rls import generate_rls_policy_sql
from common.tenant.context import tenant_bypass, set_current_agency_id
from common.encryption import encrypt_sensitive_value, decrypt_sensitive_value, rotate_sensitive_ciphertext
from integrations.storage import LocalSecureStorageAdapter
from apps.properties.models import Property


@pytest.mark.parametrize("public_policy", [False, True])
def test_s3_verifier_distinguishes_missing_policy_from_public_policy(monkeypatch, public_policy):
    """نبود سیاست سطل قابل قبول است و سیاست عمومی باعث رد بررسی می‌شود."""
    from io import StringIO
    from unittest.mock import Mock
    import boto3
    from botocore.exceptions import ClientError
    from django.core.management import call_command
    from django.core.management.base import CommandError

    client = Mock()
    client.get_public_access_block.return_value = {"PublicAccessBlockConfiguration": {
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
    }}
    client.get_bucket_acl.return_value = {"Grants": []}
    if public_policy:
        client.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": True}}
    else:
        client.get_bucket_policy_status.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucketPolicy"}}, "GetBucketPolicyStatus",
        )
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: client)
    with override_settings(
        ACTIVE_STORAGE_PROVIDER="s3", S3_PRIVATE_BUCKET_NAME="private-test", S3_BUCKET_NAME="public-test",
    ):
        if public_policy:
            with pytest.raises(CommandError, match="public bucket policy"):
                call_command("verify_storage_security", stdout=StringIO())
        else:
            call_command("verify_storage_security", stdout=StringIO())


def test_legal_section_normalization_preserves_text_and_sanitizes_html():
    """عنوان متنی و محتوای نسخه‌های قدیمی برای نمایش ایمن آماده می‌شوند."""
    from apps.cms.services import _render_sections_html, normalize_legal_sections

    sections = normalize_legal_sections([
        {"title": "شرایط <جدید>", "body_html": '<p onclick="example">متن</p>', "sort_order": "legacy"},
    ])
    assert _render_sections_html(sections) == "<h3>شرایط &lt;جدید&gt;</h3><p>متن</p>"


def test_rls_policy_is_fail_closed_and_checks_write_path():
    sql = generate_rls_policy_sql("example_tenant_table")
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "app.current_agency_id" in sql
    assert "IS NOT NULL" in sql
    assert "WITH CHECK" in sql
    assert "app.tenant_bypass" in sql
    assert "FORCE ROW LEVEL SECURITY" not in sql


def test_rls_policy_rejects_unsafe_identifiers():
    with pytest.raises(ValueError):
        generate_rls_policy_sql('example; DROP TABLE users;--')


def test_tenant_bypass_requires_allowlisted_reason():
    with pytest.raises(PermissionError):
        with tenant_bypass(reason="arbitrary"):
            pass


def test_tenant_scoped_manager_rejects_missing_context():
    set_current_agency_id(None)
    with pytest.raises(PermissionDenied):
        Property.objects.all()


def test_storage_separates_public_and_private_roots_and_rejects_traversal(tmp_path):
    public_root = tmp_path / "public"
    private_root = tmp_path / "private"
    with override_settings(
        MEDIA_ROOT=public_root,
        PRIVATE_MEDIA_ROOT=private_root,
        MEDIA_URL="/media/",
    ):
        storage = LocalSecureStorageAdapter()
        public = storage.put_bytes(
            key_prefix="public/listings", safe_filename="cover.jpg",
            content=b"public", mime_type="image/jpeg",
        )
        private = storage.put_bytes(
            key_prefix="private/agencies/a/documents", safe_filename="deed.pdf",
            content=b"private", mime_type="application/pdf",
        )
        assert public.url == "/media/public/listings/cover.jpg"
        assert private.url == ""
        assert (public_root / "public/listings/cover.jpg").read_bytes() == b"public"
        assert (private_root / "agencies/a/documents/deed.pdf").read_bytes() == b"private"
        with pytest.raises(ValidationDomainError):
            storage.get_bytes(file_key="../private/secret.txt")
        with pytest.raises(ValidationDomainError):
            storage.get_bytes(file_key="..\\\\private\\\\secret.txt")


def test_encryption_key_rotation_reads_legacy_and_rewrites_with_active_key():
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    with override_settings(
        DEBUG=False,
        SECRET_KEY="not-used-in-production",
        FIELD_ENCRYPTION_KEY=old_key,
        FIELD_ENCRYPTION_FALLBACK_KEYS=[],
        FIELD_ENCRYPTION_LEGACY_SECRET_KEYS=[],
    ):
        old_ciphertext = encrypt_sensitive_value("sensitive-value")
    with override_settings(
        DEBUG=False,
        SECRET_KEY="not-used-in-production",
        FIELD_ENCRYPTION_KEY=new_key,
        FIELD_ENCRYPTION_FALLBACK_KEYS=[old_key],
        FIELD_ENCRYPTION_LEGACY_SECRET_KEYS=[],
    ):
        assert decrypt_sensitive_value(old_ciphertext) == "sensitive-value"
        rotated = rotate_sensitive_ciphertext(old_ciphertext)
        assert decrypt_sensitive_value(rotated) == "sensitive-value"
        assert rotated != old_ciphertext


def test_legacy_public_private_prefix_is_migratable(tmp_path):
    public_root = tmp_path / "public"
    private_root = tmp_path / "private"
    with override_settings(MEDIA_ROOT=public_root, PRIVATE_MEDIA_ROOT=private_root):
        storage = LocalSecureStorageAdapter()
        legacy = public_root / "private/virtual_tours/legacy.bin"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_bytes(b"legacy-private")
        with pytest.raises(FileNotFoundError):
            storage.get_bytes(file_key="private/virtual_tours/legacy.bin")
        assert storage.get_legacy_public_bytes(
            file_key="private/virtual_tours/legacy.bin"
        ) == b"legacy-private"
        storage.delete_legacy_public_object(file_key="private/virtual_tours/legacy.bin")
        assert not legacy.exists()
