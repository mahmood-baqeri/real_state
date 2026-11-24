"""Phase 4 utilities: Persian search normalization, property quality, saved price alerts."""
from decimal import Decimal, InvalidOperation
import re
from django.utils import timezone

_TRANSLATION = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "أ": "ا", "إ": "ا", "ؤ": "و"})
_SYNONYMS = {
    "آپارتمان": ("اپارتمان", "واحد", "خانه"),
    "اپارتمان": ("آپارتمان", "واحد", "خانه"),
    "خانه": ("آپارتمان", "اپارتمان", "مسکونی"),
    "ویلا": ("باغ ویلا", "ویلایی"),
    "ویلایی": ("ویلا", "باغ ویلا"),
    "اجاره": ("رهن", "رهن و اجاره"),
    "رهن": ("اجاره", "رهن و اجاره"),
    "فروش": ("خرید", "فروشی"),
    "خرید": ("فروش", "فروشی"),
}


def convert_currency_amount(amount, source_code: str, target_code: str, rates) -> Decimal | None:
    """Convert using active database rate tuples; supports direct, inverse, and chained paths."""
    value = Decimal(str(amount or 0))
    source = (source_code or "").upper().strip()
    target = (target_code or "").upper().strip()
    if value <= 0 or not source or not target:
        return None
    if source == target:
        return value
    graph: dict[str, list[tuple[str, Decimal]]] = {}
    for base, quote, raw_rate in rates:
        base, quote, rate = str(base).upper(), str(quote).upper(), Decimal(str(raw_rate))
        if rate <= 0:
            continue
        graph.setdefault(base, []).append((quote, rate))
        graph.setdefault(quote, []).append((base, Decimal("1") / rate))
    queue = [(source, Decimal("1"))]
    visited = {source}
    while queue:
        code, multiplier = queue.pop(0)
        for neighbor, rate in graph.get(code, []):
            if neighbor in visited:
                continue
            converted_multiplier = multiplier * rate
            if neighbor == target:
                return value * converted_multiplier
            visited.add(neighbor)
            queue.append((neighbor, converted_multiplier))
    return None


def normalize_persian_search(value: str) -> str:
    value = (value or "").translate(_TRANSLATION).replace("\u200c", " ").replace("\u200f", " ")
    value = re.sub(r"[\u0640\u064b-\u065f\u0670\u06d6-\u06ed]", "", value)
    value = re.sub(r"[،؛,.!؟:()\[\]{}]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value



def search_variants(value: str) -> list[str]:
    normalized = normalize_persian_search(value)
    if not normalized:
        return []
    variants = {normalized}
    for token in normalized.split():
        for synonym in _SYNONYMS.get(token, ()):
            variants.add(normalized.replace(token, synonym))
    return sorted(variants)[:8]



def property_quality_score(prop) -> dict:
    """Explainable completeness/quality score (not a property valuation)."""
    points = 0
    checks = []
    def add(label, condition, weight):
        nonlocal points
        checks.append({"label": label, "passed": bool(condition), "weight": weight})
        if condition:
            points += weight
    add("عنوان معتبر", bool((prop.title or "").strip()), 8)
    add("شرح ملک", len((prop.description or "").strip()) >= 40, 8)
    try:
        loc = prop.location
    except Exception:
        loc = None
    add("موقعیت شهری", bool(getattr(loc, "city", "")), 12)
    add("موقعیت منطقه", bool(loc and (loc.district or loc.neighborhood)), 8)
    add("متراژ", Decimal(str(prop.built_area_sqm or 0)) > 0 or Decimal(str(prop.land_area_sqm or 0)) > 0, 12)
    add("قیمت", Decimal(str(prop.total_price or 0)) > 0 or Decimal(str(prop.rent_amount or 0)) > 0, 12)
    add("اتاق", int(prop.bedrooms or 0) > 0, 5)
    add("امکانات", prop.amenities.exists(), 8)
    media = list(prop.media_items.all())
    add("تصویر کاور", any(getattr(m, "is_cover", False) and getattr(m, "is_public", False) for m in media), 10)
    add("تصاویر عمومی", sum(1 for m in media if getattr(m, "is_public", False)) >= 3, 7)
    try:
        verification = prop.verification
    except Exception:
        verification = None
    add("تأیید ملک", bool(verification and verification.verification_status in ("VERIFIED", "EXCEPTION_APPROVED")), 10)
    add("اعتبار قیمت", not prop.price_valid_until or prop.price_valid_until > timezone.now(), 10)
    normalized_score = round(points / 110 * 100)
    return {"score": normalized_score, "max_score": 100, "level": "HIGH" if normalized_score >= 80 else "MEDIUM" if normalized_score >= 55 else "LOW", "checks": checks}



def saved_search_matches_property(filters: dict, prop) -> bool:
    """Small allowlisted matcher for user-owned saved search alert filters."""
    filters = filters or {}
    loc = getattr(prop, "location", None)
    def text_filter(key, actual):
        expected = normalize_persian_search(str(filters.get(key) or ""))
        return not expected or expected in normalize_persian_search(str(actual or ""))
    if not text_filter("city", getattr(loc, "city", "")):
        return False
    if not text_filter("district", getattr(loc, "district", "")):
        return False
    if not text_filter("q", prop.title) and not text_filter("q", getattr(loc, "neighborhood", "")):
        return False
    if filters.get("deal_type") and str(prop.deal_type_id) != str(filters["deal_type"]):
        return False
    if filters.get("property_type") and str(prop.property_type_id) != str(filters["property_type"]):
        return False
    if filters.get("currency_id") and str(prop.currency_id) != str(filters["currency_id"]):
        return False
    try:
        is_rental = bool(prop.deal_type.is_rental)
    except Exception:
        is_rental = False
    price_value = prop.rent_amount if is_rental else prop.total_price
    checks = (("min_price", "gte", Decimal(str(price_value or 0))), ("max_price", "lte", Decimal(str(price_value or 0))),
              ("min_area", "gte", Decimal(str(prop.built_area_sqm or 0))), ("max_area", "lte", Decimal(str(prop.built_area_sqm or 0))),
              ("min_bedrooms", "gte", Decimal(str(prop.bedrooms or 0))))
    for key, op, value in checks:
        raw = filters.get(key)
        if raw in (None, ""):
            continue
        try:
            limit = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return False
        if op == "gte" and value < limit:
            return False
        if op == "lte" and value > limit:
            return False
    return True



def notify_saved_search_price_change(prop, *, actor=None) -> int:
    """Notify agency members with saved matching alerts after public property price changes."""
    from django.utils import timezone
    from apps.search.models import SavedSearch
    from apps.notifications.services import send_notification
    from apps.accounts.models import AgencyMembership
    if prop.status != "PUBLISHED" or prop.visibility != "PUBLIC_PORTAL" or prop.is_deleted:
        return 0
    now = timezone.now()
    if prop.price_valid_until and prop.price_valid_until <= now:
        return 0
    qs = SavedSearch.objects.filter(notify_on_match=True).select_related("user")
    sent = 0
    for saved in qs.iterator():
        filters = saved.filters_json or {}
        if str(filters.get("agency_id") or "") != str(prop.agency_id):
            continue
        # Do not let an arbitrary saved-search filter subscribe a non-member
        # to notifications from another agency.
        if not AgencyMembership.objects.filter(
            user_id=saved.user_id, agency_id=prop.agency_id, status="ACTIVE"
        ).exists():
            continue
        if not saved_search_matches_property(filters, prop):
            continue
        try:
            is_rental = bool(prop.deal_type.is_rental)
            displayed_price = prop.rent_amount if is_rental else prop.total_price
            price_label = "اجاره" if is_rental else "قیمت"
            send_notification(
                recipient_user_id=saved.user_id,
                agency_id=prop.agency_id,
                actor=actor,
                title="تغییر قیمت ملک موردنظر",
                body=f"{price_label} ملک {prop.property_code} ({prop.title}) تغییر کرده است. مبلغ جدید: {displayed_price} {prop.currency_id}.",
            )
            sent += 1
        except Exception:
            # Notification failure must not roll back the property price update.
            continue
    return sent
