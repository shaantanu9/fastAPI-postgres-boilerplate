"""
TestCleanup Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class TestCleanupBase(BaseModel):
    """Base schema for TestCleanup"""
    name: str
    description: str


class TestCleanupCreate(TestCleanupBase):
    """Schema for creating TestCleanup"""
    pass


class TestCleanupUpdate(BaseModel):
    """Schema for updating TestCleanup"""
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None


class TestCleanupResponse(TestCleanupBase):
    """Schema for TestCleanup response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TestCleanupList(BaseModel):
    """Schema for TestCleanup list response"""
    items: List[TestCleanupResponse]
    total: int
    page: int
    size: int
    pages: int


class TestCleanupSearch(BaseModel):
    """Schema for TestCleanup search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
