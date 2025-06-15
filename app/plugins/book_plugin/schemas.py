"""
Book Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import date
from datetime import datetime


class BookBase(BaseModel):
    """Base schema for Book"""
    title: str
    author: str
    isbn: str
    pages: int
    published_date: date
    price: float


class BookCreate(BookBase):
    """Schema for creating Book"""
    pass


class BookUpdate(BaseModel):
    """Schema for updating Book"""
    id: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    pages: Optional[int] = None
    published_date: Optional[date] = None
    price: Optional[float] = None


class BookResponse(BookBase):
    """Schema for Book response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BookList(BaseModel):
    """Schema for Book list response"""
    items: List[BookResponse]
    total: int
    page: int
    size: int
    pages: int


class BookSearch(BaseModel):
    """Schema for Book search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
