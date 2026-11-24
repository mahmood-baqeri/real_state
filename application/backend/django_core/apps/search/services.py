from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from django.db.models import Q
from apps.accounts.models import AgencyMembership, User
from apps.cms.models import Article
from apps.contracts.models import Contract
from apps.customers.models import Customer
from apps.documents.models import Document
from apps.properties.models import Property
from apps.support.models import Ticket
from common.exceptions import NotFoundDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from common.tenant.context import tenant_bypass
from .models import SavedView


def score_property_for_requirement(prop: dict[str, Any], req: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic multi-criteria matching engine (0..100) using Decimal arithmetic.
    Lives inside Django Core per architectural single-source-of-truth rules.
    """
    score = 0
    reasons: list[str] = []
    mismatches: list[str] = []

    if prop.get("deal_type_id") == req.get("deal_type_id"):
        score += 15
        reasons.append("تطابق نوع معامله")
    else:
        mismatches.append("عدم تطابق نوع معامله")

    if prop.get("property_type_id") == req.get("property_type_id"):
        score += 10
        reasons.append("تطابق نوع ملک")
    else:
        mismatches.append("نوع ملک متفاوت است")

    target_city = (req.get("target_city") or "").strip()
    if target_city and prop.get("city") == target_city:
        score += 10
        reasons.append("تطابق شهر")
    elif target_city:
        mismatches.append("شهر متفاوت")

    districts = req.get("target_districts") or []
    if prop.get("district") and prop.get("district") in districts:
        score += 15
        reasons.append(f"منطقه مطلوب ({prop['district']})")
    elif districts:
        mismatches.append("خارج از محله‌های منتخب")

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
        else:
            mismatches.append("بالاتر از بودجه هدف")

    min_a = Decimal(str(req.get("min_area_sqm") or 0))
    max_a = Decimal(str(req.get("max_area_sqm") or 99999))
    area = Decimal(str(prop.get("built_area_sqm") or 0))
    if min_a <= area <= max_a:
        score += 15
        reasons.append("تطابق متراژ")
    else:
        mismatches.append("متراژ خارج از بازه مطلوب")

    if int(prop.get("bedrooms") or 0) >= int(req.get("min_bedrooms") or 0):
        score += 10
        reasons.append("تعداد اتاق مناسب")
    else:
        mismatches.append("تعداد اتاق کمتر از نیاز")

    pref_amenities = {str(c).upper() for c in (req.get("preferred_amenities") or []) if c}
    prop_amenities = {str(c).upper() for c in (prop.get("amenity_codes") or []) if c}
    if pref_amenities:
        matched_am = pref_amenities & prop_amenities
        if matched_am:
            bonus = int(round(10 * (len(matched_am) / len(pref_amenities))))
            score += max(2, bonus)
            reasons.append(f"دارای {len(matched_am)} مورد از امکانات مورد نظر")
        else:
            mismatches.append("امکانات منتخب مشتری در این ملک ثبت نشده است")

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
        "mismatches": mismatches,
    }


def global_search(*, user: User, agency_id: Optional[UUID], query: str, limit: int = 5) -> dict:
    if is_super_admin(user) and not agency_id:
        with tenant_bypass(reason="platform_reports"):
            return _global_search_impl(user=user, agency_id=agency_id, query=query, limit=limit)
    return _global_search_impl(user=user, agency_id=agency_id, query=query, limit=limit)


def _global_search_impl(*, user: User, agency_id: Optional[UUID], query: str, limit: int = 5) -> dict:
    """
    Permission-aware, tenant-isolated Global Search across 8 enterprise modules:
    properties, customers, owners, agents, contracts, tickets, documents, cms_articles.
    """
    q = (query or "").strip()
    if len(q) < 1:
        return {
            "properties": [],
            "customers": [],
            "owners": [],
            "agents": [],
            "contracts": [],
            "tickets": [],
            "documents": [],
            "articles": [],
            "total_hits": 0,
        }

    cap = max(1, min(limit, 15))
    super_admin = is_super_admin(user)
    membership = get_active_membership(user, agency_id) if agency_id else None

    # 1. Properties: materialize public results while the public-catalog bypass is active.
    def _property_results(prop_qs):
        return [
            {
                "id": str(p.id),
                "title": p.title,
                "subtitle": f"{p.property_code} — {p.location.city if getattr(p, 'location', None) else ''}",
                "href": f"/dashboard/properties" if (agency_id or super_admin) else f"/properties/{p.id}",
            }
            for p in prop_qs.select_related("location").filter(
                Q(title__icontains=q) | Q(property_code__icontains=q) | Q(location__district__icontains=q)
            )[:cap]
        ]

    if super_admin and not agency_id:
        prop_qs = Property.objects.all_tenants().filter(is_deleted=False)
        properties = _property_results(prop_qs)
    elif agency_id and (membership or super_admin):
        prop_qs = Property.objects.all_tenants().filter(agency_id=agency_id, is_deleted=False)
        if not super_admin and not has_agency_permission(user, agency_id, "property.view_all_agency"):
            prop_qs = prop_qs.filter(
                Q(agent_assignments__membership=membership)
                | Q(created_by=user)
                | Q(visibility=Property.Visibility.PUBLIC_PORTAL)
            ).distinct()
        properties = _property_results(prop_qs)
    else:
        with tenant_bypass(reason="public_catalog"):
            prop_qs = Property.objects.all_tenants().filter(
                is_deleted=False, status=Property.Status.PUBLISHED,
                visibility=Property.Visibility.PUBLIC_PORTAL,
            )
            properties = _property_results(prop_qs)

    # 2. Customers & Owners (Agency Staff / Super Admin only)
    customers_list: list[dict] = []
    owners_list: list[dict] = []
    agents_list: list[dict] = []
    contracts_list: list[dict] = []
    documents_list: list[dict] = []

    if (agency_id and membership) or super_admin:
        cust_base = Customer.objects.all_tenants().filter(is_deleted=False)
        if agency_id:
            cust_base = cust_base.filter(agency_id=agency_id)
        if not super_admin and agency_id and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
            from django.utils import timezone
            cust_base = cust_base.filter(
                Q(assigned_membership=membership)
                | Q(shares__membership=membership, shares__expires_at__isnull=True)
                | Q(shares__membership=membership, shares__expires_at__gt=timezone.now())
            ).distinct()

        for c in cust_base.filter(Q(full_name__icontains=q) | Q(primary_phone__icontains=q))[:cap]:
            entry = {
                "id": str(c.id),
                "title": c.full_name,
                "subtitle": f"{c.customer_type} — {c.primary_phone}",
                "href": "/dashboard/customers",
            }
            if c.customer_type == Customer.CustomerType.OWNER:
                owners_list.append(entry)
            else:
                customers_list.append(entry)

        # Agents / Memberships
        mem_qs = AgencyMembership.objects.select_related("user", "role").filter(status="ACTIVE")
        if agency_id:
            mem_qs = mem_qs.filter(agency_id=agency_id)
            if membership and membership.role.code == "BRANCH_MANAGER":
                mem_qs = mem_qs.filter(branch_id=membership.branch_id)
        agents_list = [
            {
                "id": str(m.id),
                "title": m.user.full_name,
                "subtitle": f"{m.role.name} — {m.user.phone_number}",
                "href": "/dashboard/agents",
            }
            for m in mem_qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__phone_number__icontains=q)
            )[:cap]
        ]

        # Contracts
        con_qs = Contract.objects.all_tenants().select_related("property")
        if agency_id:
            con_qs = con_qs.filter(agency_id=agency_id)
        if not super_admin and agency_id and not has_agency_permission(user, agency_id, "deal.view_all_agency"):
            con_qs = con_qs.filter(
                Q(created_by=user) | Q(property__agent_assignments__membership=membership)
            ).distinct()
        contracts_list = [
            {
                "id": str(c.id),
                "title": c.contract_number,
                "subtitle": c.property.title if c.property else c.contract_type,
                "href": "/dashboard/contracts",
            }
            for c in con_qs.filter(Q(contract_number__icontains=q) | Q(property__title__icontains=q))[:cap]
        ]

        # Documents use the same granular ACL and branch/agent scope as the document module.
        from apps.documents.services import list_documents
        visible_docs = list_documents(user=user, agency_id=agency_id)
        documents_list = [
            {"id": str(d.id), "title": d.title, "subtitle": d.category, "href": "/dashboard/documents"}
            for d in visible_docs if q.casefold() in (d.title or "").casefold() or q.casefold() in (d.category or "").casefold()
        ][:cap]

    # 3. Tickets (User's tickets or Agency/Platform tickets)
    t_qs = Ticket.objects.all()
    if super_admin and not agency_id:
        pass
    elif agency_id and membership and has_agency_permission(user, agency_id, "support.manage"):
        t_qs = t_qs.filter(agency_id=agency_id)
    else:
        t_qs = t_qs.filter(created_by_user=user)

    tickets_list = [
        {
            "id": str(t.id),
            "title": t.subject,
            "subtitle": f"{t.ticket_number} — {t.status}",
            "href": "/dashboard/tickets",
        }
        for t in t_qs.filter(Q(subject__icontains=q) | Q(ticket_number__icontains=q))[:cap]
    ]

    # 4. Public / Published CMS Articles
    articles_list = [
        {
            "id": str(a.id),
            "title": a.title,
            "subtitle": a.article_type,
            "href": f"/blog/{a.slug}",
        }
        for a in Article.objects.filter(status=Article.Status.PUBLISHED).filter(
            Q(title__icontains=q) | Q(summary__icontains=q)
        )[:cap]
    ]

    total_hits = (
        len(properties)
        + len(customers_list)
        + len(owners_list)
        + len(agents_list)
        + len(contracts_list)
        + len(tickets_list)
        + len(documents_list)
        + len(articles_list)
    )

    return {
        "properties": properties,
        "customers": customers_list,
        "owners": owners_list,
        "agents": agents_list,
        "contracts": contracts_list,
        "tickets": tickets_list,
        "documents": documents_list,
        "articles": articles_list,
        "total_hits": total_hits,
    }


def list_saved_views(*, user: User, agency_id: Optional[UUID], module: Optional[str] = None):
    qs = SavedView.objects.filter(user=user)
    if agency_id:
        qs = qs.filter(Q(agency_id=agency_id) | Q(agency__isnull=True))
    if module:
        qs = qs.filter(module=module)
    return list(qs)


def create_saved_view(
    *,
    user: User,
    agency_id: Optional[UUID],
    module: str,
    title: str,
    filters_json: dict,
    sort_by: str = "",
    columns_json: Optional[list] = None,
    layout_mode: str = "table",
    is_default: bool = False,
) -> SavedView:
    if is_default:
        SavedView.objects.filter(user=user, module=module).update(is_default=False)
    return SavedView.objects.create(
        user=user,
        agency_id=agency_id,
        module=module.strip(),
        title=title.strip(),
        filters_json=filters_json or {},
        sort_by=sort_by,
        columns_json=columns_json or [],
        layout_mode=layout_mode,
        is_default=is_default,
        created_by=user,
    )


def delete_saved_view(*, user: User, view_id: UUID) -> None:
    deleted, _ = SavedView.objects.filter(id=view_id, user=user).delete()
    if not deleted:
        raise NotFoundDomainError("نمای ذخیره‌شده یافت نشد.")
