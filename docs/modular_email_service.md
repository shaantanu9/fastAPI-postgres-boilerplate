# Modular Email Service Documentation

A comprehensive, scalable, and maintainable email service for AWS SES with modular architecture.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Modules](#modules)
7. [API Endpoints](#api-endpoints)
8. [Examples](#examples)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Overview

The Modular Email Service is a production-ready email system built for FastAPI applications. It provides a clean, modular architecture that separates concerns and makes the codebase maintainable and scalable.

### Key Features

- **🏗️ Modular Architecture**: Clean separation of concerns with dedicated modules
- **📧 Multiple Email Types**: Simple emails, templates, attachments, scheduling
- **👥 Multiple Recipients**: TO, CC, BCC support with proper formatting
- **📎 Attachment Support**: Files, PDFs, Excel, CSV with validation
- **⏰ Scheduled Emails**: Job queue integration with Procrastinate
- **🎨 Template Engine**: Jinja2 templating with dynamic content
- **📊 Email Tracking**: Unique tracking IDs and campaign analytics
- **🛡️ Error Handling**: Comprehensive error handling with specific codes
- **🔧 Helper Functions**: Pre-configured email types (welcome, password reset, etc.)
- **📈 Account Management**: SES account info, quotas, and domain verification

## Architecture

The service is organized into modular components:

```
app/services/email_service/
├── __init__.py           # Main service interface
├── models.py             # Pydantic models and data structures
├── client.py             # AWS SES client and account management
├── sender.py             # Core email sending functionality
├── attachments.py        # Attachment handling and validation
├── scheduler.py          # Scheduled email operations
└── helpers.py            # Pre-configured email helpers
```

### Component Overview

| Module              | Responsibility                               |
| ------------------- | -------------------------------------------- |
| `EmailService`      | Main interface and orchestration             |
| `SESClient`         | AWS SES client management and operations     |
| `EmailSender`       | Core email sending logic                     |
| `AttachmentHandler` | File attachment processing and validation    |
| `EmailScheduler`    | Scheduled email operations via Procrastinate |
| `Helper Functions`  | Pre-configured common email types            |

## Installation

1. **Install Dependencies**

   ```bash
   pip install boto3>=1.34.0 jinja2>=3.1.0 procrastinate>=2.0.0
   ```

2. **AWS SES Setup**

   - Verify your sending domain in AWS SES
   - Set up IAM permissions for SES access
   - Configure sandbox/production mode

3. **Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

## Configuration

Update your `app/core/config.py`:

```python
class Settings(BaseSettings):
    # AWS SES Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    SES_CONFIGURATION_SET: Optional[str] = None

    # Email Configuration
    EMAIL_FROM_DOMAIN: str = "yourapp.com"
    EMAIL_FROM_EMAIL: str = "noreply@yourapp.com"
    EMAIL_FROM_NAME: str = "Your App"
    EMAIL_PROVIDER: str = "aws_ses"

    # Application Settings
    APP_NAME: str = "Your Application"
    frontend_url: str = "https://yourapp.com"
    support_email: str = "support@yourapp.com"
```

## Usage

### Basic Usage

```python
from app.services.email_service import EmailService, create_email_service

# Create email service
email_service = create_email_service()

# Send simple email
response = await email_service.send_simple_email(
    to_email="user@example.com",
    subject="Hello World",
    html_content="<h1>Hello!</h1><p>Welcome to our service.</p>",
    text_content="Hello!\n\nWelcome to our service."
)

print(f"Email sent: {response.success}")
print(f"Tracking ID: {response.tracking_id}")
```

### Advanced Usage with EmailRequest

```python
from app.services.email_service import EmailService, EmailRequest, EmailRecipient

email_service = create_email_service()

# Create detailed email request
email_request = EmailRequest(
    to_recipients=[
        EmailRecipient(email="user1@example.com", name="John Doe"),
        EmailRecipient(email="user2@example.com", name="Jane Smith")
    ],
    cc_recipients=[EmailRecipient(email="manager@example.com", name="Manager")],
    from_email="updates@yourapp.com",
    from_name="Updates Team",
    subject="Monthly Newsletter",
    html_content="<h1>Newsletter</h1><p>This month's updates...</p>",
    message_tags={"type": "newsletter", "month": "january"},
    campaign_id="newsletter_2024_01"
)

response = await email_service.send_email(email_request)
```

## Modules

### 1. Models (`models.py`)

Core Pydantic models for type safety and validation:

- **`EmailRecipient`**: Email address with optional name
- **`EmailAttachment`**: File attachment with metadata
- **`EmailTemplate`**: Jinja2 template with dynamic content
- **`EmailRequest`**: Complete email request specification
- **`EmailResponse`**: Email sending result with tracking info
- **`EmailAccountInfo`**: SES account information and quotas

### 2. SES Client (`client.py`)

AWS SES client management:

```python
from app.services.email_service.client import SESClient, create_ses_client

# Create SES client
ses_client = create_ses_client()

# Get account information
account_info = await ses_client.get_account_info()

# Verify domain
success = await ses_client.verify_domain_identity("yourapp.com")

# Create configuration set
success = await ses_client.create_configuration_set("tracking-set")
```

### 3. Email Sender (`sender.py`)

Core email sending functionality:

```python
from app.services.email_service.sender import EmailSender

sender = EmailSender(ses_client)

# Send single email
response = await sender.send_email(email_request)

# Send bulk emails
responses = await sender.send_bulk_emails([email_request1, email_request2])

# Send template email
response = await sender.send_template_email(
    to_recipients=["user@example.com"],
    template_name="welcome-template",
    template_data={"user_name": "John"},
    from_email="welcome@yourapp.com"
)
```

### 4. Attachment Handler (`attachments.py`)

File attachment processing:

```python
from app.services.email_service.attachments import AttachmentHandler

handler = AttachmentHandler()

# Create attachment from file
attachment = handler.create_attachment_from_file("/path/to/file.pdf")

# Create attachment from bytes
attachment = handler.create_attachment_from_bytes(
    content=pdf_bytes,
    filename="report.pdf",
    content_type="application/pdf"
)

# Create specific attachment types
pdf_attachment = handler.create_pdf_attachment(pdf_bytes, "invoice.pdf")
csv_attachment = handler.create_csv_attachment("name,email\nJohn,john@example.com", "users.csv")
excel_attachment = handler.create_excel_attachment(excel_bytes, "data.xlsx")

# Validate attachments
is_valid, errors = handler.validate_attachments(attachments, max_size_mb=25)
```

### 5. Email Scheduler (`scheduler.py`)

Scheduled email operations with Procrastinate:

```python
from app.services.email_service.scheduler import EmailScheduler
import procrastinate

# Initialize with Procrastinate app
app = procrastinate.App(connector=procrastinate.AiopgConnector())
scheduler = EmailScheduler(app)

# Schedule email
response = await scheduler.schedule_email(email_request, send_time=future_datetime)

# Schedule bulk emails
responses = await scheduler.schedule_bulk_emails(email_requests, send_time=future_datetime)
```

### 6. Helper Functions (`helpers.py`)

Pre-configured email types:

```python
from app.services.email_service import EmailService

email_service = create_email_service()

# Welcome email with verification
response = await email_service.send_welcome_email(
    user_email="newuser@example.com",
    user_name="Alice Johnson",
    verification_token="token123"
)

# Password reset email
response = await email_service.send_password_reset_email(
    user_email="user@example.com",
    user_name="Bob Smith",
    reset_token="reset456"
)

# Notification email
response = await email_service.send_notification_email(
    user_email="user@example.com",
    user_name="Charlie Brown",
    subject="System Update",
    message="System maintenance scheduled for tonight.",
    priority="high"
)

# Invoice email with PDF
response = await email_service.send_invoice_email(
    customer_email="customer@example.com",
    customer_name="John Doe",
    invoice_number="INV-001",
    amount="$99.99",
    due_date="2024-02-15",
    pdf_content=invoice_pdf_bytes
)
```

## API Endpoints

The service includes FastAPI endpoints in `app/api/v1/endpoints/email_integration.py`:

### Core Endpoints

- **`POST /email/send`** - Send immediate email
- **`POST /email/send-simple`** - Send simple email with basic params
- **`POST /email/send-template`** - Send email using SES template
- **`POST /email/schedule`** - Schedule email for later delivery
- **`POST /email/send-with-attachments`** - Send email with file uploads

### Helper Endpoints

- **`POST /email/welcome`** - Send welcome email
- **`POST /email/password-reset`** - Send password reset email
- **`POST /email/notification`** - Send notification email

### Management Endpoints

- **`GET /email/account-info`** - Get SES account information
- **`POST /email/verify-domain/{domain}`** - Verify domain identity
- **`POST /email/create-configuration-set/{name}`** - Create configuration set
- **`GET /email/templates`** - List SES templates
- **`POST /email/test-email`** - Test email functionality

### Example API Usage

```bash
# Send simple email
curl -X POST "http://localhost:8000/api/v1/email/send-simple" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "to_email=user@example.com&subject=Hello&html_content=<h1>Hello World</h1>"

# Send welcome email
curl -X POST "http://localhost:8000/api/v1/email/welcome" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "newuser@example.com",
    "user_name": "Alice Johnson",
    "verification_token": "token123"
  }'

# Upload and send attachments
curl -X POST "http://localhost:8000/api/v1/email/send-with-attachments" \
  -F "to_emails=user@example.com" \
  -F "subject=File Attached" \
  -F "html_content=<p>Please find attached file.</p>" \
  -F "files=@/path/to/file.pdf"
```

## Examples

### Template Email with Dynamic Content

```python
from app.services.email_service import EmailService, EmailTemplate, EmailRequest, EmailRecipient

email_service = create_email_service()

# Create dynamic template
template = EmailTemplate(
    subject="Welcome {{ user_name }} to {{ app_name }}!",
    html_content="""
    <h1>Welcome {{ user_name }}!</h1>
    <p>Your account details:</p>
    <ul>
        <li>Username: {{ username }}</li>
        <li>Plan: {{ plan_type }}</li>
        <li>Registration: {{ registration_date }}</li>
    </ul>
    <a href="{{ dashboard_url }}">Go to Dashboard</a>
    """,
    template_data={
        "user_name": "John Doe",
        "app_name": "AwesomeApp",
        "username": "johndoe",
        "plan_type": "Premium",
        "registration_date": "2024-01-15",
        "dashboard_url": "https://app.example.com/dashboard"
    }
)

email_request = EmailRequest(
    to_recipients=[EmailRecipient(email="john@example.com", name="John Doe")],
    from_email="welcome@example.com",
    template=template
)

response = await email_service.send_email(email_request)
```

### Bulk Email Campaign

```python
# Send personalized emails to multiple users
users = [
    {"email": "user1@example.com", "name": "Alice", "plan": "Basic"},
    {"email": "user2@example.com", "name": "Bob", "plan": "Premium"},
    {"email": "user3@example.com", "name": "Charlie", "plan": "Enterprise"}
]

email_requests = []
for user in users:
    template = EmailTemplate(
        subject=f"Your {user['plan']} Plan Benefits",
        html_content=f"<h1>Hi {user['name']}!</h1><p>Enjoy your {user['plan']} benefits...</p>",
        template_data=user
    )

    email_request = EmailRequest(
        to_recipients=[EmailRecipient(email=user["email"], name=user["name"])],
        from_email="campaigns@example.com",
        template=template,
        message_tags={"campaign": "plan_benefits", "plan": user["plan"].lower()}
    )
    email_requests.append(email_request)

# Send all emails
responses = await email_service.send_bulk_emails(email_requests)
successful_sends = [r for r in responses if r.success]
print(f"Sent {len(successful_sends)}/{len(responses)} emails successfully")
```

### Scheduled Email with Attachments

```python
from datetime import datetime, timedelta

# Schedule report email for next Monday at 9 AM
send_time = datetime.utcnow().replace(hour=9, minute=0) + timedelta(days=7)

# Create report attachment
report_csv = "Date,Users,Revenue\n2024-01-01,100,$1000\n2024-01-02,110,$1100"
csv_attachment = email_service.create_csv_attachment(report_csv, "weekly_report.csv")

email_request = EmailRequest(
    to_recipients=[EmailRecipient(email="manager@example.com", name="Manager")],
    from_email="reports@example.com",
    subject="Weekly Report - Automated",
    html_content="<h1>Weekly Report</h1><p>Please find attached this week's report.</p>",
    attachments=[csv_attachment],
    send_time=send_time,
    message_tags={"type": "automated_report", "frequency": "weekly"}
)

# Schedule the email
response = await email_service.schedule_email(email_request)
print(f"Report scheduled for {send_time}: {response.success}")
```

## Best Practices

### 1. Error Handling

```python
try:
    response = await email_service.send_email(email_request)
    if response.success:
        logger.info(f"Email sent successfully: {response.tracking_id}")
    else:
        logger.error(f"Email failed: {response.error_message}")
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
```

### 2. Template Organization

```python
# Store templates in dedicated files
TEMPLATES_DIR = Path("app/templates/email")

def load_email_template(template_name: str) -> EmailTemplate:
    template_path = TEMPLATES_DIR / f"{template_name}.html"
    with open(template_path) as f:
        html_content = f.read()

    return EmailTemplate(
        subject=f"{{{{ subject }}}}",
        html_content=html_content,
        template_data={}
    )
```

### 3. Attachment Validation

```python
# Validate attachments before sending
attachments = [pdf_attachment, csv_attachment]
is_valid, errors = email_service.attachment_handler.validate_attachments(
    attachments,
    max_size_mb=25,
    allowed_types=["application/pdf", "text/csv", "application/vnd.ms-excel"]
)

if not is_valid:
    raise ValueError(f"Attachment validation failed: {'; '.join(errors)}")
```

### 4. Environment-Specific Configuration

```python
# Use different configurations for different environments
class EmailConfig:
    def __init__(self, environment: str):
        if environment == "production":
            self.from_email = "noreply@yourapp.com"
            self.configuration_set = "production-tracking"
        elif environment == "staging":
            self.from_email = "staging@yourapp.com"
            self.configuration_set = "staging-tracking"
        else:
            self.from_email = "dev@yourapp.com"
            self.configuration_set = None
```

### 5. Monitoring and Logging

```python
import structlog

logger = structlog.get_logger()

async def send_tracked_email(email_request: EmailRequest):
    start_time = datetime.utcnow()

    try:
        response = await email_service.send_email(email_request)

        logger.info(
            "email_sent",
            tracking_id=response.tracking_id,
            success=response.success,
            duration=(datetime.utcnow() - start_time).total_seconds(),
            recipient_count=len(email_request.to_recipients),
            has_attachments=bool(email_request.attachments)
        )

        return response

    except Exception as e:
        logger.error(
            "email_send_failed",
            error=str(e),
            duration=(datetime.utcnow() - start_time).total_seconds()
        )
        raise
```

## Troubleshooting

### Common Issues

1. **ImportError: cannot import name 'settings'**

   ```python
   # Ensure settings is properly exported in config.py
   @lru_cache
   def get_settings():
       return Settings()

   settings = get_settings()  # Add this line
   ```

2. **AWS Credentials Not Found**

   ```bash
   # Set environment variables
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"

   # Or use AWS credentials file
   aws configure
   ```

3. **SES Sandbox Limitations**

   - Verify recipient email addresses in SES console
   - Request production access to send to unverified addresses

4. **Attachment Size Limits**

   - Individual attachment: 10MB max
   - Total email size: 40MB max
   - Use attachment validation to check limits

5. **Template Rendering Errors**
   ```python
   # Validate template data before sending
   try:
       rendered_subject, html_content, text_content = email_request.get_rendered_content()
   except Exception as e:
       logger.error(f"Template rendering failed: {str(e)}")
       raise
   ```

### Debug Mode

Enable debug logging for detailed information:

```python
import logging

# Enable debug logging for email service
logging.getLogger("app.services.email_service").setLevel(logging.DEBUG)

# Enable boto3 debug logging
logging.getLogger("boto3").setLevel(logging.DEBUG)
logging.getLogger("botocore").setLevel(logging.DEBUG)
```

### Testing

```python
# Test email service with mock SES
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_email_service():
    service = EmailService()
    service.ses_client.ses_client = AsyncMock()
    service.ses_client.ses_v1_client = AsyncMock()
    return service

async def test_send_simple_email(mock_email_service):
    mock_email_service.ses_client.ses_client.send_email.return_value = {
        'MessageId': 'test-message-id'
    }

    response = await mock_email_service.send_simple_email(
        to_email="test@example.com",
        subject="Test",
        html_content="<p>Test</p>"
    )

    assert response.success
    assert response.message_id == 'test-message-id'
```

## Performance Considerations

### 1. Connection Pooling

```python
# Use session for connection reuse
import boto3
from botocore.config import Config

config = Config(
    max_pool_connections=50,
    retries={'max_attempts': 3}
)

session = boto3.Session()
ses_client = session.client('sesv2', config=config)
```

### 2. Async Operations

```python
# Use asyncio.gather for concurrent operations
import asyncio

async def send_multiple_emails_concurrently(email_requests):
    tasks = [
        email_service.send_email(request)
        for request in email_requests
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)
    return responses
```

### 3. Caching Templates

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_template(template_name: str) -> str:
    # Load and cache email templates
    with open(f"templates/{template_name}.html") as f:
        return f.read()
```

## Contributing

1. **Code Style**: Follow PEP 8 and use type hints
2. **Testing**: Add tests for new functionality
3. **Documentation**: Update docs for new features
4. **Error Handling**: Include proper error handling and logging
5. **Backwards Compatibility**: Maintain API compatibility when possible

## License

This email service is part of your FastAPI application. Use according to your project's license terms.
