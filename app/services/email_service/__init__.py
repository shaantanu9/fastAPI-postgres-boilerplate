"""Email Service.

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

from .attachments import AttachmentHandler
from .client import SESClient, SESClientError, create_ses_client
from .helpers import (
    send_invoice_email,
    send_marketing_email,
    send_notification_email,
    send_password_reset_email,
    send_welcome_email,
)
from .models import (
    BulkEmailRequest,
    EmailAccountInfo,
    EmailAttachment,
    EmailRecipient,
    EmailRequest,
    EmailResponse,
    EmailTemplate,
)
from .scheduler import EmailScheduler, create_email_scheduler
from .sender import EmailSender, EmailSenderError


class EmailServiceError(Exception):
    """Custom exception for Email Service errors."""



class EmailService:
    """Main Email Service class that provides a unified interface
    for all email operations.
    """

    def __init__(
        self,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        procrastinate_app: procrastinate.App | None = None,
        validate_aws_connection: bool = False,
    ) -> None:
        """Initialize Email Service.

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
                validate_connection=validate_aws_connection,
            )

            self.sender = EmailSender(self.ses_client)
            self.scheduler = create_email_scheduler(procrastinate_app)
            self.attachment_handler = AttachmentHandler()

            self.is_initialized = True
            logger.info("Email Service initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize Email Service: {e!s}"
            logger.error(error_msg)
            self.initialization_error = error_msg
            # Don't raise here - allow graceful degradation

    def _create_ses_client(
        self,
        aws_access_key_id: str | None,
        aws_secret_access_key: str | None,
        validate_connection: bool,
    ) -> SESClient:
        """Create SES client with error handling."""
        try:
            return create_ses_client(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                validate_connection=validate_connection,
            )
        except SESClientError as e:
            logger.warning(f"SES client initialization failed: {e!s}")
            # Return client anyway for graceful degradation
            return create_ses_client(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                validate_connection=False,
            )

    def _ensure_service_ready(self) -> None:
        """Ensure the service is ready for operations."""
        if not self.is_initialized:
            if self.initialization_error:
                msg = f"Email service not properly initialized: {self.initialization_error}"
                raise EmailServiceError(
                    msg,
                )
            msg = "Email service not initialized"
            raise EmailServiceError(msg)

    def get_health_status(self) -> dict:
        """Get comprehensive health status of email service."""
        try:
            status = {
                "service_initialized": self.is_initialized,
                "initialization_error": self.initialization_error,
                "timestamp": "2024-01-01T00:00:00Z",  # Would be datetime.utcnow().isoformat()
            }

            # Get SES client health
            if hasattr(self, "ses_client") and self.ses_client:
                status["ses_client"] = self.ses_client.get_health_status()
            else:
                status["ses_client"] = {"status": "not_initialized"}

            # Check sender status
            if hasattr(self, "sender") and self.sender:
                status["sender"] = {"status": "ready"}
            else:
                status["sender"] = {"status": "not_initialized"}

            # Check scheduler status
            if hasattr(self, "scheduler") and self.scheduler:
                status["scheduler"] = {
                    "status": "ready"
                    if self.scheduler.procrastinate_app
                    else "no_procrastinate_app",
                }
            else:
                status["scheduler"] = {"status": "not_initialized"}

            return status

        except Exception as e:
            logger.error(f"Error getting health status: {e!s}")
            return {"error": str(e), "status": "unhealthy"}

    # Core email sending methods with error handling
    async def send_email(self, email_request: EmailRequest) -> EmailResponse:
        """Send email using EmailRequest object."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Sending email with tracking ID: {email_request.tracking_id}")

            if not hasattr(self, "sender") or not self.sender:
                msg = "Email sender not initialized"
                raise EmailServiceError(msg)

            response = await self.sender.send_email(email_request)

            if response.success:
                logger.info(f"Email sent successfully: {response.tracking_id}")
            else:
                logger.error(
                    f"Email sending failed: {response.tracking_id} - {response.error_message}",
                )

            return response

        except EmailServiceError:
            raise
        except EmailSenderError as e:
            logger.error(f"Email sender error: {e!s}")
            msg = f"Email sending failed: {e!s}"
            raise EmailServiceError(msg) from e
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e!s}")
            msg = f"Unexpected error sending email: {e!s}"
            raise EmailServiceError(msg) from e

    async def send_simple_email(
        self,
        to_email: str,
        subject: str,
        html_content: str | None = None,
        text_content: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        cc_emails: list[str] | None = None,
        bcc_emails: list[str] | None = None,
    ) -> EmailResponse:
        """Send simple email with basic parameters."""
        try:
            logger.debug(f"Sending simple email to: {to_email}")

            from app.core.config import settings

            # Validate required parameters
            if not to_email:
                msg = "to_email is required"
                raise EmailServiceError(msg)
            if not subject:
                msg = "subject is required"
                raise EmailServiceError(msg)
            if not html_content and not text_content:
                msg = "Either html_content or text_content is required"
                raise EmailServiceError(
                    msg,
                )

            # Convert string emails to EmailRecipient objects
            to_recipients = [EmailRecipient(email=to_email)]
            cc_recipients = [EmailRecipient(email=email) for email in (cc_emails or [])]
            bcc_recipients = [
                EmailRecipient(email=email) for email in (bcc_emails or [])
            ]

            email_request = EmailRequest(
                to_recipients=to_recipients,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                from_email=from_email or settings.EMAIL_FROM_EMAIL,
                from_name=from_name or settings.EMAIL_FROM_NAME,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )

            return await self.send_email(email_request)

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error in send_simple_email: {e!s}")
            msg = f"Failed to send simple email: {e!s}"
            raise EmailServiceError(msg) from e

    async def send_template_email(
        self,
        to_recipients: list[str | EmailRecipient],
        template_name: str,
        template_data: dict,
        from_email: str,
        **kwargs,
    ) -> EmailResponse:
        """Send email using SES template."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Sending template email: {template_name}")

            if not to_recipients:
                msg = "to_recipients is required"
                raise EmailServiceError(msg)
            if not template_name:
                msg = "template_name is required"
                raise EmailServiceError(msg)
            if not from_email:
                msg = "from_email is required"
                raise EmailServiceError(msg)

            return await self.sender.send_template_email(
                to_recipients=to_recipients,
                template_name=template_name,
                template_data=template_data,
                from_email=from_email,
                **kwargs,
            )

        except EmailServiceError:
            raise
        except EmailSenderError as e:
            logger.error(f"Template email sender error: {e!s}")
            msg = f"Template email sending failed: {e!s}"
            raise EmailServiceError(msg) from e
        except Exception as e:
            logger.error(f"Unexpected error sending template email: {e!s}")
            msg = f"Unexpected error sending template email: {e!s}"
            raise EmailServiceError(
                msg,
            ) from e

    async def send_bulk_emails(
        self, email_requests: list[EmailRequest],
    ) -> list[EmailResponse]:
        """Send multiple emails in batch."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Sending bulk emails: {len(email_requests)} emails")

            if not email_requests:
                logger.warning("No email requests provided for bulk sending")
                return []

            responses = await self.sender.send_bulk_emails(email_requests)

            successful = len([r for r in responses if r.success])
            logger.info(
                f"Bulk email sending completed: {successful}/{len(responses)} successful",
            )

            return responses

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error in bulk email sending: {e!s}")
            msg = f"Bulk email sending failed: {e!s}"
            raise EmailServiceError(msg) from e

    # Scheduling methods with error handling
    async def schedule_email(
        self, email_request: EmailRequest, send_time=None,
    ) -> EmailResponse:
        """Schedule email for later sending."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Scheduling email: {email_request.tracking_id}")

            if not hasattr(self, "scheduler") or not self.scheduler:
                msg = "Email scheduler not initialized"
                raise EmailServiceError(msg)

            if not self.scheduler.procrastinate_app:
                msg = "Procrastinate app not configured for scheduled emails"
                raise EmailServiceError(
                    msg,
                )

            return await self.scheduler.schedule_email(email_request, send_time)

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error scheduling email: {e!s}")
            msg = f"Email scheduling failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def schedule_bulk_emails(
        self, email_requests: list[EmailRequest], send_time=None,
    ) -> list[EmailResponse]:
        """Schedule multiple emails for later sending."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Scheduling bulk emails: {len(email_requests)} emails")

            if not hasattr(self, "scheduler") or not self.scheduler:
                msg = "Email scheduler not initialized"
                raise EmailServiceError(msg)

            if not self.scheduler.procrastinate_app:
                msg = "Procrastinate app not configured for scheduled emails"
                raise EmailServiceError(
                    msg,
                )

            return await self.scheduler.schedule_bulk_emails(email_requests, send_time)

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error scheduling bulk emails: {e!s}")
            msg = f"Bulk email scheduling failed: {e!s}"
            raise EmailServiceError(msg) from e

    # Helper methods for common use cases with error handling
    async def send_welcome_email(
        self, user_email: str, user_name: str, verification_token: str,
    ) -> EmailResponse:
        """Send welcome email with verification link."""
        try:
            logger.debug(f"Sending welcome email to: {user_email}")

            if not user_email or not user_name or not verification_token:
                msg = "user_email, user_name, and verification_token are all required"
                raise EmailServiceError(
                    msg,
                )

            return await send_welcome_email(
                user_email, user_name, verification_token, self.sender,
            )

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending welcome email: {e!s}")
            msg = f"Welcome email sending failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def send_password_reset_email(
        self, user_email: str, user_name: str, reset_token: str,
    ) -> EmailResponse:
        """Send password reset email."""
        try:
            logger.debug(f"Sending password reset email to: {user_email}")

            if not user_email or not user_name or not reset_token:
                msg = "user_email, user_name, and reset_token are all required"
                raise EmailServiceError(
                    msg,
                )

            return await send_password_reset_email(
                user_email, user_name, reset_token, self.sender,
            )

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending password reset email: {e!s}")
            msg = f"Password reset email sending failed: {e!s}"
            raise EmailServiceError(
                msg,
            ) from e

    async def send_notification_email(
        self,
        user_email: str,
        user_name: str,
        subject: str,
        message: str,
        priority: str = "normal",
    ) -> EmailResponse:
        """Send notification email."""
        try:
            logger.debug(f"Sending notification email to: {user_email}")

            if not user_email or not user_name or not subject or not message:
                msg = "user_email, user_name, subject, and message are all required"
                raise EmailServiceError(
                    msg,
                )

            if priority not in ["low", "normal", "high"]:
                msg = "priority must be one of: low, normal, high"
                raise EmailServiceError(msg)

            return await send_notification_email(
                user_email, user_name, subject, message, priority, self.sender,
            )

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending notification email: {e!s}")
            msg = f"Notification email sending failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def send_invoice_email(
        self,
        customer_email: str,
        customer_name: str,
        invoice_number: str,
        amount: str,
        due_date: str,
        pdf_content: bytes | None = None,
    ) -> EmailResponse:
        """Send invoice email with optional PDF attachment."""
        try:
            logger.debug(f"Sending invoice email to: {customer_email}")

            if not all(
                [customer_email, customer_name, invoice_number, amount, due_date],
            ):
                msg = "customer_email, customer_name, invoice_number, amount, and due_date are all required"
                raise EmailServiceError(
                    msg,
                )

            return await send_invoice_email(
                customer_email,
                customer_name,
                invoice_number,
                amount,
                due_date,
                pdf_content,
                self.sender,
            )

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending invoice email: {e!s}")
            msg = f"Invoice email sending failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def send_marketing_email(
        self,
        recipients: list[EmailRecipient],
        subject: str,
        html_content: str,
        text_content: str | None = None,
        campaign_id: str | None = None,
    ) -> list[EmailResponse]:
        """Send marketing email to multiple recipients."""
        try:
            logger.debug(f"Sending marketing email to {len(recipients)} recipients")

            if not recipients:
                msg = "recipients list cannot be empty"
                raise EmailServiceError(msg)
            if not subject:
                msg = "subject is required"
                raise EmailServiceError(msg)
            if not html_content:
                msg = "html_content is required"
                raise EmailServiceError(msg)

            return await send_marketing_email(
                recipients,
                subject,
                html_content,
                text_content,
                campaign_id,
                self.sender,
            )

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending marketing email: {e!s}")
            msg = f"Marketing email sending failed: {e!s}"
            raise EmailServiceError(msg) from e

    # Attachment methods with error handling
    def create_attachment_from_file(self, file_path: str, **kwargs) -> EmailAttachment:
        """Create attachment from file path."""
        try:
            logger.debug(f"Creating attachment from file: {file_path}")

            if not file_path:
                msg = "file_path is required"
                raise EmailServiceError(msg)

            return self.attachment_handler.create_attachment_from_file(
                file_path, **kwargs,
            )

        except FileNotFoundError as e:
            logger.error(f"File not found: {file_path}")
            msg = f"File not found: {file_path}"
            raise EmailServiceError(msg) from e
        except Exception as e:
            logger.error(f"Error creating attachment from file: {e!s}")
            msg = f"Failed to create attachment from file: {e!s}"
            raise EmailServiceError(
                msg,
            ) from e

    def create_attachment_from_bytes(
        self, content: bytes, filename: str, **kwargs,
    ) -> EmailAttachment:
        """Create attachment from bytes."""
        try:
            logger.debug(f"Creating attachment from bytes: {filename}")

            if not content:
                msg = "content cannot be empty"
                raise EmailServiceError(msg)
            if not filename:
                msg = "filename is required"
                raise EmailServiceError(msg)

            return self.attachment_handler.create_attachment_from_bytes(
                content, filename, **kwargs,
            )

        except Exception as e:
            logger.error(f"Error creating attachment from bytes: {e!s}")
            msg = f"Failed to create attachment from bytes: {e!s}"
            raise EmailServiceError(
                msg,
            ) from e

    def create_pdf_attachment(
        self, content: bytes, filename: str = "document.pdf",
    ) -> EmailAttachment:
        """Create PDF attachment."""
        try:
            logger.debug(f"Creating PDF attachment: {filename}")
            return self.attachment_handler.create_pdf_attachment(content, filename)
        except Exception as e:
            logger.error(f"Error creating PDF attachment: {e!s}")
            msg = f"Failed to create PDF attachment: {e!s}"
            raise EmailServiceError(msg) from e

    def create_excel_attachment(
        self, content: bytes, filename: str = "spreadsheet.xlsx",
    ) -> EmailAttachment:
        """Create Excel attachment."""
        try:
            logger.debug(f"Creating Excel attachment: {filename}")
            return self.attachment_handler.create_excel_attachment(content, filename)
        except Exception as e:
            logger.error(f"Error creating Excel attachment: {e!s}")
            msg = f"Failed to create Excel attachment: {e!s}"
            raise EmailServiceError(msg) from e

    def create_csv_attachment(
        self, content: str | bytes, filename: str = "data.csv",
    ) -> EmailAttachment:
        """Create CSV attachment."""
        try:
            logger.debug(f"Creating CSV attachment: {filename}")
            return self.attachment_handler.create_csv_attachment(content, filename)
        except Exception as e:
            logger.error(f"Error creating CSV attachment: {e!s}")
            msg = f"Failed to create CSV attachment: {e!s}"
            raise EmailServiceError(msg) from e

    # Account and management methods with error handling
    async def get_account_info(self) -> EmailAccountInfo:
        """Get SES account information."""
        try:
            self._ensure_service_ready()
            logger.debug("Getting SES account information")

            if not hasattr(self, "ses_client") or not self.ses_client:
                msg = "SES client not initialized"
                raise EmailServiceError(msg)

            return await self.ses_client.get_account_info()

        except EmailServiceError:
            raise
        except SESClientError as e:
            logger.error(f"SES client error getting account info: {e!s}")
            msg = f"Failed to get account info: {e!s}"
            raise EmailServiceError(msg) from e
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {e!s}")
            msg = f"Unexpected error getting account info: {e!s}"
            raise EmailServiceError(
                msg,
            ) from e

    async def verify_domain(self, domain: str) -> bool:
        """Verify domain identity in SES."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Verifying domain: {domain}")

            if not domain:
                msg = "domain is required"
                raise EmailServiceError(msg)

            if not hasattr(self, "ses_client") or not self.ses_client:
                msg = "SES client not initialized"
                raise EmailServiceError(msg)

            return await self.ses_client.verify_domain_identity(domain)

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error verifying domain: {e!s}")
            msg = f"Domain verification failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def create_configuration_set(self, name: str, **kwargs) -> bool:
        """Create SES configuration set."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Creating configuration set: {name}")

            if not name:
                msg = "configuration set name is required"
                raise EmailServiceError(msg)

            if not hasattr(self, "ses_client") or not self.ses_client:
                msg = "SES client not initialized"
                raise EmailServiceError(msg)

            return await self.ses_client.create_configuration_set(name, **kwargs)

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating configuration set: {e!s}")
            msg = f"Configuration set creation failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def create_template(self, template_name: str, subject: str, **kwargs) -> bool:
        """Create SES email template."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Creating email template: {template_name}")

            if not template_name:
                msg = "template_name is required"
                raise EmailServiceError(msg)
            if not subject:
                msg = "subject is required"
                raise EmailServiceError(msg)

            if not hasattr(self, "ses_client") or not self.ses_client:
                msg = "SES client not initialized"
                raise EmailServiceError(msg)

            return await self.ses_client.create_template(
                template_name, subject, **kwargs,
            )

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating template: {e!s}")
            msg = f"Template creation failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def get_template(self, template_name: str):
        """Get SES email template."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Getting email template: {template_name}")

            if not template_name:
                msg = "template_name is required"
                raise EmailServiceError(msg)

            if not hasattr(self, "ses_client") or not self.ses_client:
                msg = "SES client not initialized"
                raise EmailServiceError(msg)

            return await self.ses_client.get_template(template_name)

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting template: {e!s}")
            msg = f"Failed to get template: {e!s}"
            raise EmailServiceError(msg) from e

    async def delete_template(self, template_name: str) -> bool:
        """Delete SES email template."""
        try:
            self._ensure_service_ready()
            logger.debug(f"Deleting email template: {template_name}")

            if not template_name:
                msg = "template_name is required"
                raise EmailServiceError(msg)

            if not hasattr(self, "ses_client") or not self.ses_client:
                msg = "SES client not initialized"
                raise EmailServiceError(msg)

            return await self.ses_client.delete_template(template_name)

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error deleting template: {e!s}")
            msg = f"Template deletion failed: {e!s}"
            raise EmailServiceError(msg) from e

    async def list_templates(self) -> list[str]:
        """List all SES email templates."""
        try:
            self._ensure_service_ready()
            logger.debug("Listing all email templates")

            if not hasattr(self, "ses_client") or not self.ses_client:
                msg = "SES client not initialized"
                raise EmailServiceError(msg)

            return await self.ses_client.list_templates()

        except EmailServiceError:
            raise
        except Exception as e:
            logger.error(f"Error listing templates: {e!s}")
            msg = f"Failed to list templates: {e!s}"
            raise EmailServiceError(msg) from e


# Factory function for easy initialization
def create_email_service(
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    procrastinate_app: procrastinate.App | None = None,
    validate_aws_connection: bool = False,
) -> EmailService:
    """Factory function to create configured EmailService.

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
            validate_aws_connection=validate_aws_connection,
        )

        logger.debug("Email Service created successfully")
        return service

    except Exception as e:
        logger.error(f"Failed to create Email Service: {e!s}")
        # Return service anyway for graceful degradation
        return EmailService(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            procrastinate_app=procrastinate_app,
            validate_aws_connection=False,
        )


# Export commonly used classes and functions
__all__ = [
    "AttachmentHandler",
    "BulkEmailRequest",
    "EmailAccountInfo",
    "EmailAttachment",
    "EmailRecipient",
    # Models
    "EmailRequest",
    "EmailResponse",
    "EmailScheduler",
    "EmailSender",
    # Main service class
    "EmailService",
    "EmailServiceError",
    "EmailTemplate",
    # Component classes
    "SESClient",
    "SESClientError",
    "create_email_scheduler",
    "create_email_service",
    # Factory functions
    "create_ses_client",
    "send_invoice_email",
    "send_marketing_email",
    "send_notification_email",
    "send_password_reset_email",
    # Helper functions
    "send_welcome_email",
]
