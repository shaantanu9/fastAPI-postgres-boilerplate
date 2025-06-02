# AWS SES Email Utility Documentation

## Overview

The AWS SES Email Utility is a comprehensive, production-ready email sending system built on top of Amazon Simple Email Service (SES). It provides advanced features for modern web applications including scheduled emails, template support, attachments, tracking, and job queue integration.

## Features

### 🚀 Core Features

- **Multiple Recipients**: Support for TO, CC, and BCC recipients
- **Rich Content**: HTML and plain text email support
- **Template System**: Jinja2-powered dynamic email templates
- **File Attachments**: Support for multiple file types including inline images
- **Scheduled Sending**: Queue emails for future delivery using Procrastinate
- **Bulk Emails**: Efficient bulk email sending with SES templates

### 📊 Advanced Features

- **Email Tracking**: Unique tracking IDs and campaign tracking
- **Configuration Sets**: SES configuration sets for advanced analytics
- **Message Tags**: Categorize emails for better organization
- **Error Handling**: Comprehensive error handling with retry logic
- **Account Management**: SES account info and quota monitoring
- **Domain Verification**: Automated domain verification workflow

### 🔒 Enterprise Features

- **Security**: Input validation and sanitization
- **Logging**: Comprehensive logging with structured data
- **Monitoring**: Integration with SES sending statistics
- **Compliance**: Support for bounce and complaint handling
- **Rate Limiting**: Built-in respect for SES sending limits

## Installation

### Dependencies

Add to your `requirements.txt`:

```txt
boto3>=1.34.0
jinja2>=3.1.0
procrastinate>=2.0.0  # Optional, for scheduled emails
pydantic>=2.0.0
loguru>=0.7.0
```

### AWS Configuration

1. **Set up AWS credentials** (one of the following):

   - Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - AWS credentials file (`~/.aws/credentials`)
   - IAM roles (recommended for production)

2. **Configure SES permissions**:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ses:SendEmail",
           "ses:SendRawEmail",
           "ses:SendBulkTemplatedEmail",
           "ses:CreateTemplate",
           "ses:GetTemplate",
           "ses:ListTemplates",
           "ses:UpdateTemplate",
           "ses:DeleteTemplate",
           "ses:GetSendQuota",
           "ses:GetSendStatistics",
           "ses:GetAccountSendingEnabled",
           "ses:VerifyEmailIdentity",
           "ses:VerifyDomainIdentity",
           "ses:CreateConfigurationSet",
           "ses:GetConfigurationSet"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

3. **Verify your domain** in AWS SES console or use the utility function:
   ```python
   await ses_utility.verify_domain_identity("yourdomain.com")
   ```

### Environment Variables

Add to your `.env` file:

```env
# AWS SES Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
SES_CONFIGURATION_SET=your-config-set  # Optional
EMAIL_FROM_DOMAIN=yourdomain.com
EMAIL_FROM_EMAIL=noreply@yourdomain.com
EMAIL_FROM_NAME=Your App Name
EMAIL_PROVIDER=ses
```

## Quick Start

### Basic Email Sending

```python
import asyncio
from app.core.aws_ses_utility import create_ses_utility, EmailRequest, EmailRecipient

async def send_simple_email():
    # Create utility instance
    ses_utility = create_ses_utility()

    # Create email request
    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
        from_email="noreply@yourdomain.com",
        from_name="Your App",
        subject="Welcome!",
        html_content="<h1>Welcome to our app!</h1>",
        text_content="Welcome to our app!"
    )

    # Send email
    response = await ses_utility.send_email(email_request)
    print(f"Email sent: {response.success}, Tracking ID: {response.tracking_id}")

# Run the example
asyncio.run(send_simple_email())
```

### Using Helper Functions

```python
from app.core.aws_ses_utility import send_welcome_email, send_password_reset_email

# Send welcome email with verification
response = await send_welcome_email(
    user_email="user@example.com",
    user_name="John Doe",
    verification_token="abc123"
)

# Send password reset email
response = await send_password_reset_email(
    user_email="user@example.com",
    user_name="John Doe",
    reset_token="xyz789"
)
```

## Advanced Usage

### Template-Based Emails

```python
from app.core.aws_ses_utility import EmailTemplate

# Create a template
template = EmailTemplate(
    subject="Welcome {{ user_name }} to {{ app_name }}!",
    html_content="""
    <html>
    <body>
        <h1>Welcome {{ user_name }}!</h1>
        <p>Thank you for joining {{ app_name }}.</p>
        <p>Your account: {{ username }}</p>
        <a href="{{ app_url }}">Get Started</a>
    </body>
    </html>
    """,
    text_content="""
    Welcome {{ user_name }}!
    Thank you for joining {{ app_name }}.
    Your account: {{ username }}
    Get started: {{ app_url }}
    """
)

# Template context
context = {
    "user_name": "John Doe",
    "app_name": "Amazing SaaS",
    "username": "johndoe",
    "app_url": "https://yourapp.com"
}

email_request = EmailRequest(
    to_recipients=[EmailRecipient(email="user@example.com", name="John Doe")],
    from_email="noreply@yourdomain.com",
    template=template,
    template_context=context
)

response = await ses_utility.send_email(email_request)
```

### Email with Attachments

```python
from app.core.aws_ses_utility import EmailAttachment

# Read file content
with open("document.pdf", "rb") as f:
    pdf_content = f.read()

with open("logo.png", "rb") as f:
    logo_content = f.read()

# Create attachments
attachments = [
    EmailAttachment(
        filename="document.pdf",
        content=pdf_content,
        content_type="application/pdf"
    ),
    EmailAttachment(
        filename="logo.png",
        content=logo_content,
        content_type="image/png",
        disposition="inline",
        content_id="logo"
    )
]

email_request = EmailRequest(
    to_recipients=[EmailRecipient(email="user@example.com")],
    from_email="noreply@yourdomain.com",
    subject="Documents Attached",
    html_content='<h1>Your documents</h1><img src="cid:logo" alt="Logo">',
    attachments=attachments
)

response = await ses_utility.send_email(email_request)
```

### Scheduled Email Sending

```python
from datetime import datetime, timedelta

# Schedule email for 1 hour from now
send_time = datetime.utcnow() + timedelta(hours=1)

email_request = EmailRequest(
    to_recipients=[EmailRecipient(email="user@example.com")],
    from_email="noreply@yourdomain.com",
    subject="Scheduled Reminder",
    html_content="<h1>This is your reminder!</h1>",
    send_time=send_time
)

# Send with immediate=False to schedule
response = await ses_utility.send_email(email_request, immediate=False)
print(f"Email scheduled: {response.delivery_status}")
```

### Bulk Email with SES Templates

```python
# Create SES template (one-time setup)
template_created = await ses_utility.create_template(
    template_name="newsletter",
    subject="{{subject}}",
    html_content="<h1>{{title}}</h1><p>Hello {{name}}, {{content}}</p>",
    text_content="{{title}}\nHello {{name}}, {{content}}"
)

# Send bulk emails
recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]
template_data = {
    "subject": "Monthly Newsletter",
    "title": "Monthly Update",
    "content": "Here's what happened this month...",
    "name": "Valued Customer"
}

response = await ses_utility.send_template_email(
    to_recipients=recipients,
    template_name="newsletter",
    template_data=template_data,
    from_email="newsletter@yourdomain.com"
)
```

### Multiple Recipients

```python
email_request = EmailRequest(
    to_recipients=[
        EmailRecipient(email="user1@example.com", name="John Doe"),
        EmailRecipient(email="user2@example.com", name="Jane Smith")
    ],
    cc_recipients=[
        EmailRecipient(email="manager@example.com", name="Manager")
    ],
    bcc_recipients=[
        EmailRecipient(email="admin@yourdomain.com", name="Admin")
    ],
    from_email="noreply@yourdomain.com",
    subject="Team Update",
    html_content="<h1>Important team update</h1>",
    message_tags={"type": "team_update", "priority": "high"}
)

response = await ses_utility.send_email(email_request)
```

## Configuration and Setup

### SES Configuration Sets

Configuration sets help you track email sending metrics:

```python
# Create configuration set
config_created = await ses_utility.create_configuration_set(
    name="my-app-emails",
    tracking_options={"CustomRedirectDomain": "track.yourdomain.com"}
)

# Use in emails
email_request = EmailRequest(
    # ... other parameters
    configuration_set="my-app-emails"
)
```

### Email Tracking and Analytics

```python
email_request = EmailRequest(
    # ... other parameters
    tracking_id="custom-tracking-id",  # Optional, auto-generated if not provided
    campaign_id="summer-2024-promo",
    message_tags={
        "type": "promotional",
        "campaign": "summer-2024",
        "segment": "premium-users"
    }
)
```

### Account Information and Monitoring

```python
# Get SES account information
account_info = await ses_utility.get_account_info()
print(f"Sending quota: {account_info['sending_quota']}")
print(f"Sending statistics: {account_info['sending_statistics']}")
```

## Integration with Procrastinate

For scheduled email sending, configure Procrastinate:

### Setup

```python
import procrastinate
from app.core.aws_ses_utility import send_scheduled_email_task

# Create Procrastinate app
app = procrastinate.App(
    connector=procrastinate.AiopgConnector(
        conninfo="postgresql://user:password@localhost/dbname"
    )
)

# Register the email task
app.task(send_scheduled_email_task)

# Create SES utility with Procrastinate
ses_utility = create_ses_utility(procrastinate_app=app)
```

### Worker Process

```python
# Run worker (separate process)
import asyncio
from app.core.aws_ses_utility import send_scheduled_email_task

async def main():
    await app.run_worker_async()

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

### Response Model

All email operations return an `EmailResponse` object:

```python
class EmailResponse:
    success: bool
    message_id: Optional[str]
    tracking_id: str
    error_message: Optional[str]
    error_code: Optional[str]
    timestamp: datetime
    delivery_status: str  # sent, scheduled, failed, queued
```

### Example Error Handling

```python
response = await ses_utility.send_email(email_request)

if response.success:
    print(f"✅ Email sent successfully!")
    print(f"Message ID: {response.message_id}")
    print(f"Tracking ID: {response.tracking_id}")
else:
    print(f"❌ Email failed: {response.error_message}")
    print(f"Error code: {response.error_code}")
    print(f"Tracking ID: {response.tracking_id}")

    # Log for debugging
    logger.error(f"Email failed", extra={
        "tracking_id": response.tracking_id,
        "error_code": response.error_code,
        "error_message": response.error_message
    })
```

### Common Error Codes

- `MessageRejected`: Email content rejected by SES
- `SendingQuotaExceeded`: Daily sending quota exceeded
- `ThrottlingException`: Sending rate exceeded
- `InvalidParameterValue`: Invalid email address or parameter
- `ConfigurationSetDoesNotExist`: Configuration set not found

## Best Practices

### 1. Domain Verification

- Always verify your sending domain in SES
- Set up DKIM and SPF records
- Use a dedicated subdomain for transactional emails

### 2. Email Content

- Always provide both HTML and text versions
- Use responsive email templates
- Keep subject lines under 50 characters
- Avoid spam trigger words

### 3. Recipient Management

- Validate email addresses before sending
- Implement bounce and complaint handling
- Maintain suppression lists
- Use double opt-in for marketing emails

### 4. Monitoring and Analytics

- Use configuration sets for tracking
- Monitor sending statistics regularly
- Set up CloudWatch alarms for high bounce rates
- Track email engagement metrics

### 5. Rate Limiting

- Respect SES sending limits
- Implement exponential backoff for retries
- Use bulk operations for large volumes
- Monitor and adjust sending rates

### 6. Security

- Use IAM roles instead of access keys in production
- Encrypt sensitive template data
- Validate all input parameters
- Log security-related events

### 7. Performance

- Use connection pooling for high volume
- Batch emails when possible
- Cache templates and configuration
- Use async operations consistently

## Testing

### Development Testing

```python
# Test with sandbox mode (if available in your region)
ses_utility = SESEmailUtility(
    aws_region="us-east-1",
    # Add sandbox configuration if needed
)

# Test email sending
response = await ses_utility.send_email(test_email_request)
assert response.success
assert response.tracking_id is not None
```

### Integration Tests

```python
import pytest
from app.core.aws_ses_utility import create_ses_utility, EmailRequest, EmailRecipient

@pytest.mark.asyncio
async def test_send_simple_email():
    ses_utility = create_ses_utility()

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email="test@example.com")],
        from_email="noreply@yourdomain.com",
        subject="Test Email",
        html_content="<p>Test content</p>"
    )

    response = await ses_utility.send_email(email_request)

    assert response.success
    assert response.message_id is not None
    assert response.tracking_id is not None
```

## Troubleshooting

### Common Issues

1. **"AWS credentials not found"**

   - Ensure AWS credentials are properly configured
   - Check environment variables or AWS credentials file
   - Verify IAM permissions

2. **"Email address not verified"**

   - Verify sender email address in SES console
   - Check if domain is verified
   - Ensure you're not in sandbox mode for production

3. **"MessageRejected"**

   - Check email content for spam indicators
   - Verify email formatting is correct
   - Ensure attachments are not too large

4. **"SendingQuotaExceeded"**

   - Check your SES sending quota
   - Request quota increase if needed
   - Implement rate limiting

5. **"ConfigurationSetDoesNotExist"**
   - Create the configuration set first
   - Check the configuration set name
   - Verify region settings

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
```

## API Reference

### Classes

#### `SESEmailUtility`

Main utility class for email operations.

**Constructor Parameters:**

- `aws_access_key_id` (str, optional): AWS access key
- `aws_secret_access_key` (str, optional): AWS secret key
- `aws_region` (str): AWS region (default: "us-east-1")
- `configuration_set` (str, optional): Default SES configuration set
- `from_domain` (str, optional): Default from domain
- `procrastinate_app` (procrastinate.App, optional): Job queue app

**Methods:**

- `send_email(email_request, immediate=True)`: Send email immediately or schedule
- `send_template_email(to_recipients, template_name, template_data, ...)`: Send bulk template email
- `create_template(template_name, subject, html_content, text_content)`: Create SES template
- `get_account_info()`: Get SES account information
- `verify_domain_identity(domain)`: Verify domain in SES
- `create_configuration_set(name, tracking_options)`: Create configuration set

#### `EmailRequest`

Email request model with all email parameters.

**Fields:**

- `to_recipients` (List[EmailRecipient]): TO recipients
- `cc_recipients` (List[EmailRecipient], optional): CC recipients
- `bcc_recipients` (List[EmailRecipient], optional): BCC recipients
- `from_email` (EmailStr): Sender email
- `from_name` (str, optional): Sender name
- `reply_to` (List[EmailStr], optional): Reply-to addresses
- `subject` (str): Email subject
- `html_content` (str, optional): HTML content
- `text_content` (str, optional): Text content
- `template` (EmailTemplate, optional): Email template
- `template_context` (Dict[str, Any]): Template context data
- `attachments` (List[EmailAttachment], optional): File attachments
- `configuration_set` (str, optional): SES configuration set
- `message_tags` (Dict[str, str]): Message tags
- `tracking_id` (str, optional): Tracking ID (auto-generated)
- `campaign_id` (str, optional): Campaign ID
- `send_time` (datetime, optional): Scheduled send time
- `timezone` (str, optional): Timezone for scheduling
- `priority` (str): Priority level (low, normal, high)

#### `EmailRecipient`

Email recipient model.

**Fields:**

- `email` (EmailStr): Email address
- `name` (str, optional): Recipient name

**Methods:**

- `format_address()`: Format email address with name

#### `EmailTemplate`

Email template model for dynamic content.

**Fields:**

- `subject` (str): Subject template
- `html_content` (str, optional): HTML template
- `text_content` (str, optional): Text template
- `template_data` (Dict[str, Any]): Default template data

**Methods:**

- `render(context)`: Render template with context

#### `EmailAttachment`

Email attachment model.

**Fields:**

- `filename` (str): Attachment filename
- `content` (bytes): File content
- `content_type` (str, optional): MIME type (auto-detected)
- `disposition` (str): Disposition (attachment/inline)
- `content_id` (str, optional): Content ID for inline images

#### `EmailResponse`

Email sending response model.

**Fields:**

- `success` (bool): Whether email was sent successfully
- `message_id` (str, optional): SES message ID
- `tracking_id` (str): Unique tracking ID
- `error_message` (str, optional): Error message if failed
- `error_code` (str, optional): Error code if failed
- `timestamp` (datetime): Response timestamp
- `delivery_status` (str): Delivery status (sent, scheduled, failed, queued)

### Helper Functions

#### `create_ses_utility(...)`

Factory function to create configured SES utility instance.

#### `send_welcome_email(user_email, user_name, verification_token, ses_utility=None)`

Send welcome email with verification link.

#### `send_password_reset_email(user_email, user_name, reset_token, ses_utility=None)`

Send password reset email.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review AWS SES documentation
3. Check application logs for detailed error messages
4. Verify AWS credentials and permissions
5. Test with simple email first before complex scenarios

## License

This utility is part of your FastAPI application and follows the same license terms.
