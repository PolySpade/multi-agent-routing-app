"""
Pagination utilities for list endpoints.

Provides standard pagination for API endpoints that return large datasets.
"""

from typing import List, TypeVar, Generic
from pydantic import BaseModel
from math import ceil

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response model.

    Attributes:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def paginate(items: List[T], page: int = 1, page_size: int = 50) -> PaginatedResponse[T]:
    """
    Paginate a list of items.

    Args:
        items: Full list of items to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        PaginatedResponse with items for the requested page

    Example:
        >>> all_items = [1, 2, 3, ..., 100]
        >>> result = paginate(all_items, page=2, page_size=10)
        >>> print(result.items)  # [11, 12, ..., 20]
        >>> print(result.total_pages)  # 10
    """
    total = len(items)
    total_pages = ceil(total / page_size) if page_size > 0 else 0

    # Ensure page is within bounds
    page = max(1, min(page, total_pages if total_pages > 0 else 1))

    start = (page - 1) * page_size
    end = start + page_size

    return PaginatedResponse(
        items=items[start:end],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
