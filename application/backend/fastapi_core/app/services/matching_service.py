from decimal import Decimal
from typing import Any


def score_property_for_requirement(prop: dict[str, Any], req: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic multi-criteria matching engine (0..100) using Decimal arithmetic.
    """
    score = 0
    reasons: list[str] = []

    if prop.get("deal_type_id") == req.get("deal_type_id"):
        score += 15
        reasons.append("تطابق نوع معامله")
    if prop.get("property_type_id") == req.get("property_type_id"):
        score += 10
        reasons.append("تطابق نوع ملک")

    target_city = (req.get("target_city") or "").strip()
    if target_city and prop.get("city") == target_city:
        score += 10
        reasons.append("تطابق شهر")
    districts = req.get("target_districts") or []
    if prop.get("district") and prop.get("district") in districts:
        score += 15
        reasons.append(f"منطقه مطلوب ({prop['district']})")

    min_b = Decimal(str(req.get("min_budget") or 0))
    max_b = Decimal(str(req.get("max_budget") or 0))
    price = Decimal(str(prop.get("total_price") or 0))
    if max_b > 0 and price > 0:
        if min_b <= price <= max_b:
            score += 25
            reasons.append("کاملاً در محدوده بودجه")
        elif price <= max_b * Decimal("1.10"):
            score += 12
            reasons.append("نزدیک به سقف بودجه (حداکثر ۱۰٪ اختلاف)")

    min_a = Decimal(str(req.get("min_area_sqm") or 0))
    max_a = Decimal(str(req.get("max_area_sqm") or 99999))
    area = Decimal(str(prop.get("built_area_sqm") or 0))
    if min_a <= area <= max_a:
        score += 15
        reasons.append("تطابق متراژ")

    if int(prop.get("bedrooms") or 0) >= int(req.get("min_bedrooms") or 0):
        score += 10
        reasons.append("تعداد اتاق مناسب")

    return {
        "property_id": str(prop["id"]),
        "property_code": prop["property_code"],
        "title": prop["title"],
        "city": prop.get("city", ""),
        "district": prop.get("district", ""),
        "total_price": str(prop.get("total_price", "0")),
        "built_area_sqm": str(prop.get("built_area_sqm", "0")),
        "match_score": min(100, score),
        "reasons": reasons,
    }
