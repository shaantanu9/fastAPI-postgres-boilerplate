# app/core/listing_service.py

import inspect
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from datetime import datetime, date
from enum import Enum

from fastapi import Query, HTTPException, status
from pydantic import BaseModel, Field, create_model
from sqlalchemy import and_, or_, asc, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select

from app.db.base import Base


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "startswith"
    ENDS_WITH = "endswith"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    LIKE = "like"
    ILIKE = "ilike"


class FilterCriteria(BaseModel):
    field: str
    operator: FilterOperator
    value: Optional[Any] = None
    values: Optional[List[Any]] = None  # For IN, NOT_IN, BETWEEN operations


class SortCriteria(BaseModel):
    field: str
    order: SortOrder = SortOrder.ASC


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class SearchParams(BaseModel):
    query: Optional[str] = Field(default=None, description="Search query string")
    fields: Optional[List[str]] = Field(default=None, description="Fields to search in")


class ListingRequest(BaseModel):
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    filters: List[FilterCriteria] = Field(default_factory=list)
    sort: List[SortCriteria] = Field(default_factory=list)
    search: Optional[SearchParams] = None
    include_relations: List[str] = Field(default_factory=list)


class ListingResponse(BaseModel):
    items: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    filters_applied: List[FilterCriteria]
    sort_applied: List[SortCriteria]
    search_applied: Optional[SearchParams] = None


class ModelIntrospector:
    """Utility class to introspect SQLAlchemy models"""
    
    @staticmethod
    def get_model_fields(model: Type[Base]) -> Dict[str, Any]:
        """Get all fields of a SQLAlchemy model with their types"""
        fields = {}
        
        # Get columns
        for column in model.__table__.columns:
            fields[column.name] = {
                'type': column.type.python_type if hasattr(column.type, 'python_type') else str,
                'nullable': column.nullable,
                'primary_key': column.primary_key,
                'foreign_key': bool(column.foreign_keys),
                'column': column
            }
        
        # Get relationships
        if hasattr(model, '__mapper__'):
            for rel_name, relationship in model.__mapper__.relationships.items():
                fields[rel_name] = {
                    'type': 'relationship',
                    'target_model': relationship.mapper.class_,
                    'relationship': relationship
                }
        
        return fields
    
    @staticmethod
    def get_searchable_fields(model: Type[Base]) -> List[str]:
        """Get list of searchable fields (text fields) for a model"""
        searchable = []
        for column in model.__table__.columns:
            if hasattr(column.type, 'python_type'):
                if column.type.python_type in (str, ):
                    searchable.append(column.name)
        return searchable
    
    @staticmethod
    def validate_field_access(model: Type[Base], field_name: str) -> bool:
        """Validate if a field can be accessed on the model"""
        return hasattr(model, field_name)


class QueryBuilder:
    """Advanced query builder for dynamic filtering and sorting"""
    
    def __init__(self, model: Type[Base], session: AsyncSession):
        self.model = model
        self.session = session
        self.introspector = ModelIntrospector()
        self.model_fields = self.introspector.get_model_fields(model)
    
    def build_base_query(self) -> Select:
        """Build base select query"""
        return Select(self.model)
    
    def apply_filters(self, query: Select, filters: List[FilterCriteria]) -> Select:
        """Apply filtering conditions to query"""
        if not filters:
            return query
        
        conditions = []
        for filter_criteria in filters:
            condition = self._build_filter_condition(filter_criteria)
            if condition is not None:
                conditions.append(condition)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def _build_filter_condition(self, filter_criteria: FilterCriteria):
        """Build individual filter condition"""
        field_name = filter_criteria.field
        operator = filter_criteria.operator
        value = filter_criteria.value
        values = filter_criteria.values
        
        # Validate field exists
        if not self.introspector.validate_field_access(self.model, field_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field '{field_name}' does not exist on model {self.model.__name__}"
            )
        
        # Get the column
        column = getattr(self.model, field_name)
        
        # Build condition based on operator
        if operator == FilterOperator.EQUALS:
            return column == value
        elif operator == FilterOperator.NOT_EQUALS:
            return column != value
        elif operator == FilterOperator.GREATER_THAN:
            return column > value
        elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return column >= value
        elif operator == FilterOperator.LESS_THAN:
            return column < value
        elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return column <= value
        elif operator == FilterOperator.CONTAINS:
            return column.contains(value)
        elif operator == FilterOperator.STARTS_WITH:
            return column.startswith(value)
        elif operator == FilterOperator.ENDS_WITH:
            return column.endswith(value)
        elif operator == FilterOperator.LIKE:
            return column.like(value)
        elif operator == FilterOperator.ILIKE:
            return column.ilike(value)
        elif operator == FilterOperator.IN:
            return column.in_(values or [])
        elif operator == FilterOperator.NOT_IN:
            return ~column.in_(values or [])
        elif operator == FilterOperator.IS_NULL:
            return column.is_(None)
        elif operator == FilterOperator.IS_NOT_NULL:
            return column.isnot(None)
        elif operator == FilterOperator.BETWEEN:
            if values and len(values) == 2:
                return column.between(values[0], values[1])
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="BETWEEN operator requires exactly 2 values"
                )
        
        return None
    
    def apply_search(self, query: Select, search_params: Optional[SearchParams]) -> Select:
        """Apply full-text search to query"""
        if not search_params or not search_params.query:
            return query
        
        search_query = search_params.query
        search_fields = search_params.fields or self.introspector.get_searchable_fields(self.model)
        
        if not search_fields:
            return query
        
        # Build search conditions for each field
        search_conditions = []
        for field_name in search_fields:
            if self.introspector.validate_field_access(self.model, field_name):
                column = getattr(self.model, field_name)
                # Use ILIKE for case-insensitive search
                search_conditions.append(column.ilike(f"%{search_query}%"))
        
        if search_conditions:
            query = query.where(or_(*search_conditions))
        
        return query
    
    def apply_sorting(self, query: Select, sort_criteria: List[SortCriteria]) -> Select:
        """Apply sorting to query"""
        if not sort_criteria:
            # Default sort by primary key
            pk_columns = [col for col in self.model.__table__.columns if col.primary_key]
            if pk_columns:
                query = query.order_by(asc(pk_columns[0]))
            return query
        
        order_clauses = []
        for sort_criterion in sort_criteria:
            field_name = sort_criterion.field
            order = sort_criterion.order
            
            # Validate field exists
            if not self.introspector.validate_field_access(self.model, field_name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sort field '{field_name}' does not exist on model {self.model.__name__}"
                )
            
            column = getattr(self.model, field_name)
            if order == SortOrder.DESC:
                order_clauses.append(desc(column))
            else:
                order_clauses.append(asc(column))
        
        if order_clauses:
            query = query.order_by(*order_clauses)
        
        return query
    
    def apply_relations(self, query: Select, include_relations: List[str]) -> Select:
        """Apply eager loading for relationships"""
        if not include_relations:
            return query
        
        load_options = []
        for relation_name in include_relations:
            if self.introspector.validate_field_access(self.model, relation_name):
                field_info = self.model_fields.get(relation_name)
                if field_info and field_info.get('type') == 'relationship':
                    # Use selectinload for collections, joinedload for single relationships
                    relationship = field_info['relationship']
                    if relationship.uselist:
                        load_options.append(selectinload(getattr(self.model, relation_name)))
                    else:
                        load_options.append(joinedload(getattr(self.model, relation_name)))
        
        if load_options:
            query = query.options(*load_options)
        
        return query
    
    def get_count_query(self, query: Select) -> Select:
        """Get count query for pagination"""
        # Remove order by and limit clauses for count
        count_query = query.with_only_columns(func.count()).order_by(None)
        return count_query


class BaseListingService:
    """Universal listing service that can be used with any SQLAlchemy model"""
    
    def __init__(self, model: Type[Base]):
        self.model = model
        self.introspector = ModelIntrospector()
    
    async def list_items(
        self,
        session: AsyncSession,
        request: ListingRequest
    ) -> ListingResponse:
        """List items with filtering, sorting, and pagination"""
        
        # Build query
        query_builder = QueryBuilder(self.model, session)
        query = query_builder.build_base_query()
        
        # Apply search
        query = query_builder.apply_search(query, request.search)
        
        # Apply filters
        query = query_builder.apply_filters(query, request.filters)
        
        # Get total count before pagination
        count_query = query_builder.get_count_query(query)
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Apply sorting
        query = query_builder.apply_sorting(query, request.sort)
        
        # Apply relationships
        query = query_builder.apply_relations(query, request.include_relations)
        
        # Apply pagination
        query = query.offset(request.pagination.offset).limit(request.pagination.limit)
        
        # Execute query
        result = await session.execute(query)
        items = result.scalars().all()
        
        # Convert items to dictionaries
        item_dicts = []
        for item in items:
            item_dict = {}
            for column in self.model.__table__.columns:
                value = getattr(item, column.name)
                # Handle datetime serialization
                if isinstance(value, (datetime, date)):
                    value = value.isoformat()
                item_dict[column.name] = value
            
            # Include relationships if requested
            for relation_name in request.include_relations:
                if hasattr(item, relation_name):
                    rel_value = getattr(item, relation_name)
                    if rel_value is not None:
                        if isinstance(rel_value, list):
                            item_dict[relation_name] = [
                                self._serialize_related_item(rel_item) for rel_item in rel_value
                            ]
                        else:
                            item_dict[relation_name] = self._serialize_related_item(rel_value)
                    else:
                        item_dict[relation_name] = None
            
            item_dicts.append(item_dict)
        
        # Calculate pagination info
        total_pages = (total_count + request.pagination.page_size - 1) // request.pagination.page_size
        has_next = request.pagination.page < total_pages
        has_previous = request.pagination.page > 1
        
        return ListingResponse(
            items=item_dicts,
            total_count=total_count,
            page=request.pagination.page,
            page_size=request.pagination.page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            filters_applied=request.filters,
            sort_applied=request.sort,
            search_applied=request.search
        )
    
    def _serialize_related_item(self, item: Any) -> Dict[str, Any]:
        """Serialize a related item"""
        if hasattr(item, '__table__'):
            serialized = {}
            for column in item.__table__.columns:
                value = getattr(item, column.name)
                if isinstance(value, (datetime, date)):
                    value = value.isoformat()
                serialized[column.name] = value
            return serialized
        return str(item)
    
    def get_filterable_fields(self) -> Dict[str, Any]:
        """Get list of filterable fields for the model"""
        return self.introspector.get_model_fields(self.model)
    
    def get_searchable_fields(self) -> List[str]:
        """Get list of searchable fields for the model"""
        return self.introspector.get_searchable_fields(self.model)


def create_listing_params_model(model: Type[Base]) -> Type[BaseModel]:
    """Create a dynamic Pydantic model for listing parameters based on SQLAlchemy model"""
    introspector = ModelIntrospector()
    model_fields = introspector.get_model_fields(model)
    
    # Create filter parameters for each field
    filter_fields = {}
    for field_name, field_info in model_fields.items():
        if field_info.get('type') != 'relationship':
            # Create optional filter parameters
            filter_fields[f"{field_name}__eq"] = (Optional[str], Field(None, description=f"Filter {field_name} equals"))
            filter_fields[f"{field_name}__ne"] = (Optional[str], Field(None, description=f"Filter {field_name} not equals"))
            filter_fields[f"{field_name}__contains"] = (Optional[str], Field(None, description=f"Filter {field_name} contains"))
            filter_fields[f"{field_name}__in"] = (Optional[List[str]], Field(None, description=f"Filter {field_name} in list"))
    
    # Add standard parameters
    filter_fields.update({
        'page': (int, Field(1, ge=1, description="Page number")),
        'page_size': (int, Field(20, ge=1, le=100, description="Items per page")),
        'sort_by': (Optional[str], Field(None, description="Sort by field")),
        'sort_order': (Optional[SortOrder], Field(SortOrder.ASC, description="Sort order")),
        'search': (Optional[str], Field(None, description="Search query")),
        'search_fields': (Optional[List[str]], Field(None, description="Fields to search in")),
    })
    
    return create_model(f"{model.__name__}ListingParams", **filter_fields)


# Utility function to create route with automatic filtering
def create_listing_route(model: Type[Base], service: BaseListingService):
    """Create FastAPI route function with automatic parameter handling"""
    
    async def list_route(
        session: AsyncSession,
        **params
    ) -> ListingResponse:
        # Convert query parameters to ListingRequest
        request = _convert_params_to_request(params)
        return await service.list_items(session, request)
    
    return list_route


def _convert_params_to_request(params: Dict[str, Any]) -> ListingRequest:
    """Convert query parameters to ListingRequest"""
    # Extract pagination
    pagination = PaginationParams(
        page=params.get('page', 1),
        page_size=params.get('page_size', 20)
    )
    
    # Extract search
    search = None
    if params.get('search'):
        search = SearchParams(
            query=params['search'],
            fields=params.get('search_fields')
        )
    
    # Extract sort
    sort = []
    if params.get('sort_by'):
        sort.append(SortCriteria(
            field=params['sort_by'],
            order=params.get('sort_order', SortOrder.ASC)
        ))
    
    # Extract filters
    filters = []
    for key, value in params.items():
        if '__' in key and value is not None:
            field_name, operator = key.rsplit('__', 1)
            if operator in [op.value for op in FilterOperator]:
                if operator == 'in':
                    filters.append(FilterCriteria(
                        field=field_name,
                        operator=FilterOperator(operator),
                        values=value if isinstance(value, list) else [value]
                    ))
                else:
                    filters.append(FilterCriteria(
                        field=field_name,
                        operator=FilterOperator(operator),
                        value=value
                    ))
    
    return ListingRequest(
        pagination=pagination,
        filters=filters,
        sort=sort,
        search=search
    ) 