"""
ShoppingCart Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from datetime import datetime


class ShoppingCartBase(BaseModel):
    """Base schema for ShoppingCart"""
    user_id: int
    session_id: str
    status: Literal["active", "abandoned", "checked_out"]
    total_items: int
    total_price: float
    currency: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    coupon_code: str
    notes: str
    is_guest: bool
    metadata: Dict[str, Any]


class ShoppingCartCreate(ShoppingCartBase):
    """Schema for creating ShoppingCart"""
    pass


class ShoppingCartUpdate(BaseModel):
    """Schema for updating ShoppingCart"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    status: Optional[Literal["active", "abandoned", "checked_out"]] = None
    total_items: Optional[int] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    coupon_code: Optional[str] = None
    notes: Optional[str] = None
    is_guest: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ShoppingCartResponse(ShoppingCartBase):
    """Schema for ShoppingCart response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ShoppingCartList(BaseModel):
    """Schema for ShoppingCart list response"""
    items: List[ShoppingCartResponse]
    total: int
    page: int
    size: int
    pages: int


class ShoppingCartSearch(BaseModel):
    """Schema for ShoppingCart search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
