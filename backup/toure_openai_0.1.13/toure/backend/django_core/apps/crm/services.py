from datetime import datetime
from typing import Optional
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from common.exceptions import NotFoundDomainError, PermissionDeniedDomainError
from common.permissions import get_active_membership, has_agency_permission, is_super_admin
from .models import CustomerInteractionLog, CustomerPipelineItem, FollowUpTask, PipelineStage


def list_pipeline_stages(agency_id: UUID) -> list[PipelineStage]:
    return list(PipelineStage.objects.all_tenants().filter(agency_id=agency_id, is_active=True).order_by("sort_order"))


def list_pipeline_items(*, user: User, agency_id: UUID):
    qs = (
        CustomerPipelineItem.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("customer", "stage", "property", "assigned_membership__user")
    )
    if not is_super_admin(user) and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return CustomerPipelineItem.objects.none()
        qs = qs.filter(assigned_membership=membership)
    return qs.order_by("stage__sort_order", "-updated_at")


@transaction.atomic
def upsert_pipeline_item(
    *,
    user: User,
    agency_id: UUID,
    customer_id: UUID,
    stage_id: UUID,
    property_id: Optional[UUID] = None,
    notes: str = "",
) -> CustomerPipelineItem:
    membership = get_active_membership(user, agency_id)
    stage = PipelineStage.objects.all_tenants().filter(id=stage_id, agency_id=agency_id).first()
    if not stage:
        raise NotFoundDomainError("مرحله پیگیری یافت نشد.")

    item, _ = CustomerPipelineItem.objects.all_tenants().update_or_create(
        agency_id=agency_id,
        customer_id=customer_id,
        defaults={
            "stage": stage,
            "property_id": property_id,
            "notes": notes,
            "assigned_membership": membership,
            "updated_by": user,
        },
    )
    return item


@transaction.atomic
def move_pipeline_item_stage(*, user: User, agency_id: UUID, item_id: UUID, stage_id: UUID, notes: Optional[str] = None) -> CustomerPipelineItem:
    item = list_pipeline_items(user=user, agency_id=agency_id).filter(id=item_id).first()
    if not item:
        raise NotFoundDomainError("آیتم قیف فروش یافت نشد.")
    stage = PipelineStage.objects.all_tenants().filter(id=stage_id, agency_id=agency_id).first()
    if not stage:
        raise NotFoundDomainError("مرحله جدید یافت نشد.")
    item.stage = stage
    if notes is not None:
        item.notes = notes
    item.updated_by = user
    item.save()
    return item


def list_follow_up_tasks(*, user: User, agency_id: UUID):
    qs = (
        FollowUpTask.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("customer", "assigned_membership__user")
    )
    if not is_super_admin(user) and not has_agency_permission(user, agency_id, "customer.view_all_agency"):
        membership = get_active_membership(user, agency_id)
        if not membership:
            return FollowUpTask.objects.none()
        qs = qs.filter(assigned_membership=membership)
    return qs.order_by("status", "due_at")


@transaction.atomic
def create_follow_up_task(
    *, user: User, agency_id: UUID, customer_id: UUID, title: str, due_at: datetime, assigned_membership_id: Optional[UUID] = None
) -> FollowUpTask:
    membership = get_active_membership(user, agency_id)
    target_membership_id = assigned_membership_id or (membership.id if membership else None)
    if not target_membership_id:
        raise PermissionDeniedDomainError("مشاور مسئول وظیفه مشخص نیست.")
    return FollowUpTask.objects.all_tenants().create(
        agency_id=agency_id,
        customer_id=customer_id,
        assigned_membership_id=target_membership_id,
        title=title.strip(),
        due_at=due_at,
        created_by=user,
    )


@transaction.atomic
def update_follow_up_task_status(*, user: User, agency_id: UUID, task_id: UUID, status_value: str) -> FollowUpTask:
    task = list_follow_up_tasks(user=user, agency_id=agency_id).filter(id=task_id).first()
    if not task:
        raise NotFoundDomainError("وظیفه پیگیری یافت نشد.")
    task.status = status_value
    if status_value == FollowUpTask.Status.COMPLETED:
        task.completed_at = timezone.now()
    task.updated_by = user
    task.save()
    return task


def list_interactions(*, user: User, agency_id: UUID, customer_id: Optional[UUID] = None):
    qs = (
        CustomerInteractionLog.objects.all_tenants()
        .filter(agency_id=agency_id)
        .select_related("customer", "membership__user")
    )
    if customer_id:
        qs = qs.filter(customer_id=customer_id)
    return qs.order_by("-created_at")


@transaction.atomic
def add_interaction_log(*, user: User, agency_id: UUID, customer_id: UUID, channel: str, summary: str, is_private: bool = True) -> CustomerInteractionLog:
    membership = get_active_membership(user, agency_id)
    return CustomerInteractionLog.objects.all_tenants().create(
        agency_id=agency_id,
        customer_id=customer_id,
        membership=membership,
        channel=channel,
        summary=summary.strip(),
        is_private=is_private,
        created_by=user,
    )
