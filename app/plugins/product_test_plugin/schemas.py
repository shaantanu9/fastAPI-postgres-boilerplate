"""
ProductTest Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class ProductTestBase(BaseModel):
    """Base schema for ProductTest"""
    name: str
    price: float
    category: str


class ProductTestCreate(ProductTestBase):
    """Schema for creating ProductTest"""
    pass


class ProductTestUpdate(BaseModel):
    """Schema for updating ProductTest"""
    id: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None


class ProductTestResponse(ProductTestBase):
    """Schema for ProductTest response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductTestList(BaseModel):
    """Schema for ProductTest list response"""
    items: List[ProductTestResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductTestSearch(BaseModel):
    """Schema for ProductTest search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
