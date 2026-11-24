from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from common.encryption import rotate_sensitive_ciphertext
from apps.accounts.models import User
from apps.customers.models import Customer
from apps.settings.models import ProviderConfiguration, SystemSetting


class Command(BaseCommand):
    help = "Re-encrypt supported sensitive fields with DJANGO_FIELD_ENCRYPTION_KEY."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=500)

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = max(1, min(options["batch_size"], 5000))
        targets = [
            (User, ("national_id_encrypted", "mfa_secret_encrypted")),
            (Customer, ("national_id_encrypted",)),
            (ProviderConfiguration, ("encrypted_credentials",)),
            (SystemSetting, ("encrypted_value",)),
        ]
        total = 0
        for model, fields in targets:
            qs = model._base_manager.all().only("pk", *fields).order_by("pk")
            for record in qs.iterator(chunk_size=batch_size):
                changed = []
                for field in fields:
                    value = getattr(record, field, "") or ""
                    if not value:
                        continue
                    try:
                        rotated = rotate_sensitive_ciphertext(value)
                    except Exception as exc:
                        raise CommandError(
                            f"Cannot rotate {model._meta.label} pk={record.pk} field={field}: {exc}"
                        ) from exc
                    if rotated != value:
                        setattr(record, field, rotated)
                        changed.append(field)
                if changed:
                    total += 1
                    if not dry_run:
                        record.save(update_fields=changed)
        self.stdout.write(self.style.SUCCESS(
            f"{'Would rotate' if dry_run else 'Rotated'} {total} records."
        ))
