from decimal import Decimal
from django.conf import settings
from django.db import models
from common.models import BaseModel, SoftDeleteMixin, TenantScopedModel


class PropertyType(models.Model):
    code = models.CharField(max_length=48, primary_key=True)
    name_fa = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80)
    category = models.CharField(
        max_length=32,
        default="RESIDENTIAL",
        choices=[
            ("RESIDENTIAL", "Residential"),
            ("COMMERCIAL", "Commercial"),
            ("LAND", "Land"),
            ("INDUSTRIAL", "Industrial"),
            ("AGRICULTURAL", "Agricultural"),
            ("PROJECT", "Construction Project"),
        ],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "properties_type"


class DealType(models.Model):
    code = models.CharField(max_length=48, primary_key=True)
    name_fa = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80)
    is_rental = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "properties_deal_type"


class AmenityCategory(models.Model):
    code = models.CharField(max_length=48, primary_key=True)
    name_fa = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80, blank=True, default="")
    icon_name = models.CharField(max_length=48, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "properties_amenity_category"
        ordering = ["sort_order", "name_fa"]


class Amenity(models.Model):
    class ValueType(models.TextChoices):
        BOOLEAN = "BOOLEAN", "Boolean"
        INTEGER = "INTEGER", "Integer"
        TEXT = "TEXT", "Text"
        CHOICE = "CHOICE", "Choice"

    code = models.CharField(max_length=48, primary_key=True)
    category = models.ForeignKey(
        AmenityCategory,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="amenities",
    )
    name_fa = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80, blank=True, default="")
    icon_name = models.CharField(max_length=48, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    value_type = models.CharField(
        max_length=16, choices=ValueType.choices, default=ValueType.BOOLEAN
    )
    unit_label = models.CharField(max_length=32, blank=True, default="")
    options_json = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "properties_amenity"
        ordering = ["sort_order", "name_fa"]


class Property(TenantScopedModel, SoftDeleteMixin):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        PUBLISHED = "PUBLISHED", "Published"
        RESERVED = "RESERVED", "Reserved"
        UNDER_NEGOTIATION = "UNDER_NEGOTIATION", "Under Negotiation"
        SOLD = "SOLD", "Sold"
        RENTED = "RENTED", "Rented"
        EXPIRED = "EXPIRED", "Expired"
        INACTIVE = "INACTIVE", "Inactive"
        REJECTED = "REJECTED", "Rejected"
        ARCHIVED = "ARCHIVED", "Archived"

    class Visibility(models.TextChoices):
        PRIVATE_AGENCY = "PRIVATE_AGENCY", "Private Agency"
        PUBLIC_PORTAL = "PUBLIC_PORTAL", "Public Portal"
        MLS_SHARED = "MLS_SHARED", "MLS Shared"

    branch = models.ForeignKey(
        "branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="properties"
    )
    property_code = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    property_type = models.ForeignKey(PropertyType, on_delete=models.PROTECT)
    deal_type = models.ForeignKey(DealType, on_delete=models.PROTECT)
    usage_type = models.CharField(max_length=48, blank=True, default="مسکونی")

    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    visibility = models.CharField(
        max_length=24, choices=Visibility.choices, default=Visibility.PRIVATE_AGENCY
    )
    is_featured = models.BooleanField(default=False)

    # Physical Specs
    land_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    built_area_sqm = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)
    floor_number = models.SmallIntegerField(null=True, blank=True)
    total_floors = models.PositiveSmallIntegerField(null=True, blank=True)
    units_per_floor = models.PositiveSmallIntegerField(null=True, blank=True)
    building_age = models.PositiveSmallIntegerField(null=True, blank=True)
    construction_year = models.PositiveSmallIntegerField(null=True, blank=True)
    deed_type = models.CharField(max_length=64, blank=True, default="تک‌برگ")
    deed_status = models.CharField(max_length=64, blank=True, default="آزاد")
    orientation = models.CharField(max_length=48, blank=True, default="")
    facade_type = models.CharField(max_length=48, blank=True, default="")
    renovation_status = models.CharField(max_length=48, blank=True, default="")
    evacuation_status = models.CharField(max_length=48, blank=True, default="")
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="properties")

    # Financial Fields (Strictly Decimal)
    currency = models.ForeignKey("settings.Currency", on_delete=models.PROTECT, default="IRT")
    total_price = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    price_per_sqm = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    deposit_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    rent_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    min_acceptable_price = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True
    )
    is_negotiable = models.BooleanField(default=True)
    price_valid_until = models.DateTimeField(null=True, blank=True)

    # Exclusivity & Analytics
    is_exclusive = models.BooleanField(default=False)
    exclusive_until = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    inquiry_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "properties_property"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "property_code"], name="uq_property_code_per_agency"
            )
        ]
        indexes = [
            models.Index(fields=["agency", "status", "visibility"]),
            models.Index(fields=["status", "deal_type", "total_price"]),
        ]

    def recalculate_price_per_sqm(self) -> None:
        area = self.built_area_sqm if self.built_area_sqm > 0 else self.land_area_sqm
        if area > 0 and self.total_price > 0:
            self.price_per_sqm = (self.total_price / area).quantize(Decimal("0.01"))


class PropertyAmenityValue(BaseModel):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="amenity_values"
    )
    amenity = models.ForeignKey(
        Amenity, on_delete=models.CASCADE, related_name="property_values"
    )
    value_text = models.CharField(max_length=120, blank=True, default="")
    value_number = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "properties_amenity_value"
        unique_together = ("property", "amenity")


class PropertyLocation(models.Model):
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="location")
    country = models.ForeignKey("settings.Country", on_delete=models.PROTECT, default="IR")
    province_ref = models.ForeignKey(
        "settings.Province", null=True, blank=True, on_delete=models.PROTECT, related_name="property_locations"
    )
    city_ref = models.ForeignKey(
        "settings.City", null=True, blank=True, on_delete=models.PROTECT, related_name="property_locations"
    )
    district_ref = models.ForeignKey(
        "settings.District", null=True, blank=True, on_delete=models.PROTECT, related_name="property_locations"
    )
    neighborhood_ref = models.ForeignKey(
        "settings.Neighborhood", null=True, blank=True, on_delete=models.PROTECT, related_name="property_locations"
    )
    province = models.CharField(max_length=80, db_index=True)
    city = models.CharField(max_length=80, db_index=True)
    district = models.CharField(max_length=80, blank=True, default="", db_index=True)
    neighborhood = models.CharField(max_length=80, blank=True, default="")
    street = models.CharField(max_length=120, blank=True, default="")
    full_address = models.CharField(max_length=255, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    hide_exact_address = models.BooleanField(default=True)

    class Meta:
        db_table = "properties_location"
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["province_ref", "city_ref", "district_ref", "neighborhood_ref"]),
        ]


class PropertyOwner(BaseModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="owners")
    owner_customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="owned_properties"
    )
    ownership_share_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("100.00")
    )
    is_primary_contact = models.BooleanField(default=True)

    class Meta:
        db_table = "properties_owner"
        unique_together = ("property", "owner_customer")


class PropertyAgentAssignment(BaseModel):
    class Role(models.TextChoices):
        PRIMARY = "PRIMARY", "Primary Agent"
        CO_AGENT = "CO_AGENT", "Co-Agent"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="agent_assignments"
    )
    membership = models.ForeignKey(
        "accounts.AgencyMembership", on_delete=models.PROTECT, related_name="assigned_properties"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PRIMARY)

    class Meta:
        db_table = "properties_agent_assignment"
        unique_together = ("property", "membership")


class PropertyPriceHistory(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="price_history")
    previous_price = models.DecimalField(max_digits=20, decimal_places=2)
    new_price = models.DecimalField(max_digits=20, decimal_places=2)
    currency_code = models.CharField(max_length=10, default="IRT")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "properties_price_history"


class PropertyStatusHistory(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    reason = models.CharField(max_length=255, blank=True, default="")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "properties_status_history"
