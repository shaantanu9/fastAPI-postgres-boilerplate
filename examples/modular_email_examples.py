"""Modular Email Service Examples.

This file demonstrates various ways to use the modular email service
for different email scenarios including simple emails, templates,
attachments, scheduling, and helper functions.

Run examples:
    python examples/modular_email_examples.py
"""

import asyncio

# Add parent directory to path for imports
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import contextlib

from app.services.email_service import (
    EmailRecipient,
    EmailRequest,
    EmailTemplate,
    create_email_service,
)


async def example_1_simple_email() -> None:
    """Example 1: Send a simple email with basic parameters."""
    # Create email service
    email_service = create_email_service()

    # Send simple email
    await email_service.send_simple_email(
        to_email="user@example.com",
        subject="Welcome to Our Service!",
        html_content="<h1>Hello!</h1><p>Thank you for joining us.</p>",
        text_content="Hello!\n\nThank you for joining us.",
        cc_emails=["manager@example.com"],
        bcc_emails=["admin@example.com"],
    )



async def example_2_multiple_recipients() -> None:
    """Example 2: Send email to multiple recipients with different types."""
    email_service = create_email_service()

    # Create recipients
    to_recipients = [
        EmailRecipient(email="user1@example.com", name="John Doe"),
        EmailRecipient(email="user2@example.com", name="Jane Smith"),
    ]

    cc_recipients = [EmailRecipient(email="manager@example.com", name="Manager")]

    bcc_recipients = [EmailRecipient(email="admin@example.com", name="Admin")]

    # Create email request
    email_request = EmailRequest(
        to_recipients=to_recipients,
        cc_recipients=cc_recipients,
        bcc_recipients=bcc_recipients,
        from_email="noreply@yourapp.com",
        from_name="Your App Team",
        subject="Important Update for All Users",
        html_content="""
        <h1>Important Update</h1>
        <p>Dear valued users,</p>
        <p>We have an important update to share with you...</p>
        <ul>
            <li>Feature 1 improvement</li>
            <li>Bug fixes</li>
            <li>New security enhancements</li>
        </ul>
        <p>Best regards,<br>Your App Team</p>
        """,
        text_content="""
        Important Update

        Dear valued users,

        We have an important update to share with you...

        - Feature 1 improvement
        - Bug fixes
        - New security enhancements

        Best regards,
        Your App Team
        """,
        message_tags={"type": "update", "category": "announcement"},
    )

    # Send email
    await email_service.send_email(email_request)



async def example_3_template_email() -> None:
    """Example 3: Send email using template with dynamic content."""
    email_service = create_email_service()

    # Create template
    template = EmailTemplate(
        subject="Welcome {{ user_name }} to {{ app_name }}!",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #007bff;">Welcome {{ user_name }}!</h1>
            <p>Thank you for joining {{ app_name }}. We're excited to have you on board!</p>

            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3>Your Account Details:</h3>
                <ul>
                    <li><strong>Username:</strong> {{ username }}</li>
                    <li><strong>Registration Date:</strong> {{ registration_date }}</li>
                    <li><strong>Account Type:</strong> {{ account_type }}</li>
                </ul>
            </div>

            <p>Next steps:</p>
            <ol>
                <li>Verify your email address</li>
                <li>Complete your profile</li>
                <li>Explore our features</li>
            </ol>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ dashboard_url }}"
                   style="background-color: #007bff; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Go to Dashboard
                </a>
            </div>

            <p>If you have any questions, feel free to contact our support team.</p>

            <p>Best regards,<br>{{ app_name }} Team</p>
        </body>
        </html>
        """,
        text_content="""
        Welcome {{ user_name }}!

        Thank you for joining {{ app_name }}. We're excited to have you on board!

        Your Account Details:
        - Username: {{ username }}
        - Registration Date: {{ registration_date }}
        - Account Type: {{ account_type }}

        Next steps:
        1. Verify your email address
        2. Complete your profile
        3. Explore our features

        Dashboard: {{ dashboard_url }}

        If you have any questions, feel free to contact our support team.

        Best regards,
        {{ app_name }} Team
        """,
        template_data={
            "user_name": "John Doe",
            "app_name": "AwesomeApp",
            "username": "john_doe",
            "registration_date": datetime.now().strftime("%Y-%m-%d"),
            "account_type": "Premium",
            "dashboard_url": "https://yourapp.com/dashboard",
        },
    )

    # Create email request with template
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="john.doe@example.com", name="John Doe")],
        from_email="welcome@yourapp.com",
        from_name="AwesomeApp Team",
        template=template,
        message_tags={"type": "welcome", "template": "user_welcome"},
    )

    # Send email
    await email_service.send_email(email_request)



async def example_4_email_with_attachments() -> None:
    """Example 4: Send email with file attachments."""
    email_service = create_email_service()

    # Create sample attachments

    # 1. PDF attachment from bytes
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n..."  # Sample PDF content
    pdf_attachment = email_service.create_pdf_attachment(
        content=pdf_content, filename="sample_document.pdf",
    )

    # 2. CSV attachment from string
    csv_content = (
        "Name,Email,Age\nJohn Doe,john@example.com,30\nJane Smith,jane@example.com,25"
    )
    csv_attachment = email_service.create_csv_attachment(
        content=csv_content, filename="user_data.csv",
    )

    # 3. Excel attachment (simulated content)
    excel_content = (
        b"PK\x03\x04..."  # Sample Excel content (in reality, use openpyxl or similar)
    )
    excel_attachment = email_service.create_excel_attachment(
        content=excel_content, filename="monthly_report.xlsx",
    )

    # Create email request with attachments
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="recipient@example.com", name="Recipient")],
        from_email="reports@yourapp.com",
        from_name="Reports Team",
        subject="Monthly Report with Attachments",
        html_content="""
        <h1>Monthly Report</h1>
        <p>Please find attached the monthly report files:</p>
        <ul>
            <li>sample_document.pdf - Documentation</li>
            <li>user_data.csv - User statistics</li>
            <li>monthly_report.xlsx - Detailed analysis</li>
        </ul>
        <p>Please review and let us know if you have any questions.</p>
        """,
        text_content="""
        Monthly Report

        Please find attached the monthly report files:
        - sample_document.pdf - Documentation
        - user_data.csv - User statistics
        - monthly_report.xlsx - Detailed analysis

        Please review and let us know if you have any questions.
        """,
        attachments=[pdf_attachment, csv_attachment, excel_attachment],
        message_tags={"type": "report", "period": "monthly"},
    )

    # Send email with attachments
    await email_service.send_email(email_request)



async def example_5_welcome_email_helper() -> None:
    """Example 5: Use welcome email helper function."""
    email_service = create_email_service()

    # Send welcome email using helper function
    await email_service.send_welcome_email(
        user_email="newuser@example.com",
        user_name="Alice Johnson",
        verification_token="abc123token456",
    )



async def example_6_password_reset_helper() -> None:
    """Example 6: Use password reset email helper function."""
    email_service = create_email_service()

    # Send password reset email using helper function
    await email_service.send_password_reset_email(
        user_email="user@example.com",
        user_name="Bob Wilson",
        reset_token="reset456token789",
    )



async def example_7_notification_email() -> None:
    """Example 7: Send notification email."""
    email_service = create_email_service()

    # Send notification email
    await email_service.send_notification_email(
        user_email="user@example.com",
        user_name="Charlie Brown",
        subject="System Maintenance Notification",
        message="We will be performing scheduled maintenance on our systems from 2 AM to 4 AM UTC. During this time, services may be temporarily unavailable.",
        priority="high",
    )



async def example_8_bulk_emails() -> None:
    """Example 8: Send bulk emails to multiple recipients."""
    email_service = create_email_service()

    # Create multiple email requests
    email_requests = []

    users = [
        {"email": "user1@example.com", "name": "User One", "plan": "Basic"},
        {"email": "user2@example.com", "name": "User Two", "plan": "Premium"},
        {"email": "user3@example.com", "name": "User Three", "plan": "Enterprise"},
    ]

    for user in users:
        template = EmailTemplate(
            subject="Your {{ plan }} Plan Update",
            html_content="""
            <h1>Hi {{ user_name }}!</h1>
            <p>We have updates regarding your {{ plan }} plan:</p>
            <p>Thank you for being a valued {{ plan }} customer!</p>
            """,
            text_content="""
            Hi {{ user_name }}!

            We have updates regarding your {{ plan }} plan:

            Thank you for being a valued {{ plan }} customer!
            """,
            template_data={"user_name": user["name"], "plan": user["plan"]},
        )

        email_request = EmailRequest(
            to_recipients=[EmailRecipient(email=user["email"], name=user["name"])],
            from_email="updates@yourapp.com",
            from_name="YourApp Team",
            template=template,
            message_tags={"type": "update", "plan": user["plan"].lower()},
        )

        email_requests.append(email_request)

    # Send bulk emails
    responses = await email_service.send_bulk_emails(email_requests)

    for _i, _response in enumerate(responses):
        pass


async def example_9_scheduled_email() -> None:
    """Example 9: Schedule email for later delivery."""
    email_service = create_email_service()

    # Schedule email for 1 hour from now
    send_time = datetime.utcnow() + timedelta(hours=1)

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="user@example.com", name="Future User")],
        from_email="scheduler@yourapp.com",
        from_name="Scheduler Bot",
        subject="Scheduled Message",
        html_content="<h1>This is a scheduled message!</h1><p>It was sent automatically at the scheduled time.</p>",
        text_content="This is a scheduled message!\n\nIt was sent automatically at the scheduled time.",
        send_time=send_time,
    )

    # Schedule the email
    await email_service.schedule_email(email_request, send_time)



async def example_10_account_management() -> None:
    """Example 10: Account management and SES operations."""
    email_service = create_email_service()

    try:
        # Get account information
        await email_service.get_account_info()

        # List templates
        await email_service.list_templates()

    except Exception:
        pass



async def run_all_examples() -> None:
    """Run all email examples."""
    examples = [
        example_1_simple_email,
        example_2_multiple_recipients,
        example_3_template_email,
        example_4_email_with_attachments,
        example_5_welcome_email_helper,
        example_6_password_reset_helper,
        example_7_notification_email,
        example_8_bulk_emails,
        example_9_scheduled_email,
        example_10_account_management,
    ]

    for example in examples:
        with contextlib.suppress(Exception):
            await example()



if __name__ == "__main__":
    # Set up environment (if needed)
    # os.environ["AWS_ACCESS_KEY_ID"] = "your-access-key"
    # os.environ["AWS_SECRET_ACCESS_KEY"] = "your-secret-key"
    # os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


    # Run examples
    asyncio.run(run_all_examples())
