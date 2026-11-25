"""مسیرهای تطبیق مشتری و ملک، کیفیت آگهی و تحلیل بازار."""

from collections import defaultdict
from decimal import Decimal
from itertools import islice
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.django_bridge import run_django
from app.dependencies.auth import RequestContext, get_optional_context
from app.schemas.common import ok

router = APIRouter(prefix="/matching", tags=["Smart Matching & Market Analytics"])


@router.get("/customer-to-properties")
async def match_properties_for_customer(
    customer_id: Optional[UUID] = None,
    deal_type_id: str = "SALE",
    property_type_id: str = "APARTMENT",
    target_city: str = "تهران",
    districts: str = "زعفرانیه,فرشته",
    min_area_sqm: Decimal = Query(default=Decimal("120"), ge=0),
    max_area_sqm: Decimal = Query(default=Decimal("250"), ge=0),
    min_budget: Decimal = Query(default=Decimal("15000000000"), ge=0),
    max_budget: Decimal = Query(default=Decimal("45000000000"), ge=0),
    min_bedrooms: int = Query(default=2, ge=0, le=20),
    amenities: str = "",
    ctx: RequestContext = Depends(get_optional_context),
):
    def _op():
        from apps.properties.models import DealType, Property, PropertyType
        from apps.search.services import score_property_for_requirement

        req = {
            "deal_type_id": None,
            "property_type_id": None,
            "target_city": target_city,
            "target_districts": [d.strip() for d in districts.split(",") if d.strip()],
            "min_area_sqm": Decimal(str(min_area_sqm)),
            "max_area_sqm": Decimal(str(max_area_sqm)),
            "min_budget": Decimal(str(min_budget)),
            "max_budget": Decimal(str(max_budget)),
            "min_bedrooms": min_bedrooms,
            "preferred_amenities": [a.strip().upper() for a in amenities.split(",") if a.strip()],
            "currency_id": "IRT",
        }

        if customer_id:
            if not ctx.user or not ctx.agency_id:
                from common.exceptions import PermissionDeniedDomainError
                raise PermissionDeniedDomainError("برای تطبیق بر اساس پرونده مشتری باید وارد آژانس شوید.")
            from apps.customers.models import CustomerRequirement
            from apps.customers.services import list_customers
            customer = list_customers(user=ctx.user, agency_id=ctx.agency_id).filter(
                id=customer_id, is_deleted=False
            ).first()
            if not customer:
                from common.exceptions import NotFoundDomainError
                raise NotFoundDomainError("مشتری یافت نشد یا در محدوده دسترسی شما نیست.")
            requirement = CustomerRequirement.objects.all_tenants().filter(
                customer=customer, agency_id=ctx.agency_id, is_active=True
            ).order_by("-created_at").first()
            if not requirement:
                from common.exceptions import NotFoundDomainError
                raise NotFoundDomainError("برای این مشتری نیاز فعال جستجوی ملک ثبت نشده است.")
            req = {
                "deal_type_id": requirement.deal_type_id,
                "property_type_id": requirement.property_type_id,
                "target_city": requirement.target_city,
                "target_districts": requirement.target_districts or [],
                "min_area_sqm": requirement.min_area_sqm,
                "max_area_sqm": requirement.max_area_sqm,
                "min_budget": requirement.min_budget,
                "max_budget": requirement.max_budget,
                "min_bedrooms": requirement.min_bedrooms,
                "preferred_amenities": requirement.required_amenities or [],
                "currency_id": requirement.currency_id,
                "is_rental": bool(requirement.deal_type.is_rental),
            }
        else:
            deal_type = DealType.objects.filter(code=deal_type_id, is_active=True).first()
            property_type = PropertyType.objects.filter(code=property_type_id, is_active=True).first()
            req["deal_type_id"] = deal_type.pk if deal_type else None
            req["property_type_id"] = property_type.pk if property_type else None
            req["is_rental"] = bool(deal_type.is_rental) if deal_type else False

        if req["min_budget"] and req["max_budget"] and Decimal(str(req["min_budget"])) > Decimal(str(req["max_budget"])):
            from common.exceptions import ValidationDomainError
            raise ValidationDomainError("حداقل بودجه نمی‌تواند از حداکثر بودجه بیشتر باشد.")
        if req["min_area_sqm"] is not None and req["max_area_sqm"] is not None and Decimal(str(req["min_area_sqm"])) > Decimal(str(req["max_area_sqm"])):
            from common.exceptions import ValidationDomainError
            raise ValidationDomainError("حداقل متراژ نمی‌تواند از حداکثر متراژ بیشتر باشد.")

        from django.utils import timezone
        from datetime import timedelta
        from apps.settings.models import ExchangeRate
        from apps.search.phase4 import convert_currency_amount
        rate_rows = list(ExchangeRate.objects.filter(is_active=True, effective_at__gte=timezone.now()-timedelta(days=30)).values_list("base_currency_id", "quote_currency_id", "rate"))

        def _score_queryset(qs, relax=False):
            if req["deal_type_id"]:
                qs = qs.filter(deal_type_id=req["deal_type_id"])
            if req["property_type_id"]:
                qs = qs.filter(property_type_id=req["property_type_id"])
            if req["target_city"] and not relax:
                qs = qs.filter(location__city=req["target_city"])
            if not relax and req["min_area_sqm"] is not None:
                qs = qs.filter(built_area_sqm__gte=req["min_area_sqm"])
            if not relax and req["max_area_sqm"] is not None:
                qs = qs.filter(built_area_sqm__lte=req["max_area_sqm"])
            if req["min_bedrooms"]:
                qs = qs.filter(bedrooms__gte=req["min_bedrooms"])
            min_budget = Decimal(str(req["min_budget"] or 0))
            max_budget = Decimal(str(req["max_budget"] or 0))
            price_field = "rent_amount" if req.get("is_rental") else "total_price"
            qs = qs.select_related("location", "property_type", "deal_type").prefetch_related("amenities")[:500]
            props = []
            from apps.properties.models import PropertyLocation
            property_rows = list(qs)
            location_map = {str(loc.property_id): loc for loc in PropertyLocation.objects.filter(property_id__in=[p.pk for p in property_rows])}
            for prop in property_rows:
                loc = location_map.get(str(prop.pk))
                source_amount = getattr(prop, price_field, None)
                normalized_price = convert_currency_amount(source_amount, prop.currency_id, req.get("currency_id"), rate_rows)
                if not relax and normalized_price is not None and max_budget > 0:
                    if normalized_price > max_budget * Decimal("1.10"):
                        continue
                    if min_budget > 0 and normalized_price < min_budget * Decimal("0.90"):
                        continue
                props.append({
                    "id": str(prop.id),
                    "property_code": prop.property_code,
                    "title": prop.title,
                    "property_type_id": prop.property_type_id,
                    "deal_type_id": prop.deal_type_id,
                    "built_area_sqm": prop.built_area_sqm,
                    "bedrooms": prop.bedrooms,
                    "total_price": prop.total_price,
                    "rent_amount": prop.rent_amount,
                    "currency_id": prop.currency_id,
                    "normalized_price": normalized_price,
                    "normalized_currency": req.get("currency_id") if normalized_price is not None else None,
                    "city": loc.city if loc else "",
                    "district": loc.district if loc else "",
                    "amenity_codes": [a.code for a in prop.amenities.all()],
                })
            return props

        if ctx.user and ctx.agency_id:
            from apps.properties.services import list_agency_properties
            qs = list_agency_properties(user=ctx.user, agency_id=ctx.agency_id).filter(
                status=Property.Status.PUBLISHED
            )
            props = _score_queryset(qs)
        else:
            from common.tenant.context import tenant_bypass
            with tenant_bypass(reason="public_catalog"):
                qs = Property.objects.all_tenants().filter(
                    is_deleted=False,
                    status=Property.Status.PUBLISHED,
                    visibility=Property.Visibility.PUBLIC_PORTAL,
                )
                props = _score_queryset(qs)
        scored = [score_property_for_requirement(prop, req) for prop in props]
        fallback_used = not scored
        if fallback_used:
            # Relax city, area, and budget only for ranked alternatives; agency/visibility scope remains intact.
            props = _score_queryset(qs, relax=True)
            scored = [score_property_for_requirement(prop, req) for prop in props]
            for item in scored:
                item["is_alternative"] = True
                item["alternative_reason"] = "تطابق کامل پیدا نشد؛ این گزینه‌ها با معیارهای نرم رتبه‌بندی شده‌اند."
        scored.sort(key=lambda item: item["match_score"], reverse=True)
        for item in scored:
            item["is_alternative"] = fallback_used or bool(item.get("mismatches"))
            item["alternative_reason"] = ("تطابق کامل پیدا نشد؛ این گزینه‌ها با معیارهای نرم رتبه‌بندی شده‌اند." if fallback_used else "؛ ".join(item.get("mismatches", [])[:2]))
        return scored[:10]

    return ok(await run_django(
        _op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None
    ))


@router.get("/analytics/price-trends")
async def district_price_trends(
    city: str = Query(default="تهران"),
    currency_code: str = Query(default="IRT", min_length=3, max_length=10),
):
    def _op():
        from django.db.models import Avg, Count
        from apps.properties.models import Property

        from common.tenant.context import tenant_bypass
        with tenant_bypass(reason="public_catalog"):
            rows = list(
                Property.objects.all_tenants()
            .filter(
                is_deleted=False,
                status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
                currency_id=currency_code,
                price_per_sqm__gt=Decimal("0"),
                location__city=city,
            )
            .values("location__district", "currency_id")
            .annotate(
                listing_count=Count("id"),
                avg_price_per_sqm=Avg("price_per_sqm"),
            )
                .filter(listing_count__gte=5)
                .order_by("-avg_price_per_sqm")
            )
        return [
            {
                "district": row["location__district"] or "سایر",
                "listing_count": row["listing_count"],
                "currency": row["currency_id"],
                "avg_price_per_sqm": str(int(row["avg_price_per_sqm"] or 0)),
            }
            for row in rows
        ]

    return ok(await run_django(_op))


@router.get("/property-quality")
async def property_quality_dashboard(ctx: RequestContext = Depends(get_optional_context)):
    """کیفیت و فایل‌های مشابه را در محدودهٔ املاک مجاز آژانس گزارش می‌کند."""
    def _op():
        """داده‌های مرتبط را یک‌جا می‌خواند و حداکثر سه مشابه را برای هر ملک نگه می‌دارد."""
        if not ctx.user or not ctx.agency_id:
            from common.exceptions import PermissionDeniedDomainError
            raise PermissionDeniedDomainError("برای گزارش کیفیت فایل‌ها باید در آژانس وارد شوید.")
        from apps.properties.models import Property
        from apps.properties.services import list_agency_properties
        qs = list_agency_properties(user=ctx.user, agency_id=ctx.agency_id).filter(
            status__in=[Property.Status.DRAFT, Property.Status.PENDING_APPROVAL, Property.Status.APPROVED, Property.Status.PUBLISHED]
        ).select_related("location", "verification").prefetch_related("media_items", "amenities")[:300]
        properties = list(qs)
        locations = {p.pk: getattr(p, "location", None) for p in properties}
        by_postal_code = defaultdict(list)
        for p in properties:
            loc = locations[p.pk]
            if loc and loc.postal_code:
                by_postal_code[loc.postal_code].append(p)
        from apps.search.phase4 import property_quality_score
        rows = []
        for p in properties:
            ver = getattr(p, "verification", None)
            quality = property_quality_score(p)
            checks = quality["checks"]
            loc = locations[p.pk]
            duplicates = []
            if loc and loc.postal_code:
                duplicates = list(islice((other for other in by_postal_code[loc.postal_code] if other.pk != p.pk), 3))
            if not duplicates and loc and loc.latitude is not None and loc.longitude is not None:
                for other in properties:
                    ol = locations[other.pk]
                    if other.pk == p.pk or not ol or ol.latitude is None or ol.longitude is None:
                        continue
                    close = abs(float(ol.latitude)-float(loc.latitude)) <= 0.00025 and abs(float(ol.longitude)-float(loc.longitude)) <= 0.00025
                    similar_area = p.built_area_sqm > 0 and abs(float(other.built_area_sqm)-float(p.built_area_sqm)) <= max(5, float(p.built_area_sqm)*0.05)
                    if close and similar_area:
                        duplicates.append(other)
                        if len(duplicates) == 3:
                            break
            checks.append({"label": "عدم تکرار احتمالی", "passed": not duplicates, "weight": 10})
            total_weight = sum(int(c.get("weight", 0)) for c in checks)
            passed_weight = sum(int(c.get("weight", 0)) for c in checks if c.get("passed"))
            score = round(passed_weight * 100 / total_weight) if total_weight else 0
            level = "HIGH" if score >= 80 else "MEDIUM" if score >= 55 else "LOW"
            missing = [c["label"] for c in checks if not c["passed"]]
            rows.append({"property_id": str(p.pk), "property_code": p.property_code, "title": p.title,
                "status": p.status, "quality_score": score, "quality_level": level,
                "missing_checks": missing, "quality_checks": checks,
                "verification_status": getattr(ver, "verification_status", "UNVERIFIED"),
                "possible_duplicate_ids": [str(d.pk) for d in duplicates],
                "price_valid_until": p.price_valid_until.isoformat() if p.price_valid_until else None,
            })
        rows.sort(key=lambda x: (x["quality_score"], x["property_code"]))
        return {"total": len(rows), "average_score": round(sum(r["quality_score"] for r in rows) / len(rows)) if rows else 0,
            "low_quality": sum(r["quality_score"] < 60 for r in rows), "items": rows}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))



@router.get("/price-alerts")
async def property_price_alerts(days: int = Query(default=30, ge=1, le=365), ctx: RequestContext = Depends(get_optional_context)):
    """Return agency-scoped price changes and stale/expiring listing price validity."""
    def _op():
        if not ctx.user or not ctx.agency_id:
            from common.exceptions import PermissionDeniedDomainError
            raise PermissionDeniedDomainError("برای هشدار قیمت باید در آژانس وارد شوید.")
        from django.utils import timezone
        from datetime import timedelta
        from apps.properties.models import PropertyPriceHistory
        from apps.properties.services import list_agency_properties
        now = timezone.now()
        qs = list_agency_properties(user=ctx.user, agency_id=ctx.agency_id).filter(is_deleted=False).select_related("location")
        scoped_ids = qs.values("pk")
        valid_until = qs.filter(price_valid_until__isnull=False, price_valid_until__lte=now + timedelta(days=days)).order_by("price_valid_until")[:200]
        recent_changes = PropertyPriceHistory.objects.filter(property_id__in=scoped_ids, changed_at__gte=now-timedelta(days=days)).select_related("property").order_by("-changed_at")[:200]
        expired_ids = set(str(p.pk) for p in valid_until if p.price_valid_until and p.price_valid_until < now)
        return {"window_days": days, "expiring_or_expired": [{"property_id": str(p.pk), "property_code": p.property_code, "title": p.title, "price_valid_until": p.price_valid_until.isoformat(), "expired": p.price_valid_until < now} for p in valid_until],
            "recent_changes": [{"property_id": str(h.property_id), "property_code": h.property.property_code, "title": h.property.title, "previous_price": str(h.previous_price), "new_price": str(h.new_price), "price_type": "RENT" if h.currency_code == "RENT" else "SALE", "currency": h.property.currency_id if h.currency_code == "RENT" else h.currency_code, "changed_at": h.changed_at.isoformat()} for h in recent_changes],
            "expired_count": len(expired_ids)}
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id if ctx.user else None))



@router.get("/search")
async def intelligent_property_search(q: str = Query(min_length=1, max_length=120), limit: int = Query(default=20, ge=1, le=50), ctx: RequestContext = Depends(get_optional_context)):
    """Normalized Persian text search using agency scope or public portal scope."""
    def _op():
        from apps.properties.models import Property
        from apps.properties.services import list_agency_properties
        from apps.search.phase4 import normalize_persian_search, search_variants
        norm = normalize_persian_search
        query = norm(q)
        terms = search_variants(q)
        if ctx.user and ctx.agency_id:
            qs = list_agency_properties(user=ctx.user, agency_id=ctx.agency_id).filter(status=Property.Status.PUBLISHED)
        else:
            qs = Property.objects.all_tenants().filter(is_deleted=False, status=Property.Status.PUBLISHED, visibility=Property.Visibility.PUBLIC_PORTAL)
        from apps.properties.models import PropertyLocation
        properties = list(qs[:500])
        locations = {str(loc.property_id): loc for loc in PropertyLocation.objects.filter(property_id__in=[p.pk for p in properties])}
        matches = []
        for p in properties:
            loc = locations.get(str(p.pk))
            hay = norm(" ".join([p.title, p.property_code, getattr(loc, "city", ""), getattr(loc, "district", ""), getattr(p, "usage_type", "")]))
            if any(t and t in hay for t in terms):
                matches.append({"id": str(p.pk), "property_code": p.property_code, "title": p.title, "city": getattr(loc, "city", ""), "district": getattr(loc, "district", ""), "status": p.status})
                if len(matches) >= limit: break
        return {"query": q, "normalized_query": query, "results": matches, "count": len(matches)}
    if not (ctx.user and ctx.agency_id):
        from common.tenant.context import tenant_bypass
        async def public_op():
            def wrapped():
                with tenant_bypass(reason="public_catalog"):
                    return _op()
            return await run_django(wrapped)
        return ok(await public_op())
    return ok(await run_django(_op, agency_id=ctx.agency_id, user_id=ctx.user.id))


@router.get("/market-opportunities")
async def market_opportunity_radar(city: str = Query(default="تهران", min_length=1, max_length=80), currency_code: str = Query(default="IRT", min_length=3, max_length=10)):
    """Public-listing-only radar: finds listings >=15% below comparable area price with >=5 samples."""
    def _op():
        from django.db.models import Avg, Count
        from common.tenant.context import tenant_bypass
        from apps.properties.models import Property, PropertyLocation
        with tenant_bypass(reason="public_catalog"):
            base = Property.objects.all_tenants().filter(
                is_deleted=False, status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
                currency_id=currency_code, price_per_sqm__gt=0,
                location__city=city,
            )
            peers = base.values("location__district", "property_type_id", "deal_type_id").annotate(
                sample_count=Count("id"), average_price_per_sqm=Avg("price_per_sqm")
            )
            benchmarks = {(r["location__district"], r["property_type_id"], r["deal_type_id"]): r for r in peers if r["sample_count"] >= 5 and r["average_price_per_sqm"]}
            candidate_props = list(base.select_related("property_type", "deal_type")[:1000])
            locs = {str(l.property_id): l for l in PropertyLocation.objects.filter(property_id__in=[p.pk for p in candidate_props])}
            opportunities = []
            for prop in candidate_props:
                loc = locs.get(str(prop.pk))
                if not loc:
                    continue
                benchmark = benchmarks.get((loc.district, prop.property_type_id, prop.deal_type_id))
                if not benchmark:
                    continue
                average = Decimal(str(benchmark["average_price_per_sqm"]))
                price = Decimal(str(prop.price_per_sqm or 0))
                discount = (average-price) * Decimal("100") / average if average > 0 else Decimal("0")
                if discount >= Decimal("15"):
                    opportunities.append({"property_id": str(prop.pk), "property_code": prop.property_code,
                        "title": prop.title, "district": loc.district or "—", "deal_type": prop.deal_type.name_fa,
                        "property_type": prop.property_type.name_fa, "currency": prop.currency_id,
                        "price_per_sqm": str(price), "district_average": str(average),
                        "discount_percent": round(float(discount), 1), "sample_count": int(benchmark["sample_count"])})
            opportunities.sort(key=lambda x: x["discount_percent"], reverse=True)
            return {"city": city, "currency": currency_code, "minimum_sample_count": 5,
                "threshold_percent": 15, "count": len(opportunities), "items": opportunities[:30]}
    return ok(await run_django(_op))
