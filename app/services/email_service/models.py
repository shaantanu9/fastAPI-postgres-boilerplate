"""Email Service Models.

Pydantic models for email functionality including recipients, attachments,
templates, requests, and responses.
"""

import mimetypes
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, EmailStr, field_validator


class EmailRecipient(BaseModel):
    """Email recipient model with validation."""

    email: EmailStr
    name: str | None = None

    def format_address(self) -> str:
        """Format email address with optional name."""
        from email.utils import formataddr

        if self.name:
            return formataddr((self.name, self.email))
        return str(self.email)


class EmailAttachment(BaseModel):
    """Email attachment model."""

    filename: str
    content: bytes
    content_type: str | None = None
    disposition: str = "attachment"  # attachment or inline
    content_id: str | None = None  # for inline images

    @field_validator("content_type", mode="before")
    @classmethod
    def set_content_type(cls, v, info):
        if v is None and info.data and "filename" in info.data:
            content_type, _ = mimetypes.guess_type(info.data and info.data["filename"])
            return content_type or "application/octet-stream"
        return v


class EmailTemplate(BaseModel):
    """Email template model."""

    subject: str
    html_content: str | None = None
    text_content: str | None = None
    template_data: dict[str, Any] = {}

    def render(self, context: dict[str, Any] | None = None) -> "EmailTemplate":
        """Render template with context data."""
        from jinja2 import Environment

        context = context or {}
        context.update(self.template_data)

        env = Environment()

        rendered_subject = env.from_string(self.subject).render(context)
        rendered_html = None
        rendered_text = None

        if self.html_content:
            rendered_html = env.from_string(self.html_content).render(context)

        if self.text_content:
            rendered_text = env.from_string(self.text_content).render(context)

        return EmailTemplate(
            subject=rendered_subject,
            html_content=rendered_html,
            text_content=rendered_text,
        )


class EmailRequest(BaseModel):
    """Comprehensive email request model."""

    # Recipients
    to_recipients: list[EmailRecipient]
    cc_recipients: list[EmailRecipient] | None = []
    bcc_recipients: list[EmailRecipient] | None = []

    # Sender information
    from_email: EmailStr
    from_name: str | None = None
    reply_to: list[EmailStr] | None = []

    # Content
    subject: str
    html_content: str | None = None
    text_content: str | None = None
    template: EmailTemplate | None = None
    template_context: dict[str, Any] = {}

    # Attachments
    attachments: list[EmailAttachment] | None = []

    # SES Configuration
    configuration_set: str | None = None
    message_tags: dict[str, str] = {}

    # Tracking and Analytics
    tracking_id: str | None = None
    campaign_id: str | None = None

    # Scheduling
    send_time: datetime | None = None  # For scheduled sending
    timezone: str | None = None

    # Advanced options
    priority: str = "normal"  # low, normal, high
    suppress_list_check: bool = False

    @field_validator("tracking_id", mode="before")
    @classmethod
    def set_tracking_id(cls, v):
        return v or str(uuid4())

    def get_rendered_content(self) -> tuple:
        """Get rendered email content."""
        if self.template:
            rendered_template = self.template.render(self.template_context)
            return (
                rendered_template.subject,
                rendered_template.html_content,
                rendered_template.text_content,
            )
        return self.subject, self.html_content, self.text_content


class EmailResponse(BaseModel):
    """Email sending response model."""

    success: bool
    message_id: str | None = None
    tracking_id: str
    error_message: str | None = None
    error_code: str | None = None
    timestamp: datetime
    delivery_status: str = "sent"  # sent, scheduled, failed, queued


class BulkEmailRequest(BaseModel):
    """Bulk email request model."""

    recipients: list[EmailRecipient]
    template_name: str
    template_data: dict[str, Any]
    from_email: EmailStr
    from_name: str | None = None
    configuration_set: str | None = None
    message_tags: dict[str, str] = {}


class EmailAccountInfo(BaseModel):
    """SES account information model."""

    account_details: dict[str, Any]
    sending_quota: dict[str, Any]
    sending_statistics: dict[str, Any]
