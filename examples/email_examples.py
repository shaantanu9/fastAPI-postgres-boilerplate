"""
AWS SES Email Utility Usage Examples

This file demonstrates various ways to use the comprehensive AWS SES email utility
with different scenarios and features.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from app.core.aws_ses_utility import (
    SESEmailUtility,
    EmailRequest,
    EmailRecipient,
    EmailTemplate,
    EmailAttachment,
    create_ses_utility,
    send_welcome_email,
    send_password_reset_email
)


async def example_1_simple_email():
    """Example 1: Send a simple email to one recipient"""
    print("📧 Example 1: Simple Email")
    
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
        text_content="Welcome! Thank you for joining our app."
    )
    
    # Send email
    response = await ses_utility.send_email(email_request)
    print(f"✅ Email sent: {response.success}, Tracking ID: {response.tracking_id}")


async def example_2_multiple_recipients():
    """Example 2: Send email to multiple recipients with CC and BCC"""
    print("\n📧 Example 2: Multiple Recipients")
    
    ses_utility = create_ses_utility()
    
    email_request = EmailRequest(
        to_recipients=[
            EmailRecipient(email="user1@example.com", name="John Doe"),
            EmailRecipient(email="user2@example.com", name="Jane Smith")
        ],
        cc_recipients=[
            EmailRecipient(email="manager@example.com", name="Manager")
        ],
        bcc_recipients=[
            EmailRecipient(email="admin@yourapp.com", name="Admin")
        ],
        from_email="noreply@yourapp.com",
        from_name="Your App",
        subject="Team Update",
        html_content="<h1>Team Update</h1><p>Important news for the team.</p>",
        message_tags={"type": "team_update", "priority": "high"}
    )
    
    response = await ses_utility.send_email(email_request)
    print(f"✅ Multi-recipient email sent: {response.success}")


async def example_3_template_email():
    """Example 3: Send email using Jinja2 templates"""
    print("\n📧 Example 3: Template Email")
    
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
        """
    )
    
    # Context data for template
    template_context = {
        "user_name": "John Doe",
        "app_name": "Amazing SaaS",
        "username": "johndoe",
        "subscription_plan": "Pro",
        "trial_end_date": "December 31, 2024",
        "app_url": "https://yourapp.com/dashboard"
    }
    
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
        from_email="noreply@yourapp.com",
        from_name="Amazing SaaS",
        template=template,
        template_context=template_context,
        message_tags={"type": "onboarding", "user_type": "trial"}
    )
    
    response = await ses_utility.send_email(email_request)
    print(f"✅ Template email sent: {response.success}")


async def example_4_email_with_attachments():
    """Example 4: Send email with file attachments"""
    print("\n📧 Example 4: Email with Attachments")
    
    ses_utility = create_ses_utility()
    
    # Create attachments
    attachments = [
        # PDF attachment
        EmailAttachment(
            filename="welcome_guide.pdf",
            content=b"PDF content here...",  # In real usage, read from file
            content_type="application/pdf"
        ),
        
        # Image attachment (inline)
        EmailAttachment(
            filename="logo.png",
            content=b"PNG image data...",  # In real usage, read from file
            content_type="image/png",
            disposition="inline",
            content_id="logo"
        ),
        
        # Excel attachment
        EmailAttachment(
            filename="data_export.xlsx",
            content=b"Excel file data...",  # In real usage, read from file
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
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
        message_tags={"type": "document_delivery"}
    )
    
    response = await ses_utility.send_email(email_request)
    print(f"✅ Email with attachments sent: {response.success}")


async def example_5_scheduled_email():
    """Example 5: Schedule email for later sending"""
    print("\n📧 Example 5: Scheduled Email")
    
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
        message_tags={"type": "reminder", "scheduled": "true"}
    )
    
    # Send with immediate=False to schedule
    response = await ses_utility.send_email(email_request, immediate=False)
    print(f"✅ Email scheduled: {response.success}, Status: {response.delivery_status}")


async def example_6_bulk_template_email():
    """Example 6: Send bulk emails using SES templates"""
    print("\n📧 Example 6: Bulk Template Email")
    
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
        """
    )
    
    if template_created:
        print("📝 Template created successfully")
        
        # Send bulk emails using the template
        recipients = [
            "user1@example.com",
            "user2@example.com",
            "user3@example.com"
        ]
        
        template_data = {
            "subject": "Monthly Newsletter",
            "title": "Monthly Update",
            "content": "Here's what happened this month...",
            "sender_name": "Your Team",
            "name": "Valued Customer"
        }
        
        response = await ses_utility.send_template_email(
            to_recipients=recipients,
            template_name="newsletter_template",
            template_data=template_data,
            from_email="newsletter@yourapp.com",
            from_name="Your App Newsletter"
        )
        
        print(f"✅ Bulk template email sent: {response.success}")


async def example_7_helper_functions():
    """Example 7: Use built-in helper functions"""
    print("\n📧 Example 7: Helper Functions")
    
    # Send welcome email
    response1 = await send_welcome_email(
        user_email="newuser@example.com",
        user_name="New User",
        verification_token="abc123token"
    )
    print(f"✅ Welcome email sent: {response1.success}")
    
    # Send password reset email
    response2 = await send_password_reset_email(
        user_email="user@example.com",
        user_name="John Doe",
        reset_token="xyz789token"
    )
    print(f"✅ Password reset email sent: {response2.success}")


async def example_8_error_handling():
    """Example 8: Error handling and logging"""
    print("\n📧 Example 8: Error Handling")
    
    ses_utility = create_ses_utility()
    
    # Example with invalid email
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="invalid-email", name="Test User")],
        from_email="noreply@yourapp.com",
        subject="Test Email",
        html_content="<p>Test content</p>"
    )
    
    response = await ses_utility.send_email(email_request)
    
    if not response.success:
        print(f"❌ Email failed: {response.error_message}")
        print(f"🔍 Error code: {response.error_code}")
        print(f"📊 Tracking ID: {response.tracking_id}")
    else:
        print(f"✅ Email sent successfully: {response.tracking_id}")


async def example_9_advanced_configuration():
    """Example 9: Advanced SES configuration"""
    print("\n📧 Example 9: Advanced Configuration")
    
    # Create SES utility with custom configuration
    ses_utility = SESEmailUtility(
        aws_region="us-west-2",
        configuration_set="my-config-set",
        from_domain="yourapp.com"
    )
    
    # Get account information
    account_info = await ses_utility.get_account_info()
    if account_info:
        print(f"📊 SES Account Info: {account_info}")
    
    # Create configuration set (one-time setup)
    config_created = await ses_utility.create_configuration_set(
        name="my-config-set",
        tracking_options={"CustomRedirectDomain": "track.yourapp.com"}
    )
    print(f"⚙️ Configuration set created: {config_created}")
    
    # Verify domain (one-time setup)
    domain_verified = await ses_utility.verify_domain_identity("yourapp.com")
    print(f"🔐 Domain verification initiated: {domain_verified}")


async def example_10_read_file_attachments():
    """Example 10: Read real files as attachments"""
    print("\n📧 Example 10: Real File Attachments")
    
    ses_utility = create_ses_utility()
    
    attachments = []
    
    # Example: Read a real file as attachment
    # Note: Replace with actual file paths in your application
    sample_files = [
        ("sample.txt", "text/plain"),
        ("sample.pdf", "application/pdf"),
        ("sample.jpg", "image/jpeg")
    ]
    
    for filename, content_type in sample_files:
        file_path = Path(f"examples/sample_files/{filename}")
        if file_path.exists():
            with open(file_path, "rb") as f:
                content = f.read()
            
            attachments.append(EmailAttachment(
                filename=filename,
                content=content,
                content_type=content_type
            ))
    
    if attachments:
        email_request = EmailRequest(
            to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
            from_email="noreply@yourapp.com",
            from_name="Your App",
            subject="Files from real filesystem",
            html_content="<h1>Your files are attached!</h1>",
            attachments=attachments
        )
        
        response = await ses_utility.send_email(email_request)
        print(f"✅ Email with real file attachments sent: {response.success}")
    else:
        print("ℹ️ No sample files found, skipping real file attachment example")


async def main():
    """Run all examples"""
    print("🚀 AWS SES Email Utility Examples\n" + "="*50)
    
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
        
        print("\n🎉 All examples completed!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        print("💡 Make sure you have:")
        print("   - AWS credentials configured")
        print("   - Verified domain in SES")
        print("   - Valid email addresses")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main()) 