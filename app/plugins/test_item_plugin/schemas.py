"""TestItem Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TestItemBase(BaseModel):
    """Base schema for TestItem."""

    name: str
    description: str
    priority: int | None = Field(default=1, description="Item priority")
    item_status: str | None = Field(default="active", description="Item status")
    rating: int | None = Field(default=0, description="Item rating")


class TestItemCreate(TestItemBase):
    """Schema for creating TestItem."""



class TestItemUpdate(BaseModel):
    """Schema for updating TestItem."""

    id: int | None = None
    name: str | None = None
    description: str | None = None
    priority: int | None = None
    item_status: str | None = None
    rating: int | None = None


class TestItemResponse(TestItemBase):
    """Schema for TestItem response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestItemList(BaseModel):
    """Schema for TestItem list response."""

    items: list[TestItemResponse]
    total: int
    page: int
    size: int
    pages: int


class TestItemSearch(BaseModel):
    """Schema for TestItem search parameters."""

    query: str | None = None
    page: int = 1
    size: int = 10
    sort_by: str | None = None
    sort_order: str | None = "asc"
