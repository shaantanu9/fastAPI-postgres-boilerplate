"""
Customer Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class CustomerBase(BaseModel):
    """Base schema for Customer"""
    name: str
    email: str
    phone: str


class CustomerCreate(CustomerBase):
    """Schema for creating Customer"""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating Customer"""
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerResponse(CustomerBase):
    """Schema for Customer response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CustomerList(BaseModel):
    """Schema for Customer list response"""
    items: List[CustomerResponse]
    total: int
    page: int
    size: int
    pages: int


class CustomerSearch(BaseModel):
    """Schema for Customer search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
