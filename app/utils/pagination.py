"""
Advanced Pagination System for FastAPI.

This module provides comprehensive pagination strategies:
- Offset-based pagination (traditional)
- Cursor-based pagination (for large datasets)
- Page-based pagination (user-friendly)
- Time-based pagination (for time-series data)
"""
from typing import Optional, List, Dict, Any, Generic, TypeVar, Union, Callable
from pydantic import BaseModel, Field, validator
from sqlalchemy import func, text, asc, desc
from sqlalchemy.orm import Query
from sqlalchemy.sql import Select
from datetime import datetime
import base64
import json
from urllib.parse import urlencode
from fastapi import Query as QueryParam, Request
import math

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Base pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Number of items per page")
    
    @validator('size')
    def validate_size(cls, v):
        if v > 100:
            raise ValueError('Page size cannot exceed 100')
        return v


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters."""
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    size: int = Field(20, ge=1, le=100, description="Number of items per page")
    direction: str = Field("forward", description="Pagination direction: forward or backward")
    
    @validator('direction')
    def validate_direction(cls, v):
        if v not in ['forward', 'backward']:
            raise ValueError('Direction must be either "forward" or "backward"')
        return v


class TimePaginationParams(BaseModel):
    """Time-based pagination parameters."""
    before: Optional[datetime] = Field(None, description="Get items before this time")
    after: Optional[datetime] = Field(None, description="Get items after this time")
    size: int = Field(20, ge=1, le=100, description="Number of items per page")
    order: str = Field("desc", description="Time ordering: asc or desc")
    
    @validator('order')
    def validate_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('Order must be either "asc" or "desc"')
        return v


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int]
    previous_page: Optional[int]


class CursorInfo(BaseModel):
    """Cursor pagination metadata."""
    has_next: bool
    has_previous: bool
    next_cursor: Optional[str]
    previous_cursor: Optional[str]
    current_size: int
    direction: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    pagination: PaginationInfo
    
    class Config:
        arbitrary_types_allowed = True


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response."""
    items: List[T]
    cursor_info: CursorInfo
    
    class Config:
        arbitrary_types_allowed = True


class TimePaginatedResponse(BaseModel, Generic[T]):
    """Time-based paginated response."""
    items: List[T]
    time_info: Dict[str, Any]
    
    class Config:
        arbitrary_types_allowed = True


class Paginator:
    """
    Advanced paginator with multiple pagination strategies.
    """
    
    @staticmethod
    def paginate_offset(
        query: Union[Query, Select],
        params: PaginationParams,
        count_query: Optional[Union[Query, Select]] = None
    ) -> Dict[str, Any]:
        """
        Offset-based pagination (traditional pagination).
        
        Pros: Simple, user-friendly page numbers
        Cons: Performance degrades with large offsets, data consistency issues
        """
        # Calculate offset
        offset = (params.page - 1) * params.size
        
        # Get total count
        if count_query is not None:
            total_items = count_query.scalar()
        else:
            if hasattr(query, 'count'):
                total_items = query.count()
            else:
                # For SQLAlchemy Select statements
                total_items = query.session.execute(
                    func.count().select_from(query.subquery())
                ).scalar()
        
        # Calculate pagination metadata
        total_pages = math.ceil(total_items / params.size)
        has_next = params.page < total_pages
        has_previous = params.page > 1
        
        # Apply pagination to query
        if hasattr(query, 'limit'):
            # SQLAlchemy ORM Query
            paginated_query = query.offset(offset).limit(params.size)
        else:
            # SQLAlchemy Core Select
            paginated_query = query.offset(offset).limit(params.size)
        
        return {
            'query': paginated_query,
            'pagination': PaginationInfo(
                current_page=params.page,
                page_size=params.size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=has_next,
                has_previous=has_previous,
                next_page=params.page + 1 if has_next else None,
                previous_page=params.page - 1 if has_previous else None
            )
        }
    
    @staticmethod
    def paginate_cursor(
        query: Union[Query, Select],
        params: CursorPaginationParams,
        cursor_column: str,
        encode_cursor: Callable = None,
        decode_cursor: Callable = None
    ) -> Dict[str, Any]:
        """
        Cursor-based pagination (for large datasets).
        
        Pros: Consistent performance, no duplicates/missing items
        Cons: No random page access, more complex implementation
        """
        if encode_cursor is None:
            encode_cursor = Paginator._encode_cursor
        if decode_cursor is None:
            decode_cursor = Paginator._decode_cursor
        
        # Decode cursor if provided
        cursor_value = None
        if params.cursor:
            try:
                cursor_value = decode_cursor(params.cursor)
            except Exception:
                raise ValueError("Invalid cursor format")
        
        # Apply cursor filtering
        if cursor_value is not None:
            if params.direction == "forward":
                if hasattr(query, 'filter'):
                    query = query.filter(getattr(query.column_descriptions[0]['type'], cursor_column) > cursor_value)
                else:
                    # For SQLAlchemy Select
                    query = query.where(getattr(query.table.c, cursor_column) > cursor_value)
            else:  # backward
                if hasattr(query, 'filter'):
                    query = query.filter(getattr(query.column_descriptions[0]['type'], cursor_column) < cursor_value)
                else:
                    query = query.where(getattr(query.table.c, cursor_column) < cursor_value)
        
        # Order by cursor column
        if params.direction == "forward":
            if hasattr(query, 'order_by'):
                query = query.order_by(asc(cursor_column))
            else:
                query = query.order_by(asc(getattr(query.table.c, cursor_column)))
        else:
            if hasattr(query, 'order_by'):
                query = query.order_by(desc(cursor_column))
            else:
                query = query.order_by(desc(getattr(query.table.c, cursor_column)))
        
        # Fetch one extra item to check if there are more results
        if hasattr(query, 'limit'):
            items_query = query.limit(params.size + 1)
        else:
            items_query = query.limit(params.size + 1)
        
        # Execute query and get results
        if hasattr(items_query, 'all'):
            results = items_query.all()
        else:
            results = list(items_query)
        
        # Check if there are more items
        has_more = len(results) > params.size
        if has_more:
            results = results[:params.size]
        
        # Generate cursors
        next_cursor = None
        previous_cursor = None
        
        if results:
            if params.direction == "forward" and has_more:
                next_cursor = encode_cursor(getattr(results[-1], cursor_column))
            if params.direction == "backward" and has_more:
                previous_cursor = encode_cursor(getattr(results[-1], cursor_column))
        
        return {
            'items': results,
            'cursor_info': CursorInfo(
                has_next=has_more if params.direction == "forward" else len(results) == params.size,
                has_previous=has_more if params.direction == "backward" else cursor_value is not None,
                next_cursor=next_cursor,
                previous_cursor=previous_cursor,
                current_size=len(results),
                direction=params.direction
            )
        }
    
    @staticmethod
    def paginate_time(
        query: Union[Query, Select],
        params: TimePaginationParams,
        time_column: str
    ) -> Dict[str, Any]:
        """
        Time-based pagination (for time-series data).
        
        Pros: Natural for time-series data, consistent ordering
        Cons: Limited to time-based sorting
        """
        # Apply time filtering
        if params.before:
            if hasattr(query, 'filter'):
                query = query.filter(getattr(query.column_descriptions[0]['type'], time_column) < params.before)
            else:
                query = query.where(getattr(query.table.c, time_column) < params.before)
        
        if params.after:
            if hasattr(query, 'filter'):
                query = query.filter(getattr(query.column_descriptions[0]['type'], time_column) > params.after)
            else:
                query = query.where(getattr(query.table.c, time_column) > params.after)
        
        # Apply ordering
        if params.order == "desc":
            if hasattr(query, 'order_by'):
                query = query.order_by(desc(time_column))
            else:
                query = query.order_by(desc(getattr(query.table.c, time_column)))
        else:
            if hasattr(query, 'order_by'):
                query = query.order_by(asc(time_column))
            else:
                query = query.order_by(asc(getattr(query.table.c, time_column)))
        
        # Fetch items with one extra to check for more
        if hasattr(query, 'limit'):
            items_query = query.limit(params.size + 1)
        else:
            items_query = query.limit(params.size + 1)
        
        # Execute query
        if hasattr(items_query, 'all'):
            results = items_query.all()
        else:
            results = list(items_query)
        
        # Check if there are more items
        has_more = len(results) > params.size
        if has_more:
            results = results[:params.size]
        
        # Generate time info
        time_info = {
            "has_more": has_more,
            "count": len(results),
            "order": params.order
        }
        
        if results:
            first_time = getattr(results[0], time_column)
            last_time = getattr(results[-1], time_column)
            
            time_info.update({
                "first_timestamp": first_time.isoformat() if isinstance(first_time, datetime) else str(first_time),
                "last_timestamp": last_time.isoformat() if isinstance(last_time, datetime) else str(last_time),
            })
        
        return {
            'items': results,
            'time_info': time_info
        }
    
    @staticmethod
    def _encode_cursor(value: Any) -> str:
        """Encode cursor value to base64 string."""
        if isinstance(value, datetime):
            value = value.isoformat()
        
        cursor_data = json.dumps(value, default=str)
        return base64.b64encode(cursor_data.encode()).decode()
    
    @staticmethod
    def _decode_cursor(cursor: str) -> Any:
        """Decode cursor from base64 string."""
        cursor_data = base64.b64decode(cursor.encode()).decode()
        return json.loads(cursor_data)


class PaginationBuilder:
    """
    Builder pattern for creating paginated queries.
    """
    
    def __init__(self, query: Union[Query, Select]):
        self.query = query
        self.strategy = "offset"
        self.params = None
        self.cursor_column = "id"
        self.time_column = "created_at"
        self.count_query = None
    
    def offset_pagination(self, params: PaginationParams):
        """Use offset-based pagination."""
        self.strategy = "offset"
        self.params = params
        return self
    
    def cursor_pagination(self, params: CursorPaginationParams, cursor_column: str = "id"):
        """Use cursor-based pagination."""
        self.strategy = "cursor"
        self.params = params
        self.cursor_column = cursor_column
        return self
    
    def time_pagination(self, params: TimePaginationParams, time_column: str = "created_at"):
        """Use time-based pagination."""
        self.strategy = "time"
        self.params = params
        self.time_column = time_column
        return self
    
    def with_count_query(self, count_query: Union[Query, Select]):
        """Provide custom count query for offset pagination."""
        self.count_query = count_query
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the paginated result."""
        if self.strategy == "offset":
            return Paginator.paginate_offset(self.query, self.params, self.count_query)
        elif self.strategy == "cursor":
            return Paginator.paginate_cursor(self.query, self.params, self.cursor_column)
        elif self.strategy == "time":
            return Paginator.paginate_time(self.query, self.params, self.time_column)
        else:
            raise ValueError(f"Unknown pagination strategy: {self.strategy}")


# Dependency functions for FastAPI
def get_pagination_params(
    page: int = QueryParam(1, ge=1, description="Page number"),
    size: int = QueryParam(20, ge=1, le=100, description="Page size")
) -> PaginationParams:
    """FastAPI dependency for offset pagination parameters."""
    return PaginationParams(page=page, size=size)


def get_cursor_pagination_params(
    cursor: Optional[str] = QueryParam(None, description="Pagination cursor"),
    size: int = QueryParam(20, ge=1, le=100, description="Page size"),
    direction: str = QueryParam("forward", description="Pagination direction")
) -> CursorPaginationParams:
    """FastAPI dependency for cursor pagination parameters."""
    return CursorPaginationParams(cursor=cursor, size=size, direction=direction)


def get_time_pagination_params(
    before: Optional[datetime] = QueryParam(None, description="Get items before this time"),
    after: Optional[datetime] = QueryParam(None, description="Get items after this time"),
    size: int = QueryParam(20, ge=1, le=100, description="Page size"),
    order: str = QueryParam("desc", description="Time ordering")
) -> TimePaginationParams:
    """FastAPI dependency for time pagination parameters."""
    return TimePaginationParams(before=before, after=after, size=size, order=order)


# Utility functions
def build_pagination_links(request: Request, pagination: PaginationInfo) -> Dict[str, Optional[str]]:
    """Build pagination links for REST API."""
    base_url = str(request.url.remove_query_params("page"))
    
    links = {
        "self": f"{base_url}?page={pagination.current_page}&size={pagination.page_size}",
        "first": f"{base_url}?page=1&size={pagination.page_size}",
        "last": f"{base_url}?page={pagination.total_pages}&size={pagination.page_size}",
        "next": None,
        "previous": None
    }
    
    if pagination.has_next:
        links["next"] = f"{base_url}?page={pagination.next_page}&size={pagination.page_size}"
    
    if pagination.has_previous:
        links["previous"] = f"{base_url}?page={pagination.previous_page}&size={pagination.page_size}"
    
    return links


def build_cursor_links(request: Request, cursor_info: CursorInfo) -> Dict[str, Optional[str]]:
    """Build cursor pagination links."""
    base_url = str(request.url.remove_query_params("cursor", "direction"))
    
    links = {
        "self": str(request.url),
        "next": None,
        "previous": None
    }
    
    if cursor_info.has_next and cursor_info.next_cursor:
        links["next"] = f"{base_url}?cursor={cursor_info.next_cursor}&direction=forward&size={cursor_info.current_size}"
    
    if cursor_info.has_previous and cursor_info.previous_cursor:
        links["previous"] = f"{base_url}?cursor={cursor_info.previous_cursor}&direction=backward&size={cursor_info.current_size}"
    
    return links 