"""
Product Pydantic schemas
"""
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ProductBase(BaseModel):
    """Base schema for Product"""
    name: str
    price: float = Field(..., gt=0)
    category: Literal["electronics", "clothing", "books"]
    description: Optional[str] = None
    stock: int = Field(..., ge=0)
    is_active: bool


class ProductCreate(ProductBase):
    """Schema for creating Product"""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating Product"""
    id: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category: Optional[Literal["electronics", "clothing", "books"]] = None
    description: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema for Product response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductList(BaseModel):
    """Schema for Product list response"""
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductSearch(BaseModel):
    """Schema for Product search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
