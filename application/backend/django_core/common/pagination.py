from math import ceil
from typing import Callable, Iterable, Tuple
from django.db.models import QuerySet


def paginate_queryset(
    qs: QuerySet,
    *,
    page: int = 1,
    page_size: int = 20,
    serializer_fn: Callable | None = None,
) -> Tuple[list, dict]:
    safe_page = max(1, page)
    safe_size = min(max(1, page_size), 100)
    total = qs.count()
    total_pages = max(1, ceil(total / safe_size)) if total else 1
    offset = (safe_page - 1) * safe_size
    items_raw = list(qs[offset : offset + safe_size])
    items = [serializer_fn(item) for item in items_raw] if serializer_fn else items_raw
    meta = {
        "count": total,
        "page": safe_page,
        "page_size": safe_size,
        "total_pages": total_pages,
        "has_next": safe_page < total_pages,
        "has_prev": safe_page > 1,
    }
    return items, meta


def paginate_list(items: Iterable, *, page: int = 1, page_size: int = 20) -> Tuple[list, dict]:
    seq = list(items)
    safe_page = max(1, page)
    safe_size = min(max(1, page_size), 100)
    total = len(seq)
    total_pages = max(1, ceil(total / safe_size)) if total else 1
    offset = (safe_page - 1) * safe_size
    meta = {
        "count": total,
        "page": safe_page,
        "page_size": safe_size,
        "total_pages": total_pages,
        "has_next": safe_page < total_pages,
        "has_prev": safe_page > 1,
    }
    return seq[offset : offset + safe_size], meta
