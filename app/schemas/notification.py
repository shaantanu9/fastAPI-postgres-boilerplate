"""Schemas for notification preferences."""

from pydantic import BaseModel

from app.models.notification import NotificationCategory, NotificationChannel


class NotificationPreferenceBase(BaseModel):
    category: NotificationCategory
    channel: NotificationChannel
    enabled: bool = True


class NotificationPreferenceCreate(NotificationPreferenceBase):
    pass


class NotificationPreferenceUpdate(NotificationPreferenceBase):
    pass


class NotificationPreferenceRead(NotificationPreferenceBase):
    id: str

    class Config:
        orm_mode = True
