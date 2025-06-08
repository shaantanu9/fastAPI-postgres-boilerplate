"""Email Service Helper Functions.

Pre-configured email functions for common use cases like welcome emails,
password reset emails, notifications, etc.
"""

from app.core.config import settings

from .client import create_ses_client
from .models import EmailRecipient, EmailRequest, EmailResponse, EmailTemplate
from .sender import EmailSender


async def send_welcome_email(
    user_email: str,
    user_name: str,
    verification_token: str,
    email_sender: EmailSender | None = None,
) -> EmailResponse:
    """Send welcome email with verification link.

    Args:
        user_email: User's email address
        user_name: User's display name
        verification_token: Email verification token
        email_sender: Optional EmailSender instance

    Returns:
        EmailResponse object

    """
    if not email_sender:
        ses_client = create_ses_client()
        email_sender = EmailSender(ses_client)

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
            "verification_link": f"{settings.frontend_url}/verify-email?token={verification_token}",
        },
    )

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email=user_email, name=user_name)],
        from_email=settings.EMAIL_FROM_EMAIL,
        from_name=settings.EMAIL_FROM_NAME,
        template=template,
        configuration_set=settings.SES_CONFIGURATION_SET,
        message_tags={"type": "welcome", "category": "authentication"},
    )

    return await email_sender.send_email(email_request)


async def send_password_reset_email(
    user_email: str,
    user_name: str,
    reset_token: str,
    email_sender: EmailSender | None = None,
) -> EmailResponse:
    """Send password reset email.

    Args:
        user_email: User's email address
        user_name: User's display name
        reset_token: Password reset token
        email_sender: Optional EmailSender instance

    Returns:
        EmailResponse object

    """
    if not email_sender:
        ses_client = create_ses_client()
        email_sender = EmailSender(ses_client)

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
            "reset_link": f"{settings.frontend_url}/reset-password?token={reset_token}",
        },
    )

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email=user_email, name=user_name)],
        from_email=settings.EMAIL_FROM_EMAIL,
        from_name=settings.EMAIL_FROM_NAME,
        template=template,
        configuration_set=settings.SES_CONFIGURATION_SET,
        message_tags={"type": "password_reset", "category": "authentication"},
    )

    return await email_sender.send_email(email_request)


async def send_notification_email(
    user_email: str,
    user_name: str,
    subject: str,
    message: str,
    priority: str = "normal",
    email_sender: EmailSender | None = None,
) -> EmailResponse:
    """Send notification email.

    Args:
        user_email: User's email address
        user_name: User's display name
        subject: Email subject
        message: Email message content
        priority: Email priority (low, normal, high)
        email_sender: Optional EmailSender instance

    Returns:
        EmailResponse object

    """
    if not email_sender:
        ses_client = create_ses_client()
        email_sender = EmailSender(ses_client)

    template = EmailTemplate(
        subject=subject,
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">{{ subject }}</h2>
            <p>Hello {{ user_name }},</p>
            <div style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff;">
                {{ message }}
            </div>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
                This is an automated notification from {{ app_name }}.
            </p>
        </body>
        </html>
        """,
        text_content="""
        {{ subject }}

        Hello {{ user_name }},

        {{ message }}

        ---
        This is an automated notification from {{ app_name }}.
        """,
        template_data={
            "app_name": settings.APP_NAME,
            "user_name": user_name,
            "subject": subject,
            "message": message,
        },
    )

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email=user_email, name=user_name)],
        from_email=settings.EMAIL_FROM_EMAIL,
        from_name=settings.EMAIL_FROM_NAME,
        template=template,
        priority=priority,
        configuration_set=settings.SES_CONFIGURATION_SET,
        message_tags={"type": "notification", "priority": priority},
    )

    return await email_sender.send_email(email_request)


async def send_invoice_email(
    customer_email: str,
    customer_name: str,
    invoice_number: str,
    amount: str,
    due_date: str,
    pdf_content: bytes | None = None,
    email_sender: EmailSender | None = None,
) -> EmailResponse:
    """Send invoice email with optional PDF attachment.

    Args:
        customer_email: Customer's email address
        customer_name: Customer's name
        invoice_number: Invoice number
        amount: Invoice amount
        due_date: Payment due date
        pdf_content: Optional PDF invoice content
        email_sender: Optional EmailSender instance

    Returns:
        EmailResponse object

    """
    if not email_sender:
        ses_client = create_ses_client()
        email_sender = EmailSender(ses_client)

    template = EmailTemplate(
        subject="Invoice {{ invoice_number }} from {{ app_name }}",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Invoice {{ invoice_number }}</h2>
            <p>Dear {{ customer_name }},</p>
            <p>Please find your invoice details below:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Invoice Number:</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{{ invoice_number }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Amount Due:</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{{ amount }}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Due Date:</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{{ due_date }}</td>
                </tr>
            </table>
            <p>Please process payment by the due date to avoid any late fees.</p>
            <p>Thank you for your business!</p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
                {{ app_name }} - {{ support_email }}
            </p>
        </body>
        </html>
        """,
        text_content="""
        Invoice {{ invoice_number }}

        Dear {{ customer_name }},

        Please find your invoice details below:

        Invoice Number: {{ invoice_number }}
        Amount Due: {{ amount }}
        Due Date: {{ due_date }}

        Please process payment by the due date to avoid any late fees.

        Thank you for your business!

        {{ app_name }} - {{ support_email }}
        """,
        template_data={
            "app_name": settings.APP_NAME,
            "customer_name": customer_name,
            "invoice_number": invoice_number,
            "amount": amount,
            "due_date": due_date,
            "support_email": settings.support_email,
        },
    )

    # Add PDF attachment if provided
    attachments = []
    if pdf_content:
        from .attachments import AttachmentHandler

        pdf_attachment = AttachmentHandler.create_pdf_attachment(
            content=pdf_content, filename=f"invoice_{invoice_number}.pdf",
        )
        attachments.append(pdf_attachment)

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email=customer_email, name=customer_name)],
        from_email=settings.EMAIL_FROM_EMAIL,
        from_name=settings.EMAIL_FROM_NAME,
        template=template,
        attachments=attachments,
        configuration_set=settings.SES_CONFIGURATION_SET,
        message_tags={"type": "invoice", "invoice_number": invoice_number},
    )

    return await email_sender.send_email(email_request)


async def send_marketing_email(
    recipients: list[EmailRecipient],
    subject: str,
    html_content: str,
    text_content: str | None = None,
    campaign_id: str | None = None,
    email_sender: EmailSender | None = None,
) -> list[EmailResponse]:
    """Send marketing email to multiple recipients.

    Args:
        recipients: List of email recipients
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text content (optional)
        campaign_id: Campaign tracking ID
        email_sender: Optional EmailSender instance

    Returns:
        List of EmailResponse objects

    """
    if not email_sender:
        ses_client = create_ses_client()
        email_sender = EmailSender(ses_client)

    responses = []

    for recipient in recipients:
        email_request = EmailRequest(
            to_recipients=[recipient],
            from_email=settings.EMAIL_FROM_EMAIL,
            from_name=settings.EMAIL_FROM_NAME,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            campaign_id=campaign_id,
            configuration_set=settings.SES_CONFIGURATION_SET,
            message_tags={"type": "marketing", "campaign_id": campaign_id or "default"},
        )

        response = await email_sender.send_email(email_request)
        responses.append(response)

    return responses
