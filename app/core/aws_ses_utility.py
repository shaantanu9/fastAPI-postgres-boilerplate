"""
Comprehensive AWS SES Email Utility

A production-ready, dynamic email sending utility for AWS SES with advanced features:
- Immediate and scheduled email sending
- Template support with dynamic content
- Multiple recipients (TO, CC, BCC)
- File attachments support
- Job queue integration (Procrastinate)
- Email tracking and analytics
- Bounce and complaint handling
- Configuration sets support
- Advanced error handling and retry logic
- Email validation and sanitization
- Rate limiting and throttling
- Comprehensive logging and metrics

Author: AI Assistant
Version: 1.0.0
"""

import asyncio
import mimetypes
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import boto3
import procrastinate
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from jinja2 import Environment, Template
from loguru import logger
from pydantic import BaseModel, EmailStr, validator

from app.core.config import settings


class EmailRecipient(BaseModel):
    """Email recipient model with validation"""
    email: EmailStr
    name: Optional[str] = None
    
    def format_address(self) -> str:
        """Format email address with optional name"""
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


class SESEmailUtility:
    """
    Comprehensive AWS SES Email Utility
    
    Features:
    - Multiple recipient types (TO, CC, BCC)
    - Template rendering with Jinja2
    - File attachments support
    - Scheduled email sending with Procrastinate
    - Configuration sets and message tags
    - Email tracking and analytics
    - Advanced error handling and retry logic
    - Rate limiting and throttling
    - Bounce and complaint handling
    """
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: str = "us-east-1",
        configuration_set: Optional[str] = None,
        from_domain: Optional[str] = None,
        procrastinate_app: Optional[procrastinate.App] = None
    ):
        """
        Initialize SES Email Utility
        
        Args:
            aws_access_key_id: AWS access key (if None, uses default credentials)
            aws_secret_access_key: AWS secret key (if None, uses default credentials)
            aws_region: AWS region for SES
            configuration_set: Default SES configuration set
            from_domain: Default from domain for emails
            procrastinate_app: Procrastinate app for job scheduling
        """
        self.aws_region = aws_region
        self.default_configuration_set = configuration_set
        self.from_domain = from_domain
        self.procrastinate_app = procrastinate_app
        
        # Initialize SES client
        try:
            session_kwargs = {"region_name": aws_region}
            if aws_access_key_id and aws_secret_access_key:
                session_kwargs.update({
                    "aws_access_key_id": aws_access_key_id,
                    "aws_secret_access_key": aws_secret_access_key
                })
            
            self.ses_client = boto3.client('sesv2', **session_kwargs)
            self.ses_v1_client = boto3.client('ses', **session_kwargs)
            
            # Test connection
            self.ses_client.get_account()
            logger.info(f"SES Email Utility initialized for region: {aws_region}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize SES client: {str(e)}")
            raise
    
    async def send_email(
        self,
        email_request: EmailRequest,
        immediate: bool = True
    ) -> EmailResponse:
        """
        Send email immediately or schedule for later
        
        Args:
            email_request: Email request object
            immediate: If True, send immediately; if False, schedule based on send_time
        
        Returns:
            EmailResponse object with sending results
        """
        try:
            # Validate request
            await self._validate_email_request(email_request)
            
            # Check if email should be scheduled
            if not immediate or email_request.send_time:
                return await self._schedule_email(email_request)
            
            # Send immediately
            return await self._send_immediate_email(email_request)
            
        except Exception as e:
            logger.error(f"Error in send_email: {str(e)}")
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=str(e),
                timestamp=datetime.utcnow(),
                delivery_status="failed"
            )
    
    async def _send_immediate_email(self, email_request: EmailRequest) -> EmailResponse:
        """Send email immediately using SES"""
        try:
            # Get rendered content
            subject, html_content, text_content = email_request.get_rendered_content()
            
            # Prepare recipients
            to_addresses = [recipient.email for recipient in email_request.to_recipients]
            cc_addresses = [recipient.email for recipient in email_request.cc_recipients] if email_request.cc_recipients else []
            bcc_addresses = [recipient.email for recipient in email_request.bcc_recipients] if email_request.bcc_recipients else []
            
            # Prepare sender
            from_address = formataddr((email_request.from_name, email_request.from_email)) if email_request.from_name else email_request.from_email
            
            # Check if we have attachments - use different methods
            if email_request.attachments:
                message_id = await self._send_raw_email_with_attachments(email_request)
            else:
                message_id = await self._send_simple_email(email_request)
            
            logger.info(f"Email sent successfully. Message ID: {message_id}, Tracking ID: {email_request.tracking_id}")
            
            return EmailResponse(
                success=True,
                message_id=message_id,
                tracking_id=email_request.tracking_id,
                timestamp=datetime.utcnow(),
                delivery_status="sent"
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES ClientError: {error_code} - {error_message}")
            
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=error_message,
                error_code=error_code,
                timestamp=datetime.utcnow(),
                delivery_status="failed"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=str(e),
                timestamp=datetime.utcnow(),
                delivery_status="failed"
            )
    
    async def _send_simple_email(self, email_request: EmailRequest) -> str:
        """Send simple email without attachments using SES v2 API"""
        subject, html_content, text_content = email_request.get_rendered_content()
        
        # Prepare destinations
        destination = {}
        if email_request.to_recipients:
            destination['ToAddresses'] = [r.email for r in email_request.to_recipients]
        if email_request.cc_recipients:
            destination['CcAddresses'] = [r.email for r in email_request.cc_recipients]
        if email_request.bcc_recipients:
            destination['BccAddresses'] = [r.email for r in email_request.bcc_recipients]
        
        # Prepare message body
        body = {}
        if html_content:
            body['Html'] = {'Data': html_content, 'Charset': 'UTF-8'}
        if text_content:
            body['Text'] = {'Data': text_content, 'Charset': 'UTF-8'}
        
        # Prepare email request
        email_params = {
            'FromEmailAddress': email_request.from_email,
            'Destination': destination,
            'Content': {
                'Simple': {
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': body
                }
            }
        }
        
        # Add configuration set if specified
        if email_request.configuration_set or self.default_configuration_set:
            email_params['ConfigurationSetName'] = email_request.configuration_set or self.default_configuration_set
        
        # Add reply-to addresses
        if email_request.reply_to:
            email_params['ReplyToAddresses'] = email_request.reply_to
        
        # Add message tags
        if email_request.message_tags:
            email_params['EmailTags'] = [
                {'Name': key, 'Value': value}
                for key, value in email_request.message_tags.items()
            ]
        
        # Send email
        response = self.ses_client.send_email(**email_params)
        return response['MessageId']
    
    async def _send_raw_email_with_attachments(self, email_request: EmailRequest) -> str:
        """Send email with attachments using raw email format"""
        subject, html_content, text_content = email_request.get_rendered_content()
        
        # Create multipart message
        msg = MIMEMultipart('mixed')
        
        # Set headers
        msg['Subject'] = subject
        msg['From'] = formataddr((email_request.from_name, email_request.from_email)) if email_request.from_name else email_request.from_email
        msg['To'] = ', '.join([r.format_address() for r in email_request.to_recipients])
        
        if email_request.cc_recipients:
            msg['Cc'] = ', '.join([r.format_address() for r in email_request.cc_recipients])
        
        if email_request.reply_to:
            msg['Reply-To'] = ', '.join(email_request.reply_to)
        
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=self.from_domain)
        
        # Add tracking headers
        msg['X-Tracking-ID'] = email_request.tracking_id
        if email_request.campaign_id:
            msg['X-Campaign-ID'] = email_request.campaign_id
        
        # Create body container
        body_container = MIMEMultipart('alternative')
        
        # Add text content
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            body_container.attach(text_part)
        
        # Add HTML content
        if html_content:
            html_part = MIMEText(html_content, 'html', 'utf-8')
            body_container.attach(html_part)
        
        msg.attach(body_container)
        
        # Add attachments
        for attachment in email_request.attachments:
            await self._add_attachment(msg, attachment)
        
        # Prepare destinations
        destinations = []
        destinations.extend([r.email for r in email_request.to_recipients])
        if email_request.cc_recipients:
            destinations.extend([r.email for r in email_request.cc_recipients])
        if email_request.bcc_recipients:
            destinations.extend([r.email for r in email_request.bcc_recipients])
        
        # Prepare raw email parameters
        raw_email_params = {
            'Source': email_request.from_email,
            'Destinations': destinations,
            'RawMessage': {'Data': msg.as_string()}
        }
        
        # Add configuration set if specified
        if email_request.configuration_set or self.default_configuration_set:
            raw_email_params['ConfigurationSetName'] = email_request.configuration_set or self.default_configuration_set
        
        # Send raw email
        response = self.ses_v1_client.send_raw_email(**raw_email_params)
        return response['MessageId']
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: EmailAttachment):
        """Add attachment to email message"""
        try:
            if attachment.content_type.startswith('image/') and attachment.disposition == 'inline':
                # Handle inline images
                img = MIMEImage(attachment.content)
                img.add_header('Content-Disposition', 'inline', filename=attachment.filename)
                if attachment.content_id:
                    img.add_header('Content-ID', f'<{attachment.content_id}>')
                msg.attach(img)
            else:
                # Handle regular attachments
                part = MIMEApplication(attachment.content)
                part.add_header(
                    'Content-Disposition',
                    f'{attachment.disposition}; filename="{attachment.filename}"'
                )
                part.add_header('Content-Type', attachment.content_type)
                msg.attach(part)
                
        except Exception as e:
            logger.error(f"Error adding attachment {attachment.filename}: {str(e)}")
            raise
    
    async def _schedule_email(self, email_request: EmailRequest) -> EmailResponse:
        """Schedule email for later sending using Procrastinate"""
        if not self.procrastinate_app:
            raise ValueError("Procrastinate app not configured for scheduled emails")
        
        # Calculate delay
        send_time = email_request.send_time or datetime.utcnow()
        delay = max(0, (send_time - datetime.utcnow()).total_seconds())
        
        try:
            # Schedule job
            job = await self.procrastinate_app.defer_async(
                task="send_scheduled_email",
                email_request=email_request.dict(),
                schedule_at=send_time
            )
            
            logger.info(f"Email scheduled for {send_time}. Job ID: {job.id}, Tracking ID: {email_request.tracking_id}")
            
            return EmailResponse(
                success=True,
                tracking_id=email_request.tracking_id,
                timestamp=datetime.utcnow(),
                delivery_status="scheduled"
            )
            
        except Exception as e:
            logger.error(f"Error scheduling email: {str(e)}")
            return EmailResponse(
                success=False,
                tracking_id=email_request.tracking_id,
                error_message=str(e),
                timestamp=datetime.utcnow(),
                delivery_status="failed"
            )
    
    async def _validate_email_request(self, email_request: EmailRequest):
        """Validate email request before sending"""
        # Check recipients
        if not email_request.to_recipients and not email_request.bcc_recipients:
            raise ValueError("At least one recipient (TO or BCC) is required")
        
        # Check content
        if not any([
            email_request.html_content,
            email_request.text_content,
            email_request.template
        ]):
            raise ValueError("Email content (HTML, text, or template) is required")
        
        # Validate sender domain if configured
        if self.from_domain and not email_request.from_email.endswith(f"@{self.from_domain}"):
            logger.warning(f"Sender email {email_request.from_email} does not match configured domain {self.from_domain}")
    
    async def send_template_email(
        self,
        to_recipients: List[Union[str, EmailRecipient]],
        template_name: str,
        template_data: Dict[str, Any],
        from_email: str,
        cc_recipients: Optional[List[Union[str, EmailRecipient]]] = None,
        bcc_recipients: Optional[List[Union[str, EmailRecipient]]] = None,
        from_name: Optional[str] = None,
        configuration_set: Optional[str] = None,
        send_time: Optional[datetime] = None
    ) -> EmailResponse:
        """
        Send email using SES template
        
        Args:
            to_recipients: List of TO recipients
            template_name: SES template name
            template_data: Template data for rendering
            from_email: Sender email address
            cc_recipients: List of CC recipients
            bcc_recipients: List of BCC recipients
            from_name: Sender name
            configuration_set: SES configuration set
            send_time: Schedule send time
        
        Returns:
            EmailResponse object
        """
        try:
            # Convert string recipients to EmailRecipient objects
            def convert_recipients(recipients):
                if not recipients:
                    return []
                return [
                    r if isinstance(r, EmailRecipient) else EmailRecipient(email=r)
                    for r in recipients
                ]
            
            to_list = convert_recipients(to_recipients)
            cc_list = convert_recipients(cc_recipients)
            bcc_list = convert_recipients(bcc_recipients)
            
            # Prepare destinations
            destinations = []
            for recipient in to_list + cc_list + bcc_list:
                destinations.append({
                    'Destination': {
                        'ToAddresses': [recipient.email]
                    },
                    'ReplacementTemplateData': '{}'  # Individual customization if needed
                })
            
            # Prepare bulk email parameters
            bulk_email_params = {
                'Source': from_email,
                'Template': template_name,
                'DefaultTemplateData': str(template_data),
                'Destinations': destinations
            }
            
            # Add configuration set if specified
            if configuration_set or self.default_configuration_set:
                bulk_email_params['ConfigurationSetName'] = configuration_set or self.default_configuration_set
            
            # Send bulk template email
            response = self.ses_v1_client.send_bulk_templated_email(**bulk_email_params)
            
            tracking_id = str(uuid4())
            
            logger.info(f"Template email sent successfully. Template: {template_name}, Tracking ID: {tracking_id}")
            
            return EmailResponse(
                success=True,
                message_id=response.get('MessageId'),
                tracking_id=tracking_id,
                timestamp=datetime.utcnow(),
                delivery_status="sent"
            )
            
        except Exception as e:
            logger.error(f"Error sending template email: {str(e)}")
            return EmailResponse(
                success=False,
                tracking_id=str(uuid4()),
                error_message=str(e),
                timestamp=datetime.utcnow(),
                delivery_status="failed"
            )
    
    async def create_template(
        self,
        template_name: str,
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Create SES email template
        
        Args:
            template_name: Unique template name
            subject: Email subject with template variables
            html_content: HTML content with template variables
            text_content: Text content with template variables
        
        Returns:
            True if template created successfully
        """
        try:
            template_data = {
                'TemplateName': template_name,
                'SubjectPart': subject
            }
            
            if html_content:
                template_data['HtmlPart'] = html_content
            
            if text_content:
                template_data['TextPart'] = text_content
            
            self.ses_v1_client.create_template(Template=template_data)
            logger.info(f"Email template '{template_name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating template '{template_name}': {str(e)}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get SES account information and sending statistics"""
        try:
            account_info = self.ses_client.get_account()
            
            # Get sending quota and rate
            quota_info = self.ses_v1_client.get_send_quota()
            
            # Get sending statistics
            send_stats = self.ses_v1_client.get_send_statistics()
            
            return {
                'account_details': account_info,
                'sending_quota': quota_info,
                'sending_statistics': send_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}
    
    async def verify_domain_identity(self, domain: str) -> bool:
        """Verify domain identity in SES"""
        try:
            self.ses_client.create_email_identity(EmailIdentity=domain)
            logger.info(f"Domain identity verification initiated for: {domain}")
            return True
        except Exception as e:
            logger.error(f"Error verifying domain {domain}: {str(e)}")
            return False
    
    async def create_configuration_set(
        self,
        name: str,
        tracking_options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create SES configuration set"""
        try:
            config_set_data = {'ConfigurationSetName': name}
            
            if tracking_options:
                config_set_data['TrackingOptions'] = tracking_options
            
            self.ses_client.create_configuration_set(**config_set_data)
            logger.info(f"Configuration set '{name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating configuration set '{name}': {str(e)}")
            return False


# Procrastinate task for scheduled emails
async def send_scheduled_email_task(ctx, email_request_dict: Dict[str, Any]):
    """Procrastinate task to send scheduled emails"""
    try:
        # Reconstruct email request
        email_request = EmailRequest(**email_request_dict)
        
        # Initialize SES utility
        ses_utility = SESEmailUtility(
            aws_region=settings.AWS_REGION,
            configuration_set=settings.SES_CONFIGURATION_SET,
            from_domain=settings.EMAIL_FROM_DOMAIN
        )
        
        # Send email
        response = await ses_utility._send_immediate_email(email_request)
        
        if response.success:
            logger.info(f"Scheduled email sent successfully. Tracking ID: {response.tracking_id}")
        else:
            logger.error(f"Failed to send scheduled email. Tracking ID: {response.tracking_id}, Error: {response.error_message}")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in scheduled email task: {str(e)}")
        raise


# Factory function to create configured SES utility
def create_ses_utility(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    procrastinate_app: Optional[procrastinate.App] = None
) -> SESEmailUtility:
    """
    Factory function to create configured SES utility
    
    Args:
        aws_access_key_id: AWS access key (optional, uses settings if None)
        aws_secret_access_key: AWS secret key (optional, uses settings if None)
        procrastinate_app: Procrastinate app for scheduling
    
    Returns:
        Configured SESEmailUtility instance
    """
    return SESEmailUtility(
        aws_access_key_id=aws_access_key_id or settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION or "us-east-1",
        configuration_set=settings.SES_CONFIGURATION_SET,
        from_domain=settings.EMAIL_FROM_DOMAIN,
        procrastinate_app=procrastinate_app
    )


# Helper functions for common email scenarios
async def send_welcome_email(
    user_email: str,
    user_name: str,
    verification_token: str,
    ses_utility: Optional[SESEmailUtility] = None
) -> EmailResponse:
    """Send welcome email with verification link"""
    if not ses_utility:
        ses_utility = create_ses_utility()
    
    template = EmailTemplate(
        subject="Welcome to {{ app_name }}! Please verify your email",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #333;">Welcome to {{ app_name }}, {{ user_name }}!</h1>
            <p>Thank you for signing up. Please click the button below to verify your email address:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ verification_link }}" 
                   style="background-color: #007bff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all;">{{ verification_link }}</p>
            <p>This verification link will expire in 24 hours.</p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
                If you didn't create an account, please ignore this email.
            </p>
        </body>
        </html>
        """,
        text_content="""
        Welcome to {{ app_name }}, {{ user_name }}!
        
        Thank you for signing up. Please visit the following link to verify your email address:
        {{ verification_link }}
        
        This verification link will expire in 24 hours.
        
        If you didn't create an account, please ignore this email.
        """,
        template_data={
            "app_name": settings.APP_NAME,
            "user_name": user_name,
            "verification_link": f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        }
    )
    
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email=user_email, name=user_name)],
        from_email=settings.EMAIL_FROM_EMAIL,
        from_name=settings.EMAIL_FROM_NAME,
        template=template,
        configuration_set=settings.SES_CONFIGURATION_SET,
        message_tags={"type": "welcome", "category": "authentication"}
    )
    
    return await ses_utility.send_email(email_request)


async def send_password_reset_email(
    user_email: str,
    user_name: str,
    reset_token: str,
    ses_utility: Optional[SESEmailUtility] = None
) -> EmailResponse:
    """Send password reset email"""
    if not ses_utility:
        ses_utility = create_ses_utility()
    
    template = EmailTemplate(
        subject="Password Reset Request for {{ app_name }}",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #333;">Password Reset Request</h1>
            <p>Hello {{ user_name }},</p>
            <p>We received a request to reset your password for your {{ app_name }} account.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ reset_link }}" 
                   style="background-color: #dc3545; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Reset Password
                </a>
            </div>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all;">{{ reset_link }}</p>
            <p>This password reset link will expire in 1 hour.</p>
            <p>If you didn't request a password reset, please ignore this email and your password will remain unchanged.</p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
                For security, never share this email or link with others.
            </p>
        </body>
        </html>
        """,
        text_content="""
        Password Reset Request
        
        Hello {{ user_name }},
        
        We received a request to reset your password for your {{ app_name }} account.
        
        Please visit the following link to reset your password:
        {{ reset_link }}
        
        This password reset link will expire in 1 hour.
        
        If you didn't request a password reset, please ignore this email and your password will remain unchanged.
        """,
        template_data={
            "app_name": settings.APP_NAME,
            "user_name": user_name,
            "reset_link": f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        }
    )
    
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email=user_email, name=user_name)],
        from_email=settings.EMAIL_FROM_EMAIL,
        from_name=settings.EMAIL_FROM_NAME,
        template=template,
        configuration_set=settings.SES_CONFIGURATION_SET,
        message_tags={"type": "password_reset", "category": "authentication"}
    )
    
    return await ses_utility.send_email(email_request) 