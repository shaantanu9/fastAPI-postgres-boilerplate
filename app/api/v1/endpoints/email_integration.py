"""Email Service API Endpoints.

FastAPI endpoints for email operations using the modular email service.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel, EmailStr

from app.services.email_service import (
    EmailRecipient,
    EmailRequest,
    EmailService,
    EmailServiceError,
    create_email_service,
)

router = APIRouter()

# Global email service instance - created without validation to prevent startup crashes
try:
    email_service = create_email_service(validate_aws_connection=False)
    logger.info("Email service initialized successfully for API endpoints")
except Exception as e:
    logger.warning(
        f"Email service initialization failed, will retry on first use: {e!s}",
    )
    email_service = None


# API Models
class SendEmailRequest(BaseModel):
    """API model for sending emails via the email service endpoints.

    Attributes:
        to_emails (List[str]): List of recipient email addresses.
        cc_emails (Optional[List[str]]): List of CC email addresses.
        bcc_emails (Optional[List[str]]): List of BCC email addresses.
        subject (str): Subject of the email.
        html_content (Optional[str]): HTML content of the email.
        text_content (Optional[str]): Plain text content of the email.
        from_name (Optional[str]): Sender's display name.
        reply_to (Optional[List[str]]): List of reply-to email addresses.
        message_tags (Dict[str, str]): Custom tags for tracking/campaigns.
        campaign_id (Optional[str]): Campaign identifier.
        priority (str): Priority for sending the email.

    """

    to_emails: list[str]
    cc_emails: list[str] | None = []
    bcc_emails: list[str] | None = []
    subject: str
    html_content: str | None = None
    text_content: str | None = None
    from_name: str | None = None
    reply_to: list[str] | None = []
    message_tags: dict[str, str] = {}
    campaign_id: str | None = None
    priority: str = "normal"


class SendTemplateEmailRequest(BaseModel):
    """API model for sending template-based emails.

    Attributes:
        to_emails (List[str]): List of recipient email addresses.
        cc_emails (Optional[List[str]]): List of CC email addresses.
        subject (str): Subject of the email.
        template_data (Dict[str, str]): Data for populating the email template.
        from_name (Optional[str]): Sender's display name.
        message_tags (Dict[str, str]): Custom tags for tracking/campaigns.

    """

    to_emails: list[str]
    cc_emails: list[str] | None = []
    subject: str
    template_data: dict[str, str]
    from_name: str | None = None
    message_tags: dict[str, str] = {}


class ScheduleEmailRequest(BaseModel):
    """API model for scheduling emails to be sent at a specific time.

    Attributes:
        to_emails (List[str]): List of recipient email addresses.
        subject (str): Subject of the email.
        html_content (Optional[str]): HTML content of the email.
        text_content (Optional[str]): Plain text content of the email.
        send_time (datetime): Scheduled time for sending the email.
        from_name (Optional[str]): Sender's display name.
        message_tags (Dict[str, str]): Custom tags for tracking/campaigns.

    """

    to_emails: list[str]
    subject: str
    html_content: str | None = None
    text_content: str | None = None
    send_time: datetime
    from_name: str | None = None
    message_tags: dict[str, str] = {}


class WelcomeEmailRequest(BaseModel):
    """API model for sending welcome emails to new users.

    Attributes:
        user_email (EmailStr): Recipient's email address.
        user_name (str): Recipient's name.
        verification_token (str): Token for email verification link.

    """

    user_email: EmailStr
    user_name: str
    verification_token: str


class PasswordResetRequest(BaseModel):
    """API model for sending password reset emails.

    Attributes:
        user_email (EmailStr): Recipient's email address.
        user_name (str): Recipient's name.
        reset_token (str): Token for password reset link.

    """

    user_email: EmailStr
    user_name: str
    reset_token: str


class EmailStatusResponse(BaseModel):
    """API response model for email operations.

    Attributes:
        success (bool): Whether the operation was successful.
        tracking_id (str): Unique tracking ID for the email operation.
        message_id (Optional[str]): ID returned by the email provider (e.g., SES).
        delivery_status (str): Status of the email delivery.
        error_message (Optional[str]): Error message if the operation failed.
        timestamp (datetime): Time of the operation.

    """

    success: bool
    tracking_id: str
    message_id: str | None = None
    delivery_status: str
    error_message: str | None = None
    timestamp: datetime


def get_email_service() -> EmailService:
    """Retrieve a global email service instance, initializing it if necessary.

    Returns:
        EmailService: The global email service instance.

    Raises:
        HTTPException: If the email service cannot be initialized.

    """
    global email_service

    if email_service is None:
        try:
            logger.debug("Creating new email service instance...")
            email_service = create_email_service(validate_aws_connection=False)
            logger.info("Email service created successfully")
        except Exception as e:
            logger.error(f"Failed to create email service: {e!s}")
            raise HTTPException(
                status_code=503, detail=f"Email service unavailable: {e!s}",
            )

    return email_service


def handle_email_service_error(e: Exception, operation: str) -> HTTPException:
    """Handle email service errors and convert them to appropriate HTTP exceptions.

    Args:
        e (Exception): The exception raised during the email operation.
        operation (str): The name of the email operation being performed.

    Returns:
        HTTPException: Mapped HTTP exception for FastAPI error handling.

    """
    if isinstance(e, EmailServiceError):
        logger.error(f"Email service error in {operation}: {e!s}")
        return HTTPException(status_code=400, detail=f"Email service error: {e!s}")
    if "credentials" in str(e).lower():
        logger.error(f"AWS credentials error in {operation}: {e!s}")
        return HTTPException(
            status_code=503,
            detail="AWS credentials not configured. Please configure AWS credentials to use email functionality.",
        )
    if "not found" in str(e).lower():
        logger.error(f"Resource not found error in {operation}: {e!s}")
        return HTTPException(status_code=404, detail=str(e))
    logger.error(f"Unexpected error in {operation}: {e!s}")
    return HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


@router.get("/health")
async def get_email_service_health():
    """Get health status of the email service and its components.

    Returns:
        dict: Health status, details, and timestamp.

    """
    try:
        service = get_email_service()
        health_status = service.get_health_status()

        # Determine overall health
        overall_health = "healthy"
        if not health_status.get("service_initialized", False):
            overall_health = "unhealthy"
        elif health_status.get("ses_client", {}).get("connection") == "unhealthy":
            overall_health = "degraded"

        return {
            "status": overall_health,
            "details": health_status,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting health status: {e!s}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/send", response_model=EmailStatusResponse)
async def send_email(request: SendEmailRequest, background_tasks: BackgroundTasks):
    """Send an email immediately to multiple recipients with support for CC, BCC, custom tags, and priority.

    Args:
        request (SendEmailRequest): The email sending request payload.
        background_tasks (BackgroundTasks): FastAPI background tasks handler.

    Returns:
        EmailStatusResponse: Status and metadata of the email operation.

    Raises:
        HTTPException: On email sending error or service failure.

    """
    try:
        logger.debug(
            f"API request to send email to {len(request.to_emails)} recipients",
        )

        service = get_email_service()

        # Validate request
        if not request.to_emails:
            raise HTTPException(status_code=400, detail="to_emails cannot be empty")
        if not request.subject:
            raise HTTPException(status_code=400, detail="subject is required")
        if not request.html_content and not request.text_content:
            raise HTTPException(
                status_code=400,
                detail="Either html_content or text_content is required",
            )

        # Convert to EmailRecipient objects
        to_recipients = [EmailRecipient(email=email) for email in request.to_emails]
        cc_recipients = [EmailRecipient(email=email) for email in request.cc_emails]
        bcc_recipients = [EmailRecipient(email=email) for email in request.bcc_emails]

        # Create email request
        from app.core.config import settings

        email_request = EmailRequest(
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            from_email=settings.EMAIL_FROM_EMAIL,
            from_name=request.from_name or settings.EMAIL_FROM_NAME,
            subject=request.subject,
            html_content=request.html_content,
            text_content=request.text_content,
            reply_to=request.reply_to,
            message_tags=request.message_tags,
            campaign_id=request.campaign_id,
            priority=request.priority,
        )

        # Send email
        response = await service.send_email(email_request)

        logger.info(
            f"Email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "send_email")


@router.post("/send-simple")
async def send_simple_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
    cc_emails: str | None = None,  # Comma-separated
    bcc_emails: str | None = None,  # Comma-separated
):
    """Send a simple email with basic parameters and minimal configuration.

    Args:
        to_email (str): Recipient email address.
        subject (str): Subject of the email.
        html_content (str): HTML content of the email.
        text_content (str, optional): Plain text content of the email.
        cc_emails (str, optional): Comma-separated CC emails.
        bcc_emails (str, optional): Comma-separated BCC emails.

    Returns:
        EmailStatusResponse: Status and metadata of the email operation.

    Raises:
        HTTPException: On email sending error or service failure.

    """
    try:
        logger.debug(f"API request to send simple email to: {to_email}")

        service = get_email_service()

        # Validate required parameters
        if not to_email:
            raise HTTPException(status_code=400, detail="to_email is required")
        if not subject:
            raise HTTPException(status_code=400, detail="subject is required")
        if not html_content and not text_content:
            raise HTTPException(
                status_code=400,
                detail="Either html_content or text_content is required",
            )

        # Parse comma-separated emails
        cc_list = [email.strip() for email in cc_emails.split(",")] if cc_emails else []
        bcc_list = (
            [email.strip() for email in bcc_emails.split(",")] if bcc_emails else []
        )

        response = await service.send_simple_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            cc_emails=cc_list,
            bcc_emails=bcc_list,
        )

        logger.info(
            f"Simple email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "send_simple_email")


@router.post("/send-template", response_model=EmailStatusResponse)
async def send_template_email(request: SendTemplateEmailRequest):
    """Send an email using a pre-created SES template and dynamic template data.

    Args:
        request (SendTemplateEmailRequest): The template email sending request payload.

    Returns:
        EmailStatusResponse: Status and metadata of the email operation.

    Raises:
        HTTPException: On template sending error or service failure.

    """
    try:
        logger.debug(
            f"API request to send template email to {len(request.to_emails)} recipients",
        )

        service = get_email_service()

        # Validate request
        if not request.to_emails:
            raise HTTPException(status_code=400, detail="to_emails cannot be empty")
        if not request.subject:
            raise HTTPException(status_code=400, detail="subject is required")

        # Convert string emails to EmailRecipient objects
        to_recipients = [EmailRecipient(email=email) for email in request.to_emails]
        cc_recipients = [EmailRecipient(email=email) for email in request.cc_emails]

        # Note: This requires a template name to be configured
        template_name = "default-template"  # This should be configurable

        from app.core.config import settings

        # Send template email
        response = await service.send_template_email(
            to_recipients=to_recipients,
            template_name=template_name,
            template_data=request.template_data,
            from_email=settings.EMAIL_FROM_EMAIL,
            cc_recipients=cc_recipients,
            from_name=request.from_name or settings.EMAIL_FROM_NAME,
        )

        logger.info(
            f"Template email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "send_template_email")


@router.post("/schedule", response_model=EmailStatusResponse)
async def schedule_email(request: ScheduleEmailRequest):
    """Schedule an email for later delivery using the job queue.

    Args:
        request (ScheduleEmailRequest): The scheduling request payload.

    Returns:
        EmailStatusResponse: Status and metadata of the scheduled email operation.

    Raises:
        HTTPException: On scheduling error or service failure.

    """
    try:
        logger.debug(f"API request to schedule email for {request.send_time}")

        service = get_email_service()

        # Validate request
        if not request.to_emails:
            raise HTTPException(status_code=400, detail="to_emails cannot be empty")
        if not request.subject:
            raise HTTPException(status_code=400, detail="subject is required")
        if not request.html_content and not request.text_content:
            raise HTTPException(
                status_code=400,
                detail="Either html_content or text_content is required",
            )

        # Convert to EmailRecipient objects
        to_recipients = [EmailRecipient(email=email) for email in request.to_emails]

        # Create email request
        from app.core.config import settings

        email_request = EmailRequest(
            to_recipients=to_recipients,
            from_email=settings.EMAIL_FROM_EMAIL,
            from_name=request.from_name or settings.EMAIL_FROM_NAME,
            subject=request.subject,
            html_content=request.html_content,
            text_content=request.text_content,
            send_time=request.send_time,
            message_tags=request.message_tags,
        )

        # Schedule email
        response = await service.schedule_email(email_request)

        logger.info(
            f"Schedule email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "schedule_email")


@router.post("/send-with-attachments", response_model=EmailStatusResponse)
async def send_email_with_attachments(
    to_emails: str,  # Comma-separated emails
    subject: str,
    html_content: str,
    files: Annotated[list[UploadFile], File()] = ...,
):
    """Send an email with file attachments, supporting multiple file types and MIME detection.

    Args:
        to_emails (str): Comma-separated recipient email addresses.
        subject (str): Subject of the email.
        html_content (str): HTML content of the email.
        files (List[UploadFile]): List of files to attach.

    Returns:
        EmailStatusResponse: Status and metadata of the email operation.

    Raises:
        HTTPException: On attachment or sending failure.

    """
    try:
        logger.debug(f"API request to send email with {len(files)} attachments")

        service = get_email_service()

        # Validate request
        if not to_emails:
            raise HTTPException(status_code=400, detail="to_emails is required")
        if not subject:
            raise HTTPException(status_code=400, detail="subject is required")
        if not html_content:
            raise HTTPException(status_code=400, detail="html_content is required")
        if not files:
            raise HTTPException(status_code=400, detail="At least one file is required")

        # Parse email addresses
        to_list = [email.strip() for email in to_emails.split(",")]
        if not to_list or not to_list[0]:
            raise HTTPException(
                status_code=400, detail="Valid email addresses required",
            )

        to_recipients = [EmailRecipient(email=email) for email in to_list]

        # Process attachments
        attachments = []
        for file in files:
            try:
                content = await file.read()
                if not content:
                    logger.warning(f"Empty file uploaded: {file.filename}")
                    continue

                attachment = service.create_attachment_from_bytes(
                    content=content,
                    filename=file.filename or "unknown_file",
                    content_type=file.content_type,
                )
                attachments.append(attachment)
                logger.debug(
                    f"Processed attachment: {file.filename} ({len(content)} bytes)",
                )

            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {e!s}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Error processing file {file.filename}: {e!s}",
                )

        if not attachments:
            raise HTTPException(status_code=400, detail="No valid attachments found")

        # Create email request with attachments
        from app.core.config import settings

        email_request = EmailRequest(
            to_recipients=to_recipients,
            from_email=settings.EMAIL_FROM_EMAIL,
            from_name=settings.EMAIL_FROM_NAME,
            subject=subject,
            html_content=html_content,
            attachments=attachments,
        )

        # Send email with attachments
        response = await service.send_email(email_request)

        logger.info(
            f"Attachment email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "send_email_with_attachments")


@router.post("/welcome", response_model=EmailStatusResponse)
async def send_welcome_email_api(request: WelcomeEmailRequest):
    """Send a welcome email with a verification link using a pre-configured template.

    Args:
        request (WelcomeEmailRequest): The welcome email request payload.

    Returns:
        EmailStatusResponse: Status and metadata of the welcome email operation.

    Raises:
        HTTPException: On sending error or template failure.

    """
    try:
        logger.debug(f"API request to send welcome email to: {request.user_email}")

        service = get_email_service()

        response = await service.send_welcome_email(
            user_email=request.user_email,
            user_name=request.user_name,
            verification_token=request.verification_token,
        )

        logger.info(
            f"Welcome email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "send_welcome_email")


@router.post("/password-reset", response_model=EmailStatusResponse)
async def send_password_reset_api(request: PasswordResetRequest):
    """Send a password reset email using a pre-configured template with a secure reset link.

    Args:
        request (PasswordResetRequest): The password reset email request payload.

    Returns:
        EmailStatusResponse: Status and metadata of the password reset email operation.

    Raises:
        HTTPException: On sending error or template failure.

    """
    try:
        logger.debug(
            f"API request to send password reset email to: {request.user_email}",
        )

        service = get_email_service()

        response = await service.send_password_reset_email(
            user_email=request.user_email,
            user_name=request.user_name,
            reset_token=request.reset_token,
        )

        logger.info(
            f"Password reset email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "send_password_reset_email")


@router.post("/notification")
async def send_notification(
    user_email: str,
    user_name: str,
    subject: str,
    message: str,
    priority: str = "normal",
):
    """Send a general-purpose notification email for user alerts and updates.

    Args:
        user_email (str): Recipient's email address.
        user_name (str): Recipient's name.
        subject (str): Subject of the notification email.
        message (str): Content of the notification message.
        priority (str, optional): Priority for sending the notification.

    Returns:
        EmailStatusResponse: Status and metadata of the notification email operation.

    Raises:
        HTTPException: On sending error or service failure.

    """
    try:
        logger.debug(f"API request to send notification email to: {user_email}")

        service = get_email_service()

        # Validate priority
        if priority not in ["low", "normal", "high"]:
            raise HTTPException(
                status_code=400, detail="priority must be one of: low, normal, high",
            )

        response = await service.send_notification_email(
            user_email=user_email,
            user_name=user_name,
            subject=subject,
            message=message,
            priority=priority,
        )

        logger.info(
            f"Notification email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return EmailStatusResponse(
            success=response.success,
            tracking_id=response.tracking_id,
            message_id=response.message_id,
            delivery_status=response.delivery_status,
            error_message=response.error_message,
            timestamp=response.timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "send_notification_email")


@router.get("/account-info")
async def get_ses_account_info():
    """Get AWS SES account information including quotas and statistics.

    Returns:
        dict: SES account details, quotas, and statistics.

    Raises:
        HTTPException: On SES API error or credentials failure.

    """
    try:
        logger.debug("API request to get SES account info")

        service = get_email_service()
        account_info = await service.get_account_info()

        return {
            "account_details": account_info.account_details,
            "sending_quota": account_info.sending_quota,
            "sending_statistics": account_info.sending_statistics,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "get_account_info")


@router.post("/verify-domain/{domain}")
async def verify_domain(domain: str):
    """Initiate domain verification process in SES for sending emails from the domain.

    Args:
        domain (str): Domain name to verify with SES.

    Returns:
        dict: Verification status and DNS records if applicable.

    Raises:
        HTTPException: On SES API error or verification failure.

    """
    try:
        logger.debug(f"API request to verify domain: {domain}")

        service = get_email_service()

        if not domain:
            raise HTTPException(status_code=400, detail="domain is required")

        success = await service.verify_domain(domain)

        return {
            "success": success,
            "domain": domain,
            "message": f"Domain verification initiated for {domain}"
            if success
            else f"Failed to verify domain {domain}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "verify_domain")


@router.post("/create-configuration-set/{name}")
async def create_configuration_set(name: str):
    """Create a configuration set in SES for tracking email events and metrics.

    Args:
        name (str): The name of the configuration set to create.

    Returns:
        dict: Status and details of the configuration set creation.

    Raises:
        HTTPException: On SES API error or configuration set failure.

    """
    try:
        logger.debug(f"API request to create configuration set: {name}")

        service = get_email_service()

        if not name:
            raise HTTPException(
                status_code=400, detail="configuration set name is required",
            )

        success = await service.create_configuration_set(name)

        return {
            "success": success,
            "name": name,
            "message": f"Configuration set '{name}' created successfully"
            if success
            else f"Failed to create configuration set '{name}'",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "create_configuration_set")


@router.get("/templates")
async def list_templates():
    """List all SES email templates configured in the account.

    Returns:
        dict: List of SES email templates and their metadata.

    Raises:
        HTTPException: On SES API error or template retrieval failure.

    """
    try:
        logger.debug("API request to list email templates")

        service = get_email_service()
        templates = await service.list_templates()

        return {"templates": templates, "count": len(templates)}

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "list_templates")


@router.get("/config/debug")
async def get_configuration_debug():
    """Get detailed configuration debug information for the email service.

    Returns:
        dict: Debug information about the email service configuration.

    Raises:
        HTTPException: On configuration retrieval failure.

    """
    try:
        from app.core.config import get_debug_info, validate_aws_configuration

        debug_info = get_debug_info()
        validation_result = validate_aws_configuration()

        return {
            "configuration": debug_info,
            "validation": validation_result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting configuration debug info: {e!s}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


@router.get("/config/status")
async def get_configuration_status():
    """Get a summary of the email service configuration status with recommendations.

    Returns:
        dict: Configuration status summary and recommendations.

    Raises:
        HTTPException: On configuration status retrieval failure.

    """
    try:
        from app.core.config import validate_aws_configuration

        validation_result = validate_aws_configuration()

        status = "ready" if validation_result["is_valid"] else "needs_configuration"

        return {
            "status": status,
            "ready": validation_result["is_valid"],
            "issues_count": len(validation_result["issues"]),
            "issues": validation_result["issues"],
            "recommendations": validation_result["recommendations"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting configuration status: {e!s}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/test-email")
async def test_email_sending():
    """Test email sending functionality by sending a test email.

    Returns:
        EmailStatusResponse: Status and metadata of the test email operation.

    Raises:
        HTTPException: On test email sending error or service failure.

    """
    try:
        logger.debug("API request to send test email")

        service = get_email_service()

        # Use a test email address that works in SES sandbox
        test_email = "test@example.com"

        response = await service.send_simple_email(
            to_email=test_email,
            subject="Test Email from Modular Email Service",
            html_content="<h1>Test Email</h1><p>This is a test email from the modular email service.</p><p>If you receive this, the email service is working correctly!</p>",
            text_content="Test Email\n\nThis is a test email from the modular email service.\n\nIf you receive this, the email service is working correctly!",
        )

        logger.info(
            f"Test email API response: success={response.success}, tracking_id={response.tracking_id}",
        )

        return {
            "success": response.success,
            "tracking_id": response.tracking_id,
            "message_id": response.message_id,
            "test_email": test_email,
            "message": "Test email sent successfully"
            if response.success
            else "Test email failed",
            "error": response.error_message if not response.success else None,
            "timestamp": response.timestamp.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_email_service_error(e, "test_email_sending")
