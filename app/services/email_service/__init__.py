"""
Email Service

A comprehensive, modular email service for AWS SES with advanced features:
- Immediate and scheduled email sending
- Template support with dynamic content
- Multiple recipients (TO, CC, BCC)
- File attachments support
- Job queue integration (Procrastinate)
- Email tracking and analytics
- Pre-configured helper functions for common use cases

Usage:
    from app.services.email_service import EmailService
    
    # Create email service
    email_service = EmailService()
    
    # Send simple email
    response = await email_service.send_simple_email(
        to_email="user@example.com",
        subject="Hello",
        html_content="<p>Hello World!</p>"
    )
    
    # Send welcome email
    response = await email_service.send_welcome_email(
        user_email="user@example.com",
        user_name="John Doe",
        verification_token="abc123"
    )
"""

from typing import List, Optional, Union
import procrastinate
from loguru import logger

from .models import (
    EmailRequest,
    EmailResponse, 
    EmailRecipient,
    EmailAttachment,
    EmailTemplate,
    EmailAccountInfo,
    BulkEmailRequest
)
from .client import SESClient, SESClientError, create_ses_client
from .sender import EmailSender, EmailSenderError
from .scheduler import EmailScheduler, create_email_scheduler
from .attachments import AttachmentHandler
from .helpers import (
    send_welcome_email,
    send_password_reset_email,
    send_notification_email,
    send_invoice_email,
    send_marketing_email
)


class EmailServiceError(Exception):
    """Custom exception for Email Service errors"""
    pass


class EmailService:
    """
    Main Email Service class that provides a unified interface
    for all email operations.
    """
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        procrastinate_app: Optional[procrastinate.App] = None,
        validate_aws_connection: bool = False
    ):
        """
        Initialize Email Service
        
        Args:
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
            procrastinate_app: Procrastinate app for scheduling
            validate_aws_connection: Whether to validate AWS connection during init
        """
        self.is_initialized = False
        self.initialization_error = None
        
        try:
            logger.debug("Initializing Email Service...")
            
            # Initialize components with error handling
            self.ses_client = self._create_ses_client(
                aws_access_key_id, 
                aws_secret_access_key, 
                validate_connection=validate_aws_connection
            )
            
            self.sender = EmailSender(self.ses_client)
            self.scheduler = create_email_scheduler(procrastinate_app)
            self.attachment_handler = AttachmentHandler()
            
            self.is_initialized = True
            logger.info("Email Service initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Email Service: {str(e)}"
            logger.error(error_msg)
            self.initialization_error = error_msg
            # Don't raise here - allow graceful degradation
    
    def _create_ses_client(
        self, 
        aws_access_key_id: Optional[str], 
        aws_secret_access_key: Optional[str],
        validate_connection: bool
    ) -> SESClient:
        """Create SES client with error handling"""
        try:
            return create_ses_client(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                validate_connection=validate_connection
            )
        except SESClientError as e:
            logger.warning(f"SES client initialization failed: {str(e)}")
            # Return client anyway for graceful degradation
            return create_ses_client(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                validate_connection=False
            )
    
    def _ensure_service_ready(self):
        """Ensure the service is ready for operations"""
        if not self.is_initialized:
            if self.initialization_error:
                raise EmailServiceError(f"Email service not properly initialized: {self.initialization_error}")
            else:
                raise EmailServiceError("Email service not initialized")
    
    def get_health_status(self) -> dict:
        """Get comprehensive health status of email service"""
        try:
            status = {
                "service_initialized": self.is_initialized,
                "initialization_error": self.initialization_error,
                "timestamp": "2024-01-01T00:00:00Z"  # Would be datetime.utcnow().isoformat()
            }
            
            # Get SES client health
            if hasattr(self, 'ses_client') and self.ses_client:
                status["ses_client"] = self.ses_client.get_health_status()
            else:
                status["ses_client"] = {"status": "not_initialized"}
            
            # Check sender status
            if hasattr(self, 'sender') and self.sender:
                status["sender"] = {"status": "ready"}
            else:
                status["sender"] = {"status": "not_initialized"}
            
            # Check scheduler status
            if hasattr(self, 'scheduler') and self.scheduler:
                status["scheduler"] = {
                    "status": "ready" if self.scheduler.procrastinate_app else "no_procrastinate_app"
                }
            else:
                status["scheduler"] = {"status": "not_initialized"}
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting health status: {str(e)}")
            return {"error": str(e), "status": "unhealthy"}
    
    # Core email sending methods with error handling
    async def send_email(self, email_request: EmailRequest) -> EmailResponse:
        """Send email using EmailRequest object"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Sending email with tracking ID: {email_request.tracking_id}")
            
            if not hasattr(self, 'sender') or not self.sender:
                raise EmailServiceError("Email sender not initialized")
            
            response = await self.sender.send_email(email_request)
            
            if response.success:
                logger.info(f"Email sent successfully: {response.tracking_id}")
            else:
                logger.error(f"Email sending failed: {response.tracking_id} - {response.error_message}")
            
            return response
            
        except EmailServiceError:
            raise
        except EmailSenderError as e:
            logger.error(f"Email sender error: {str(e)}")
            raise EmailServiceError(f"Email sending failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            raise EmailServiceError(f"Unexpected error sending email: {str(e)}") from e
    
    async def send_simple_email(
        self,
        to_email: str,
        subject: str,
        html_content: str = None,
        text_content: str = None,
        from_email: str = None,
        from_name: str = None,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None
    ) -> EmailResponse:
        """Send simple email with basic parameters"""
        try:
            logger.debug(f"Sending simple email to: {to_email}")
            
            from app.core.config import settings
            
            # Validate required parameters
            if not to_email:
                raise EmailServiceError("to_email is required")
            if not subject:
                raise EmailServiceError("subject is required")
            if not html_content and not text_content:
                raise EmailServiceError("Either html_content or text_content is required")
            
            # Convert string emails to EmailRecipient objects
            to_recipients = [EmailRecipient(email=to_email)]
            cc_recipients = [EmailRecipient(email=email) for email in (cc_emails or [])]
            bcc_recipients = [EmailRecipient(email=email) for email in (bcc_emails or [])]
            
            email_request = EmailRequest(
                to_recipients=to_recipients,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                from_email=from_email or settings.EMAIL_FROM_EMAIL,
                from_name=from_name or settings.EMAIL_FROM_NAME,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            return await self.send_email(email_request)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error in send_simple_email: {str(e)}")
            raise EmailServiceError(f"Failed to send simple email: {str(e)}") from e
    
    async def send_template_email(
        self,
        to_recipients: List[Union[str, EmailRecipient]],
        template_name: str,
        template_data: dict,
        from_email: str,
        **kwargs
    ) -> EmailResponse:
        """Send email using SES template"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Sending template email: {template_name}")
            
            if not to_recipients:
                raise EmailServiceError("to_recipients is required")
            if not template_name:
                raise EmailServiceError("template_name is required")
            if not from_email:
                raise EmailServiceError("from_email is required")
            
            return await self.sender.send_template_email(
                to_recipients=to_recipients,
                template_name=template_name,
                template_data=template_data,
                from_email=from_email,
                **kwargs
            )
            
        except EmailServiceError:
            raise
        except EmailSenderError as e:
            logger.error(f"Template email sender error: {str(e)}")
            raise EmailServiceError(f"Template email sending failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error sending template email: {str(e)}")
            raise EmailServiceError(f"Unexpected error sending template email: {str(e)}") from e
    
    async def send_bulk_emails(self, email_requests: List[EmailRequest]) -> List[EmailResponse]:
        """Send multiple emails in batch"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Sending bulk emails: {len(email_requests)} emails")
            
            if not email_requests:
                logger.warning("No email requests provided for bulk sending")
                return []
            
            responses = await self.sender.send_bulk_emails(email_requests)
            
            successful = len([r for r in responses if r.success])
            logger.info(f"Bulk email sending completed: {successful}/{len(responses)} successful")
            
            return responses
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error in bulk email sending: {str(e)}")
            raise EmailServiceError(f"Bulk email sending failed: {str(e)}") from e
    
    # Scheduling methods with error handling
    async def schedule_email(self, email_request: EmailRequest, send_time=None) -> EmailResponse:
        """Schedule email for later sending"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Scheduling email: {email_request.tracking_id}")
            
            if not hasattr(self, 'scheduler') or not self.scheduler:
                raise EmailServiceError("Email scheduler not initialized")
            
            if not self.scheduler.procrastinate_app:
                raise EmailServiceError("Procrastinate app not configured for scheduled emails")
            
            return await self.scheduler.schedule_email(email_request, send_time)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error scheduling email: {str(e)}")
            raise EmailServiceError(f"Email scheduling failed: {str(e)}") from e
    
    async def schedule_bulk_emails(self, email_requests: List[EmailRequest], send_time=None) -> List[EmailResponse]:
        """Schedule multiple emails for later sending"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Scheduling bulk emails: {len(email_requests)} emails")
            
            if not hasattr(self, 'scheduler') or not self.scheduler:
                raise EmailServiceError("Email scheduler not initialized")
            
            if not self.scheduler.procrastinate_app:
                raise EmailServiceError("Procrastinate app not configured for scheduled emails")
            
            return await self.scheduler.schedule_bulk_emails(email_requests, send_time)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error scheduling bulk emails: {str(e)}")
            raise EmailServiceError(f"Bulk email scheduling failed: {str(e)}") from e
    
    # Helper methods for common use cases with error handling
    async def send_welcome_email(self, user_email: str, user_name: str, verification_token: str) -> EmailResponse:
        """Send welcome email with verification link"""
        try:
            logger.debug(f"Sending welcome email to: {user_email}")
            
            if not user_email or not user_name or not verification_token:
                raise EmailServiceError("user_email, user_name, and verification_token are all required")
            
            return await send_welcome_email(user_email, user_name, verification_token, self.sender)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            raise EmailServiceError(f"Welcome email sending failed: {str(e)}") from e
    
    async def send_password_reset_email(self, user_email: str, user_name: str, reset_token: str) -> EmailResponse:
        """Send password reset email"""
        try:
            logger.debug(f"Sending password reset email to: {user_email}")
            
            if not user_email or not user_name or not reset_token:
                raise EmailServiceError("user_email, user_name, and reset_token are all required")
            
            return await send_password_reset_email(user_email, user_name, reset_token, self.sender)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            raise EmailServiceError(f"Password reset email sending failed: {str(e)}") from e
    
    async def send_notification_email(
        self, 
        user_email: str, 
        user_name: str, 
        subject: str, 
        message: str, 
        priority: str = "normal"
    ) -> EmailResponse:
        """Send notification email"""
        try:
            logger.debug(f"Sending notification email to: {user_email}")
            
            if not user_email or not user_name or not subject or not message:
                raise EmailServiceError("user_email, user_name, subject, and message are all required")
            
            if priority not in ["low", "normal", "high"]:
                raise EmailServiceError("priority must be one of: low, normal, high")
            
            return await send_notification_email(user_email, user_name, subject, message, priority, self.sender)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}")
            raise EmailServiceError(f"Notification email sending failed: {str(e)}") from e
    
    async def send_invoice_email(
        self,
        customer_email: str,
        customer_name: str,
        invoice_number: str,
        amount: str,
        due_date: str,
        pdf_content: bytes = None
    ) -> EmailResponse:
        """Send invoice email with optional PDF attachment"""
        try:
            logger.debug(f"Sending invoice email to: {customer_email}")
            
            if not all([customer_email, customer_name, invoice_number, amount, due_date]):
                raise EmailServiceError("customer_email, customer_name, invoice_number, amount, and due_date are all required")
            
            return await send_invoice_email(
                customer_email, customer_name, invoice_number, amount, due_date, pdf_content, self.sender
            )
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending invoice email: {str(e)}")
            raise EmailServiceError(f"Invoice email sending failed: {str(e)}") from e
    
    async def send_marketing_email(
        self,
        recipients: List[EmailRecipient],
        subject: str,
        html_content: str,
        text_content: str = None,
        campaign_id: str = None
    ) -> List[EmailResponse]:
        """Send marketing email to multiple recipients"""
        try:
            logger.debug(f"Sending marketing email to {len(recipients)} recipients")
            
            if not recipients:
                raise EmailServiceError("recipients list cannot be empty")
            if not subject:
                raise EmailServiceError("subject is required")
            if not html_content:
                raise EmailServiceError("html_content is required")
            
            return await send_marketing_email(recipients, subject, html_content, text_content, campaign_id, self.sender)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending marketing email: {str(e)}")
            raise EmailServiceError(f"Marketing email sending failed: {str(e)}") from e
    
    # Attachment methods with error handling
    def create_attachment_from_file(self, file_path: str, **kwargs) -> EmailAttachment:
        """Create attachment from file path"""
        try:
            logger.debug(f"Creating attachment from file: {file_path}")
            
            if not file_path:
                raise EmailServiceError("file_path is required")
            
            return self.attachment_handler.create_attachment_from_file(file_path, **kwargs)
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {file_path}")
            raise EmailServiceError(f"File not found: {file_path}") from e
        except Exception as e:
            logger.error(f"Error creating attachment from file: {str(e)}")
            raise EmailServiceError(f"Failed to create attachment from file: {str(e)}") from e
    
    def create_attachment_from_bytes(self, content: bytes, filename: str, **kwargs) -> EmailAttachment:
        """Create attachment from bytes"""
        try:
            logger.debug(f"Creating attachment from bytes: {filename}")
            
            if not content:
                raise EmailServiceError("content cannot be empty")
            if not filename:
                raise EmailServiceError("filename is required")
            
            return self.attachment_handler.create_attachment_from_bytes(content, filename, **kwargs)
            
        except Exception as e:
            logger.error(f"Error creating attachment from bytes: {str(e)}")
            raise EmailServiceError(f"Failed to create attachment from bytes: {str(e)}") from e
    
    def create_pdf_attachment(self, content: bytes, filename: str = "document.pdf") -> EmailAttachment:
        """Create PDF attachment"""
        try:
            logger.debug(f"Creating PDF attachment: {filename}")
            return self.attachment_handler.create_pdf_attachment(content, filename)
        except Exception as e:
            logger.error(f"Error creating PDF attachment: {str(e)}")
            raise EmailServiceError(f"Failed to create PDF attachment: {str(e)}") from e
    
    def create_excel_attachment(self, content: bytes, filename: str = "spreadsheet.xlsx") -> EmailAttachment:
        """Create Excel attachment"""
        try:
            logger.debug(f"Creating Excel attachment: {filename}")
            return self.attachment_handler.create_excel_attachment(content, filename)
        except Exception as e:
            logger.error(f"Error creating Excel attachment: {str(e)}")
            raise EmailServiceError(f"Failed to create Excel attachment: {str(e)}") from e
    
    def create_csv_attachment(self, content: Union[str, bytes], filename: str = "data.csv") -> EmailAttachment:
        """Create CSV attachment"""
        try:
            logger.debug(f"Creating CSV attachment: {filename}")
            return self.attachment_handler.create_csv_attachment(content, filename)
        except Exception as e:
            logger.error(f"Error creating CSV attachment: {str(e)}")
            raise EmailServiceError(f"Failed to create CSV attachment: {str(e)}") from e
    
    # Account and management methods with error handling
    async def get_account_info(self) -> EmailAccountInfo:
        """Get SES account information"""
        try:
            self._ensure_service_ready()
            logger.debug("Getting SES account information")
            
            if not hasattr(self, 'ses_client') or not self.ses_client:
                raise EmailServiceError("SES client not initialized")
            
            return await self.ses_client.get_account_info()
            
        except EmailServiceError:
            raise
        except SESClientError as e:
            logger.error(f"SES client error getting account info: {str(e)}")
            raise EmailServiceError(f"Failed to get account info: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {str(e)}")
            raise EmailServiceError(f"Unexpected error getting account info: {str(e)}") from e
    
    async def verify_domain(self, domain: str) -> bool:
        """Verify domain identity in SES"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Verifying domain: {domain}")
            
            if not domain:
                raise EmailServiceError("domain is required")
            
            if not hasattr(self, 'ses_client') or not self.ses_client:
                raise EmailServiceError("SES client not initialized")
            
            return await self.ses_client.verify_domain_identity(domain)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error verifying domain: {str(e)}")
            raise EmailServiceError(f"Domain verification failed: {str(e)}") from e
    
    async def create_configuration_set(self, name: str, **kwargs) -> bool:
        """Create SES configuration set"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Creating configuration set: {name}")
            
            if not name:
                raise EmailServiceError("configuration set name is required")
            
            if not hasattr(self, 'ses_client') or not self.ses_client:
                raise EmailServiceError("SES client not initialized")
            
            return await self.ses_client.create_configuration_set(name, **kwargs)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating configuration set: {str(e)}")
            raise EmailServiceError(f"Configuration set creation failed: {str(e)}") from e
    
    async def create_template(self, template_name: str, subject: str, **kwargs) -> bool:
        """Create SES email template"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Creating email template: {template_name}")
            
            if not template_name:
                raise EmailServiceError("template_name is required")
            if not subject:
                raise EmailServiceError("subject is required")
            
            if not hasattr(self, 'ses_client') or not self.ses_client:
                raise EmailServiceError("SES client not initialized")
            
            return await self.ses_client.create_template(template_name, subject, **kwargs)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            raise EmailServiceError(f"Template creation failed: {str(e)}") from e
    
    async def get_template(self, template_name: str):
        """Get SES email template"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Getting email template: {template_name}")
            
            if not template_name:
                raise EmailServiceError("template_name is required")
            
            if not hasattr(self, 'ses_client') or not self.ses_client:
                raise EmailServiceError("SES client not initialized")
            
            return await self.ses_client.get_template(template_name)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            raise EmailServiceError(f"Failed to get template: {str(e)}") from e
    
    async def delete_template(self, template_name: str) -> bool:
        """Delete SES email template"""
        try:
            self._ensure_service_ready()
            logger.debug(f"Deleting email template: {template_name}")
            
            if not template_name:
                raise EmailServiceError("template_name is required")
            
            if not hasattr(self, 'ses_client') or not self.ses_client:
                raise EmailServiceError("SES client not initialized")
            
            return await self.ses_client.delete_template(template_name)
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error deleting template: {str(e)}")
            raise EmailServiceError(f"Template deletion failed: {str(e)}") from e
    
    async def list_templates(self) -> List[str]:
        """List all SES email templates"""
        try:
            self._ensure_service_ready()
            logger.debug("Listing all email templates")
            
            if not hasattr(self, 'ses_client') or not self.ses_client:
                raise EmailServiceError("SES client not initialized")
            
            return await self.ses_client.list_templates()
            
        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error listing templates: {str(e)}")
            raise EmailServiceError(f"Failed to list templates: {str(e)}") from e


# Factory function for easy initialization
def create_email_service(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    procrastinate_app: Optional[procrastinate.App] = None,
    validate_aws_connection: bool = False
) -> EmailService:
    """
    Factory function to create configured EmailService
    
    Args:
        aws_access_key_id: AWS access key (optional)
        aws_secret_access_key: AWS secret key (optional)
        procrastinate_app: Procrastinate app for scheduling
        validate_aws_connection: Whether to validate AWS connection during creation
    
    Returns:
        Configured EmailService instance
    """
    try:
        logger.debug("Creating Email Service with factory function")
        
        service = EmailService(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            procrastinate_app=procrastinate_app,
            validate_aws_connection=validate_aws_connection
        )
        
        logger.debug("Email Service created successfully")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create Email Service: {str(e)}")
        # Return service anyway for graceful degradation
        return EmailService(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            procrastinate_app=procrastinate_app,
            validate_aws_connection=False
        )


# Export commonly used classes and functions
__all__ = [
    # Main service class
    'EmailService',
    'EmailServiceError',
    'create_email_service',
    
    # Models
    'EmailRequest',
    'EmailResponse',
    'EmailRecipient', 
    'EmailAttachment',
    'EmailTemplate',
    'EmailAccountInfo',
    'BulkEmailRequest',
    
    # Component classes
    'SESClient',
    'SESClientError',
    'EmailSender',
    'EmailScheduler',
    'AttachmentHandler',
    
    # Helper functions
    'send_welcome_email',
    'send_password_reset_email',
    'send_notification_email', 
    'send_invoice_email',
    'send_marketing_email',
    
    # Factory functions
    'create_ses_client',
    'create_email_scheduler'
] 