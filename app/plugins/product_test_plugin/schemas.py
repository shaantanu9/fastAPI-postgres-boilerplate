"""ProductTest Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class ProductTestBase(BaseModel):
    """Base schema for ProductTest."""

    name: str
    price: float
    category: str


class ProductTestCreate(ProductTestBase):
    """Schema for creating ProductTest."""



class ProductTestUpdate(BaseModel):
    """Schema for updating ProductTest."""

    id: int | None = None
    name: str | None = None
    price: float | None = None
    category: str | None = None


class ProductTestResponse(ProductTestBase):
    """Schema for ProductTest response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductTestList(BaseModel):
    """Schema for ProductTest list response."""

    items: list[ProductTestResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductTestSearch(BaseModel):
    """Schema for ProductTest search parameters."""

    query: str | None = None
    page: int = 1
    size: int = 10
    sort_by: str | None = None
    sort_order: str | None = "asc"
