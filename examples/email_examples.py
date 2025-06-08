"""AWS SES Email Utility Usage Examples.

This file demonstrates various ways to use the comprehensive AWS SES email utility
with different scenarios and features.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from app.core.aws_ses_utility import (
    EmailAttachment,
    EmailRecipient,
    EmailRequest,
    EmailTemplate,
    SESEmailUtility,
    create_ses_utility,
    send_password_reset_email,
    send_welcome_email,
)


async def example_1_simple_email() -> None:
    """Example 1: Send a simple email to one recipient."""
    # Create SES utility
    ses_utility = create_ses_utility()

    # Create email request
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
        from_email="noreply@yourapp.com",
        from_name="Your App",
        subject="Welcome to our app!",
        html_content="""
        <html>
        <body>
            <h1>Welcome!</h1>
            <p>Thank you for joining our app.</p>
        </body>
        </html>
        """,
        text_content="Welcome! Thank you for joining our app.",
    )

    # Send email
    await ses_utility.send_email(email_request)


async def example_2_multiple_recipients() -> None:
    """Example 2: Send email to multiple recipients with CC and BCC."""
    ses_utility = create_ses_utility()

    email_request = EmailRequest(
        to_recipients=[
            EmailRecipient(email="user1@example.com", name="John Doe"),
            EmailRecipient(email="user2@example.com", name="Jane Smith"),
        ],
        cc_recipients=[EmailRecipient(email="manager@example.com", name="Manager")],
        bcc_recipients=[EmailRecipient(email="admin@yourapp.com", name="Admin")],
        from_email="noreply@yourapp.com",
        from_name="Your App",
        subject="Team Update",
        html_content="<h1>Team Update</h1><p>Important news for the team.</p>",
        message_tags={"type": "team_update", "priority": "high"},
    )

    await ses_utility.send_email(email_request)


async def example_3_template_email() -> None:
    """Example 3: Send email using Jinja2 templates."""
    ses_utility = create_ses_utility()

    # Create template
    template = EmailTemplate(
        subject="Welcome {{ user_name }} to {{ app_name }}!",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h1>Welcome {{ user_name }}!</h1>
            <p>Thank you for joining <strong>{{ app_name }}</strong>.</p>
            <p>Your account details:</p>
            <ul>
                <li>Username: {{ username }}</li>
                <li>Plan: {{ subscription_plan }}</li>
                <li>Trial ends: {{ trial_end_date }}</li>
            </ul>
            <a href="{{ app_url }}" style="background-color: #007bff; color: white;
               padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                Get Started
            </a>
        </body>
        </html>
        """,
        text_content="""
        Welcome {{ user_name }}!

        Thank you for joining {{ app_name }}.

        Your account details:
        - Username: {{ username }}
        - Plan: {{ subscription_plan }}
        - Trial ends: {{ trial_end_date }}

        Get started: {{ app_url }}
        """,
    )

    # Context data for template
    template_context = {
        "user_name": "John Doe",
        "app_name": "Amazing SaaS",
        "username": "johndoe",
        "subscription_plan": "Pro",
        "trial_end_date": "December 31, 2024",
        "app_url": "https://yourapp.com/dashboard",
    }

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
        from_email="noreply@yourapp.com",
        from_name="Amazing SaaS",
        template=template,
        template_context=template_context,
        message_tags={"type": "onboarding", "user_type": "trial"},
    )

    await ses_utility.send_email(email_request)


async def example_4_email_with_attachments() -> None:
    """Example 4: Send email with file attachments."""
    ses_utility = create_ses_utility()

    # Create attachments
    attachments = [
        # PDF attachment
        EmailAttachment(
            filename="welcome_guide.pdf",
            content=b"PDF content here...",  # In real usage, read from file
            content_type="application/pdf",
        ),
        # Image attachment (inline)
        EmailAttachment(
            filename="logo.png",
            content=b"PNG image data...",  # In real usage, read from file
            content_type="image/png",
            disposition="inline",
            content_id="logo",
        ),
        # Excel attachment
        EmailAttachment(
            filename="data_export.xlsx",
            content=b"Excel file data...",  # In real usage, read from file
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    ]

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
        from_email="noreply@yourapp.com",
        from_name="Your App",
        subject="Your documents are ready",
        html_content="""
        <html>
        <body>
            <h1>Your Documents</h1>
            <p>Please find your requested documents attached.</p>
            <img src="cid:logo" alt="Company Logo" style="width: 200px;">
            <p>Best regards,<br>The Team</p>
        </body>
        </html>
        """,
        attachments=attachments,
        message_tags={"type": "document_delivery"},
    )

    await ses_utility.send_email(email_request)


async def example_5_scheduled_email() -> None:
    """Example 5: Schedule email for later sending."""
    # Note: This requires Procrastinate to be configured
    ses_utility = create_ses_utility()

    # Schedule email for 1 hour from now
    send_time = datetime.utcnow() + timedelta(hours=1)

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
        from_email="noreply@yourapp.com",
        from_name="Your App",
        subject="Scheduled Reminder",
        html_content="<h1>This is your scheduled reminder!</h1>",
        send_time=send_time,
        message_tags={"type": "reminder", "scheduled": "true"},
    )

    # Send with immediate=False to schedule
    await ses_utility.send_email(email_request, immediate=False)


async def example_6_bulk_template_email() -> None:
    """Example 6: Send bulk emails using SES templates."""
    ses_utility = create_ses_utility()

    # First, create a template in SES (this is a one-time setup)
    template_created = await ses_utility.create_template(
        template_name="newsletter_template",
        subject="{{subject}}",
        html_content="""
        <html>
        <body>
            <h1>{{title}}</h1>
            <p>Hello {{name}},</p>
            <p>{{content}}</p>
            <p>Best regards,<br>{{sender_name}}</p>
        </body>
        </html>
        """,
        text_content="""
        {{title}}

        Hello {{name}},

        {{content}}

        Best regards,
        {{sender_name}}
        """,
    )

    if template_created:

        # Send bulk emails using the template
        recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]

        template_data = {
            "subject": "Monthly Newsletter",
            "title": "Monthly Update",
            "content": "Here's what happened this month...",
            "sender_name": "Your Team",
            "name": "Valued Customer",
        }

        await ses_utility.send_template_email(
            to_recipients=recipients,
            template_name="newsletter_template",
            template_data=template_data,
            from_email="newsletter@yourapp.com",
            from_name="Your App Newsletter",
        )



async def example_7_helper_functions() -> None:
    """Example 7: Use built-in helper functions."""
    # Send welcome email
    await send_welcome_email(
        user_email="newuser@example.com",
        user_name="New User",
        verification_token="abc123token",
    )

    # Send password reset email
    await send_password_reset_email(
        user_email="user@example.com", user_name="John Doe", reset_token="xyz789token",
    )


async def example_8_error_handling() -> None:
    """Example 8: Error handling and logging."""
    ses_utility = create_ses_utility()

    # Example with invalid email
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="invalid-email", name="Test User")],
        from_email="noreply@yourapp.com",
        subject="Test Email",
        html_content="<p>Test content</p>",
    )

    response = await ses_utility.send_email(email_request)

    if not response.success:
        pass
    else:
        pass


async def example_9_advanced_configuration() -> None:
    """Example 9: Advanced SES configuration."""
    # Create SES utility with custom configuration
    ses_utility = SESEmailUtility(
        aws_region="us-west-2",
        configuration_set="my-config-set",
        from_domain="yourapp.com",
    )

    # Get account information
    account_info = await ses_utility.get_account_info()
    if account_info:
        pass

    # Create configuration set (one-time setup)
    await ses_utility.create_configuration_set(
        name="my-config-set",
        tracking_options={"CustomRedirectDomain": "track.yourapp.com"},
    )

    # Verify domain (one-time setup)
    await ses_utility.verify_domain_identity("yourapp.com")


async def example_10_read_file_attachments() -> None:
    """Example 10: Read real files as attachments."""
    ses_utility = create_ses_utility()

    attachments = []

    # Example: Read a real file as attachment
    # Note: Replace with actual file paths in your application
    sample_files = [
        ("sample.txt", "text/plain"),
        ("sample.pdf", "application/pdf"),
        ("sample.jpg", "image/jpeg"),
    ]

    for filename, content_type in sample_files:
        file_path = Path(f"examples/sample_files/{filename}")
        if file_path.exists():
            with open(file_path, "rb") as f:
                content = f.read()

            attachments.append(
                EmailAttachment(
                    filename=filename, content=content, content_type=content_type,
                ),
            )

    if attachments:
        email_request = EmailRequest(
            to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
            from_email="noreply@yourapp.com",
            from_name="Your App",
            subject="Files from real filesystem",
            html_content="<h1>Your files are attached!</h1>",
            attachments=attachments,
        )

        await ses_utility.send_email(email_request)
    else:
        pass


async def main() -> None:
    """Run all examples."""
    try:
        await example_1_simple_email()
        await example_2_multiple_recipients()
        await example_3_template_email()
        await example_4_email_with_attachments()
        await example_5_scheduled_email()
        await example_6_bulk_template_email()
        await example_7_helper_functions()
        await example_8_error_handling()
        await example_9_advanced_configuration()
        await example_10_read_file_attachments()


    except Exception:
        pass


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
