"""بررسی جداسازی ریشه‌های فایل و کنترل دسترسی مخزن خصوصی."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path


class Command(BaseCommand):
    """تنظیمات مخزن محلی یا سیاست‌های واقعی سطل S3 را بررسی می‌کند."""
    help = "Verify private storage isolation and, for S3, the actual private bucket public-access controls."

    def handle(self, *args, **options):
        """در صورت هم‌پوشانی ریشه‌ها یا دسترسی عمومی سطل خصوصی خطا می‌دهد."""
        public_root = Path(settings.MEDIA_ROOT).resolve()
        private_root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
        if public_root == private_root or public_root in private_root.parents or private_root in public_root.parents:
            raise CommandError("PUBLIC_MEDIA_ROOT and PRIVATE_MEDIA_ROOT overlap.")

        provider = getattr(settings, "ACTIVE_STORAGE_PROVIDER", "local")
        if provider == "s3":
            private_bucket = getattr(settings, "S3_PRIVATE_BUCKET_NAME", "")
            public_bucket = getattr(settings, "S3_BUCKET_NAME", "")
            if not private_bucket or private_bucket == public_bucket:
                raise CommandError("S3 private bucket must be set and different from the public bucket.")
            try:
                import boto3
                from botocore.exceptions import ClientError
                client = boto3.client(
                    "s3",
                    endpoint_url=getattr(settings, "S3_ENDPOINT_URL", None) or None,
                    aws_access_key_id=getattr(settings, "S3_ACCESS_KEY_ID", ""),
                    aws_secret_access_key=getattr(settings, "S3_SECRET_ACCESS_KEY", ""),
                    region_name=getattr(settings, "S3_REGION", "us-east-1"),
                )
                block = client.get_public_access_block(Bucket=private_bucket)["PublicAccessBlockConfiguration"]
                required = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
                unsafe = [name for name in required if not block.get(name)]
                if unsafe:
                    raise CommandError("Private S3 bucket public-access block is incomplete: " + ", ".join(unsafe))
                try:
                    status = client.get_bucket_policy_status(Bucket=private_bucket).get("PolicyStatus", {})
                    if status.get("IsPublic"):
                        raise CommandError("Private S3 bucket has a public bucket policy.")
                except ClientError as exc:
                    if exc.response.get("Error", {}).get("Code") != "NoSuchBucketPolicy":
                        raise
                acl = client.get_bucket_acl(Bucket=private_bucket)
                public_grants = [g for g in acl.get("Grants", []) if g.get("Grantee", {}).get("URI", "").endswith(("/AllUsers", "/AuthenticatedUsers"))]
                if public_grants:
                    raise CommandError("Private S3 bucket ACL contains public grants.")
            except CommandError:
                raise
            except Exception as exc:
                raise CommandError(f"Could not verify private S3 bucket controls: {exc}") from exc
        elif provider != "local":
            raise CommandError(f"Unknown storage provider: {provider!r}")

        self.stdout.write(self.style.SUCCESS(
            f"Storage isolation verified: public={public_root}, private={private_root}, provider={provider}."
        ))
