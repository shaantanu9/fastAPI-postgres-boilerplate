"""
Email Service Models

Pydantic models for email functionality including recipients, attachments,
templates, requests, and responses.
"""

import mimetypes
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, EmailStr, validator


class EmailRecipient(BaseModel):
    """Email recipient model with validation"""
    email: EmailStr
    name: Optional[str] = None
    
    def format_address(self) -> str:
        """Format email address with optional name"""
        from email.utils import formataddr
        if self.name:
            return formataddr((self.name, self.email))
        return str(self.email)


class EmailAttachment(BaseModel):
    """Email attachment model"""
    filename: str
    content: bytes
    content_type: Optional[str] = None
    disposition: str = "attachment"  # attachment or inline
    content_id: Optional[str] = None  # for inline images
    
    @validator('content_type', pre=True, always=True)
    def set_content_type(cls, v, values):
        if v is None and 'filename' in values:
            content_type, _ = mimetypes.guess_type(values['filename'])
            return content_type or 'application/octet-stream'
        return v


class EmailTemplate(BaseModel):
    """Email template model"""
    subject: str
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    template_data: Dict[str, Any] = {}
    
    def render(self, context: Dict[str, Any] = None) -> 'EmailTemplate':
        """Render template with context data"""
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
            text_content=rendered_text
        )


class EmailRequest(BaseModel):
    """Comprehensive email request model"""
    # Recipients
    to_recipients: List[EmailRecipient]
    cc_recipients: Optional[List[EmailRecipient]] = []
    bcc_recipients: Optional[List[EmailRecipient]] = []
    
    # Sender information
    from_email: EmailStr
    from_name: Optional[str] = None
    reply_to: Optional[List[EmailStr]] = []
    
    # Content
    subject: str
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    template: Optional[EmailTemplate] = None
    template_context: Dict[str, Any] = {}
    
    # Attachments
    attachments: Optional[List[EmailAttachment]] = []
    
    # SES Configuration
    configuration_set: Optional[str] = None
    message_tags: Dict[str, str] = {}
    
    # Tracking and Analytics
    tracking_id: Optional[str] = None
    campaign_id: Optional[str] = None
    
    # Scheduling
    send_time: Optional[datetime] = None  # For scheduled sending
    timezone: Optional[str] = None
    
    # Advanced options
    priority: str = "normal"  # low, normal, high
    suppress_list_check: bool = False
    
    @validator('tracking_id', pre=True, always=True)
    def set_tracking_id(cls, v):
        return v or str(uuid4())
    
    def get_rendered_content(self) -> tuple:
        """Get rendered email content"""
        if self.template:
            rendered_template = self.template.render(self.template_context)
            return (
                rendered_template.subject,
                rendered_template.html_content,
                rendered_template.text_content
            )
        return self.subject, self.html_content, self.text_content


class EmailResponse(BaseModel):
    """Email sending response model"""
    success: bool
    message_id: Optional[str] = None
    tracking_id: str
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime
    delivery_status: str = "sent"  # sent, scheduled, failed, queued


class BulkEmailRequest(BaseModel):
    """Bulk email request model"""
    recipients: List[EmailRecipient]
    template_name: str
    template_data: Dict[str, Any]
    from_email: EmailStr
    from_name: Optional[str] = None
    configuration_set: Optional[str] = None
    message_tags: Dict[str, str] = {}


class EmailAccountInfo(BaseModel):
    """SES account information model"""
    account_details: Dict[str, Any]
    sending_quota: Dict[str, Any]
    sending_statistics: Dict[str, Any] 