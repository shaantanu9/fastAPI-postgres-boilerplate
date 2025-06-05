"""
TestItem Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class TestItemBase(BaseModel):
    """Base schema for TestItem"""
    name: str
    description: str
    priority: Optional[int] = Field(default=1, description="Item priority")
    item_status: Optional[str] = Field(default="active", description="Item status")
    rating: Optional[int] = Field(default=0, description="Item rating")


class TestItemCreate(TestItemBase):
    """Schema for creating TestItem"""
    pass


class TestItemUpdate(BaseModel):
    """Schema for updating TestItem"""
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    item_status: Optional[str] = None
    rating: Optional[int] = None


class TestItemResponse(TestItemBase):
    """Schema for TestItem response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TestItemList(BaseModel):
    """Schema for TestItem list response"""
    items: List[TestItemResponse]
    total: int
    page: int
    size: int
    pages: int


class TestItemSearch(BaseModel):
    """Schema for TestItem search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
