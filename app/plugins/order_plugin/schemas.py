"""
Order Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from pydantic import EmailStr
from datetime import datetime
from datetime import datetime


class OrderBase(BaseModel):
    """Base schema for Order"""
    customer_name: str
    customer_email: EmailStr
    total_amount: float = Field(..., gt=0)
    status: str
    order_date: datetime
    shipping_address: str
    notes: str


class OrderCreate(OrderBase):
    """Schema for creating Order"""
    pass


class OrderUpdate(BaseModel):
    """Schema for updating Order"""
    id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    total_amount: Optional[float] = Field(None, gt=0)
    status: Optional[str] = None
    order_date: Optional[datetime] = None
    shipping_address: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(OrderBase):
    """Schema for Order response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderList(BaseModel):
    """Schema for Order list response"""
    items: List[OrderResponse]
    total: int
    page: int
    size: int
    pages: int


class OrderSearch(BaseModel):
    """Schema for Order search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
