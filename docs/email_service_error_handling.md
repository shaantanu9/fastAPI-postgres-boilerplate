# Email Service Error Handling & Debugging Guide

This guide covers the comprehensive error handling and debugging features implemented in the modular email service.

## Table of Contents

1. [Overview](#overview)
2. [Error Handling Architecture](#error-handling-architecture)
3. [Custom Exceptions](#custom-exceptions)
4. [Debugging Endpoints](#debugging-endpoints)
5. [Common Error Scenarios](#common-error-scenarios)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Logging and Monitoring](#logging-and-monitoring)

## Overview

The email service now includes robust error handling and debugging capabilities designed to:

- **Prevent application crashes** during startup when AWS credentials are missing
- **Provide clear error messages** for developers and users
- **Enable graceful degradation** when services are unavailable
- **Offer comprehensive debugging tools** for configuration issues
- **Support development environments** without requiring AWS setup

## Error Handling Architecture

### Lazy Initialization

The email service uses lazy initialization to prevent startup crashes:

```python
# Service initializes without validating AWS connection
email_service = create_email_service(validate_aws_connection=False)

# Connection is only validated when first used
response = await email_service.send_email(email_request)
```

### Error Hierarchy

```
Exception
├── EmailServiceError (Main service errors)
├── SESClientError (AWS SES client errors)
├── EmailSenderError (Email sending errors)
└── HTTPException (API layer errors)
```

### Graceful Degradation

- **Startup**: Application starts successfully even without AWS credentials
- **Runtime**: Clear error messages when attempting to use unconfigured services
- **Health Checks**: Service status available through health endpoints

## Custom Exceptions

### EmailServiceError

Main exception for email service operations with detailed error context:

```python
try:
    response = await email_service.send_email(email_request)
except EmailServiceError as e:
    # Handle email service specific errors
    logger.error(f"Email service error: {str(e)}")
```

### SESClientError

AWS SES client specific errors with AWS error code mapping:

```python
try:
    account_info = await ses_client.get_account_info()
except SESClientError as e:
    # Handle SES client errors with specific AWS error codes
    if "credentials" in str(e).lower():
        # Handle credentials error
        pass
```

### EmailSenderError

Email sending operation errors with validation details:

```python
try:
    response = await sender.send_email(email_request)
except EmailSenderError as e:
    # Handle sending errors (validation, attachment issues, etc.)
    logger.error(f"Email sending error: {str(e)}")
```

## Debugging Endpoints

### Health Check Endpoint

**GET** `/api/v1/email/health`

Returns comprehensive health status of all email service components:

```json
{
  "status": "healthy|degraded|unhealthy",
  "details": {
    "service_initialized": true,
    "initialization_error": null,
    "ses_client": {
      "initialized": false,
      "region": "us-east-1",
      "configuration_set": null,
      "from_domain": null,
      "error": null,
      "connection": "not_connected|healthy|unhealthy"
    },
    "sender": { "status": "ready|not_initialized" },
    "scheduler": { "status": "ready|no_procrastinate_app|not_initialized" }
  },
  "timestamp": "2025-01-01T00:00:00Z"
}
```

**Status Meanings:**

- `healthy`: All components working correctly
- `degraded`: Service functional but some features unavailable
- `unhealthy`: Service not functional

### Configuration Status

**GET** `/api/v1/email/config/status`

Quick configuration validation with actionable recommendations:

```json
{
  "status": "ready|needs_configuration|error",
  "ready": false,
  "issues_count": 1,
  "issues": ["AWS credentials not configured in environment variables"],
  "recommendations": [
    "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
  ],
  "timestamp": "2025-01-01T00:00:00Z"
}
```

### Configuration Debug

**GET** `/api/v1/email/config/debug`

Detailed configuration information for debugging:

```json
{
  "configuration": {
    "aws_access_key_configured": false,
    "aws_secret_key_configured": false,
    "aws_region": "us-east-1",
    "email_from_email": "noreply@yourapp.com",
    "email_from_name": "Your App",
    "email_provider": "ses",
    "ses_configuration_set": null,
    "email_from_domain": null,
    "environment_variables_set": {
      "AWS_ACCESS_KEY_ID": false,
      "AWS_SECRET_ACCESS_KEY": false,
      "AWS_REGION": false,
      "EMAIL_FROM_EMAIL": false,
      "EMAIL_FROM_NAME": false
    }
  },
  "validation": {
    "aws_credentials_configured": false,
    "aws_region_configured": true,
    "email_settings_configured": true,
    "issues": ["AWS credentials not configured"],
    "recommendations": ["Set AWS credentials"],
    "is_valid": false
  }
}
```

## Common Error Scenarios

### 1. AWS Credentials Not Configured

**Error Message:**

```
"AWS credentials not configured. Please configure AWS credentials to use email functionality."
```

**Solution:**

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

**API Response:**

```json
{
  "detail": "AWS credentials not configured. Please configure AWS credentials to use email functionality."
}
```

### 2. SES Access Denied

**Error Message:**

```
"AWS SES access denied. Please check IAM permissions for SES operations."
```

**Solution:**

- Verify IAM user has SES permissions
- Check SES service availability in the region
- Ensure SES is not in sandbox mode for production emails

### 3. Invalid Email Addresses

**Error Message:**

```
"Invalid email address: invalid-email"
```

**Solution:**

- Validate email format before sending
- Ensure all recipients have valid email addresses
- Check for typos in email addresses

### 4. Template Not Found

**Error Message:**

```
"Template 'template-name' does not exist"
```

**Solution:**

- Create the template in AWS SES console
- Verify template name spelling
- Check template exists in the correct AWS region

### 5. Attachment Too Large

**Error Message:**

```
"Attachment validation failed: Total attachment size 30.5MB exceeds 25MB limit"
```

**Solution:**

- Reduce attachment sizes
- Split large attachments across multiple emails
- Use file hosting and send links instead

## Troubleshooting Guide

### Step 1: Check Service Health

```bash
curl http://localhost:8000/api/v1/email/health
```

### Step 2: Validate Configuration

```bash
curl http://localhost:8000/api/v1/email/config/status
```

### Step 3: Get Debug Information

```bash
curl http://localhost:8000/api/v1/email/config/debug
```

### Step 4: Test Email Functionality

```bash
curl -X POST http://localhost:8000/api/v1/email/test-email
```

### Common Configuration Issues

#### Missing AWS Credentials

**Check:**

```bash
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
```

**Fix:**

```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

#### AWS Region Issues

**Check current region:**

```bash
aws configure get region
```

**Set region:**

```bash
export AWS_REGION="us-east-1"
```

#### SES Sandbox Mode

**Issue:** Can only send to verified email addresses

**Check status:**

```bash
aws ses get-send-quota
```

**Solution:** Request production access in AWS console

### Development Environment Setup

For development without AWS credentials:

1. **Use Mock Service:**

```python
# For testing without AWS
email_service = create_email_service(validate_aws_connection=False)
```

2. **Check Service Status:**

```python
health = email_service.get_health_status()
print(f"Service ready: {health['service_initialized']}")
```

3. **Handle Errors Gracefully:**

```python
try:
    response = await email_service.send_email(request)
    if not response.success:
        print(f"Email failed: {response.error_message}")
except EmailServiceError as e:
    print(f"Configuration issue: {str(e)}")
```

## Logging and Monitoring

### Log Levels

The service uses structured logging with different levels:

- **DEBUG**: Detailed operation information
- **INFO**: Important service events
- **WARNING**: Non-critical issues
- **ERROR**: Operation failures

### Log Examples

```python
# Service initialization
logger.info("Email Service initialized successfully")

# Email sending
logger.debug(f"Sending email with tracking ID: {tracking_id}")
logger.info(f"Email sent successfully: {tracking_id}")

# Errors
logger.error(f"SES client error: {error_message}")
logger.warning(f"Attachment validation warning: {warning}")
```

### Monitoring Endpoints

Monitor these endpoints for service health:

1. **`/api/v1/email/health`** - Overall service health
2. **`/api/v1/email/config/status`** - Configuration status
3. **Application logs** - Detailed error information

### Production Monitoring

Set up alerts for:

- Service health status changes
- High error rates in email sending
- AWS quota limits approaching
- Configuration validation failures

## Error Response Format

All API endpoints return consistent error responses:

```json
{
  "success": false,
  "tracking_id": "uuid",
  "error_message": "Detailed error description",
  "error_code": "AWS_ERROR_CODE",
  "timestamp": "2025-01-01T00:00:00Z",
  "delivery_status": "failed"
}
```

For API errors:

```json
{
  "detail": "HTTP error description"
}
```

## Best Practices

### Error Handling

1. **Always check response status:**

```python
response = await email_service.send_email(request)
if not response.success:
    handle_error(response.error_message)
```

2. **Use specific exception handling:**

```python
try:
    response = await email_service.send_email(request)
except EmailServiceError as e:
    # Handle service configuration issues
    pass
except Exception as e:
    # Handle unexpected errors
    pass
```

3. **Implement retry logic for transient errors:**

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def send_email_with_retry(email_request):
    return await email_service.send_email(email_request)
```

### Development

1. **Use health checks in development:**

```python
health = email_service.get_health_status()
if not health["service_initialized"]:
    print("Email service not properly configured")
```

2. **Validate configuration before deployment:**

```python
from app.core.config import validate_aws_configuration

validation = validate_aws_configuration()
if not validation["is_valid"]:
    print(f"Configuration issues: {validation['issues']}")
```

3. **Enable debug logging:**

```python
import logging
logging.getLogger("app.services.email_service").setLevel(logging.DEBUG)
```

This comprehensive error handling system ensures that the email service is robust, debuggable, and provides clear feedback when issues occur.
