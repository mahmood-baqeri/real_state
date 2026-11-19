# Path: backend/django_core/apps/accounts/models.py

import uuid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone as dj_timezone
from common.encryption import decrypt_sensitive_value, encrypt_sensitive_value


class UserManager(BaseUserManager):
    def create_user(self, phone_number: str, password: str | None = None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required.")
        email = extra_fields.get("email")
        if email:
            extra_fields["email"] = self.normalize_email(email)
        user = self.model(phone_number=phone_number.strip(), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        extra_fields.setdefault("platform_role", User.PlatformRole.SUPER_ADMIN)
        return self.create_user(phone_number=phone_number, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Verification"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        BANNED = "BANNED", "Banned"
        DELETED = "DELETED", "Soft Deleted"

    class PlatformRole(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        AGENCY_USER = "AGENCY_USER", "Agency Member"
        CUSTOMER = "CUSTOMER", "Customer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=24, unique=True, db_index=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=80, blank=True, default="")
    last_name = models.CharField(max_length=80, blank=True, default="")
    national_id_encrypted = models.TextField(blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")

    platform_role = models.CharField(
        max_length=24, choices=PlatformRole.choices, default=PlatformRole.CUSTOMER
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)

    preferred_language = models.CharField(max_length=8, default="fa")
    preferred_calendar = models.CharField(max_length=16, default="jalali")
    preferred_currency = models.CharField(max_length=10, default="IRT")
    timezone = models.CharField(max_length=64, default="UTC")

    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_mfa_enabled = models.BooleanField(default=False)
    mfa_secret_encrypted = models.TextField(blank=True, default="")

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.phone_number

    def set_national_id(self, raw_id: str) -> None:
        self.national_id_encrypted = encrypt_sensitive_value(raw_id)

    def get_national_id(self) -> str:
        return decrypt_sensitive_value(self.national_id_encrypted)

    def can_authenticate(self) -> bool:
        return self.is_active and self.status == self.Status.ACTIVE


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    jti = models.UUIDField(unique=True, default=uuid.uuid4)
    device_name = models.CharField(max_length=128, blank=True, default="Web Browser")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now)
    last_active_at = models.DateTimeField(default=dj_timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_user_session"


class LoginAttemptLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identifier = models.CharField(max_length=128, db_index=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    succeeded = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(default=dj_timezone.now, db_index=True)

    class Meta:
        db_table = "accounts_login_attempt_log"


class Permission(models.Model):
    code = models.CharField(max_length=100, primary_key=True)
    module = models.CharField(max_length=48, db_index=True)
    description = models.CharField(max_length=255)

    class Meta:
        db_table = "accounts_permission"


class Role(models.Model):
    class Scope(models.TextChoices):
        PLATFORM = "PLATFORM", "Platform"
        AGENCY = "AGENCY", "Agency"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=100)
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.AGENCY)
    agency = models.ForeignKey(
        "agencies.Agency",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="custom_roles",
    )
    is_system_role = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, through="RolePermission", blank=True)

    class Meta:
        db_table = "accounts_role"
        constraints = [
            models.UniqueConstraint(fields=["code", "agency"], name="uq_role_code_per_agency")
        ]


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = "accounts_role_permission"
        unique_together = ("role", "permission")


class AgencyMembership(models.Model):
    class Status(models.TextChoices):
        INVITED = "INVITED", "Invited"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        LEFT = "LEFT", "Left"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="memberships"
    )
    branch = models.ForeignKey(
        "branches.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="memberships",
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        db_table = "accounts_agency_membership"
        unique_together = ("user", "agency")


class MembershipPermissionOverride(models.Model):
    class Effect(models.TextChoices):
        ALLOW = "ALLOW", "Allow"
        DENY = "DENY", "Deny"

    membership = models.ForeignKey(
        AgencyMembership, on_delete=models.CASCADE, related_name="permission_overrides"
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    effect = models.CharField(max_length=8, choices=Effect.choices)

    class Meta:
        db_table = "accounts_membership_permission_override"
        unique_together = ("membership", "permission")
