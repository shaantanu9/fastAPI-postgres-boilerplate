# 👥 SaaS User Management System - Complete Guide

## 🎯 Overview

This FastAPI SaaS boilerplate provides enterprise-grade user management with all the essential features for a production SaaS application:

### ✅ **Implemented Features**

- **User Registration** with email verification
- **Password Reset** flow with secure tokens
- **User Invitations** for team management
- **Profile Management** with security controls
- **Multi-Factor Authentication (MFA)** with TOTP
- **Session Management** with device tracking
- **Role-Based Access Control (RBAC)** with permissions
- **Security Event Logging** for audit trails
- **Email Service** with beautiful templates
- **Account Management** (deactivation, reactivation)

---

## 📋 **Table of Contents**

1. [Quick Setup](#quick-setup)
2. [User Registration Flow](#user-registration-flow)
3. [Authentication System](#authentication-system)
4. [Email Verification](#email-verification)
5. [Password Reset](#password-reset)
6. [User Invitations](#user-invitations)
7. [Profile Management](#profile-management)
8. [Role-Based Access Control](#role-based-access-control)
9. [Session Management](#session-management)
10. [Security Features](#security-features)
11. [API Reference](#api-reference)
12. [Configuration](#configuration)

---

## 🚀 Quick Setup

### 1. Configure Email Settings

Update your `.env` file:

```env
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@yourapp.com
SMTP_FROM_NAME=Your SaaS App
EMAIL_SECRET_KEY=your-secret-email-key-change-this

# Frontend URLs
FRONTEND_URL=http://localhost:3000
SUPPORT_EMAIL=support@yourapp.com
APP_NAME=Your SaaS App
```

### 2. Install Dependencies

```bash
pip install aiosmtplib jinja2
```

### 3. Run Database Migrations

```bash
alembic upgrade head
```

### 4. Seed Default Roles & Permissions

```bash
python app/scripts/seed_rbac.py
```

### 5. Create First Admin User

```python
# Uncomment and run the admin creation in seed_rbac.py
asyncio.run(create_first_admin_user(
    username="admin",
    email="admin@yourapp.com",
    password="AdminPassword123!",
    first_name="System",
    last_name="Administrator"
))
```

---

## 📝 User Registration Flow

### Standard Registration

**Endpoint:** `POST /api/v1/auth/register`

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePassword123!"
}
```

**Response:**

```json
{
  "id": "user-uuid",
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-06-01T10:00:00Z"
}
```

**What Happens:**

1. User data is validated
2. Password strength is checked
3. User account is created (unverified)
4. Verification email is sent automatically
5. Default "user" role is assigned
6. Security event is logged

---

## 📧 Email Verification

### Send Verification Email

**Endpoint:** `POST /api/v1/user-management/send-verification-email`

```json
{
  "email": "john@example.com"
}
```

### Verify Email

**Endpoint:** `POST /api/v1/user-management/verify-email`

```json
{
  "token": "verification-token-from-email",
  "user_id": "user-uuid"
}
```

**Email Templates:**

- Professional HTML templates included
- Customizable branding
- Mobile-responsive design
- Security warnings

---

## 🔐 Password Reset

### Request Password Reset

**Endpoint:** `POST /api/v1/user-management/forgot-password`

```json
{
  "email": "john@example.com"
}
```

### Reset Password

**Endpoint:** `POST /api/v1/user-management/reset-password`

```json
{
  "user_id": "user-uuid",
  "token": "reset-token-from-email",
  "new_password": "NewSecurePassword123!"
}
```

**Features:**

- Secure token generation
- 1-hour expiration
- Password strength validation
- Notification emails
- Account security logging

---

## 📨 User Invitations

### Invite New User

**Endpoint:** `POST /api/v1/user-management/invite-user`

```json
{
  "email": "newuser@example.com",
  "organization_name": "Acme Corp",
  "role": "user"
}
```

**Features:**

- Email invitation with branded template
- Organization context
- Role pre-assignment
- Invitation tracking
- Expiration handling

---

## 👤 Profile Management

### Get User Profile

**Endpoint:** `GET /api/v1/user-management/profile`

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/user-management/profile
```

### Update Profile

**Endpoint:** `PUT /api/v1/user-management/profile`

```json
{
  "first_name": "John",
  "last_name": "Smith",
  "username": "johnsmith"
}
```

### Change Password

**Endpoint:** `POST /api/v1/user-management/change-password`

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword123!"
}
```

---

## 🛡️ Role-Based Access Control (RBAC)

### Default Roles

| Role            | Description        | Permissions                         |
| --------------- | ------------------ | ----------------------------------- |
| **super_admin** | Full system access | All permissions                     |
| **admin**       | Organization admin | User management, billing, analytics |
| **manager**     | Team manager       | Limited admin access                |
| **user**        | Standard user      | Basic access                        |
| **viewer**      | Read-only          | View-only access                    |

### Permission Categories

```python
# User Management
"users.create", "users.read", "users.update", "users.delete", "users.invite"

# Organization
"organization.read", "organization.update", "organization.manage"

# Files
"files.upload", "files.download", "files.delete", "files.manage"

# API Access
"api.read", "api.write", "api.admin"

# Billing (SaaS)
"billing.read", "billing.manage"

# System
"system.admin", "system.monitoring"
```

### Check User Permissions

```python
from app.services.user_service import enhanced_user_service

# Get user permissions
permissions = await enhanced_user_service.get_user_permissions(db, user_id)

# Check specific permission
has_permission = any(p.name == "users.create" for p in permissions)
```

---

## 🖥️ Session Management

### View Active Sessions

**Endpoint:** `GET /api/v1/user-management/sessions`

```json
{
  "sessions": [
    {
      "id": "session-uuid",
      "ip_address": "192.168.1.100",
      "user_agent": "Chrome/91.0.4472.124",
      "created_at": "2025-06-01T10:00:00Z",
      "last_activity": "2025-06-01T11:30:00Z",
      "expires_at": "2025-07-01T10:00:00Z"
    }
  ]
}
```

### Terminate Session

**Endpoint:** `DELETE /api/v1/user-management/sessions/{session_id}`

### Terminate All Sessions

**Endpoint:** `DELETE /api/v1/user-management/sessions/all`

**Features:**

- Device fingerprinting
- IP tracking
- Session limits per user
- Automatic cleanup
- Security monitoring

---

## 🔒 Security Features

### Multi-Factor Authentication (MFA)

#### Enable MFA

**Endpoint:** `POST /api/v1/user-management/mfa/enable`

```json
{
  "message": "MFA setup initiated",
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAA...",
  "backup_codes": ["12345678", "87654321", ...]
}
```

#### Verify MFA Setup

**Endpoint:** `POST /api/v1/user-management/mfa/verify-setup`

```json
{
  "token": "123456"
}
```

### Security Events

**Endpoint:** `GET /api/v1/user-management/security-events`

```json
{
  "events": [
    {
      "id": "event-uuid",
      "event_type": "successful_login",
      "event_category": "authentication",
      "ip_address": "192.168.1.100",
      "risk_score": 0,
      "status": "success",
      "created_at": "2025-06-01T10:00:00Z"
    }
  ]
}
```

**Tracked Events:**

- Login attempts (success/failure)
- Password changes
- Account lockouts
- MFA events
- Profile updates
- Session activities

---

## 📚 API Reference

### Authentication Endpoints

| Method | Endpoint                | Description          |
| ------ | ----------------------- | -------------------- |
| POST   | `/api/v1/auth/register` | Register new user    |
| POST   | `/api/v1/auth/login`    | User login           |
| POST   | `/api/v1/auth/refresh`  | Refresh access token |
| POST   | `/api/v1/auth/logout`   | User logout          |
| GET    | `/api/v1/auth/me`       | Get current user     |

### User Management Endpoints

| Method | Endpoint                                          | Description             |
| ------ | ------------------------------------------------- | ----------------------- |
| POST   | `/api/v1/user-management/send-verification-email` | Send verification email |
| POST   | `/api/v1/user-management/verify-email`            | Verify email address    |
| POST   | `/api/v1/user-management/forgot-password`         | Request password reset  |
| POST   | `/api/v1/user-management/reset-password`          | Reset password          |
| POST   | `/api/v1/user-management/invite-user`             | Invite new user         |
| GET    | `/api/v1/user-management/profile`                 | Get user profile        |
| PUT    | `/api/v1/user-management/profile`                 | Update profile          |
| POST   | `/api/v1/user-management/change-password`         | Change password         |
| GET    | `/api/v1/user-management/sessions`                | View sessions           |
| DELETE | `/api/v1/user-management/sessions/{id}`           | Terminate session       |
| POST   | `/api/v1/user-management/mfa/enable`              | Enable MFA              |
| GET    | `/api/v1/user-management/security-events`         | View security events    |

---

## ⚙️ Configuration

### Email Provider Setup

#### Gmail Setup

1. Enable 2-Factor Authentication
2. Generate App Password
3. Use in SMTP_PASSWORD

#### SendGrid Setup

```env
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

#### AWS SES Setup

```env
SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-aws-access-key
SMTP_PASSWORD=your-aws-secret-key
```

### Security Configuration

```python
# Password Policy
MIN_PASSWORD_LENGTH = 12
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL_CHARS = True

# Account Lockout
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 30  # minutes

# Session Management
MAX_SESSIONS_PER_USER = 5
SESSION_LIFETIME = 30  # days
ACCESS_TOKEN_LIFETIME = 15  # minutes
```

---

## 🔧 Customization

### Email Templates

Templates are stored in `app/templates/emails/`:

- `verification.html` - Email verification
- `password_reset.html` - Password reset
- `invitation.html` - User invitations
- `welcome.html` - Welcome email
- `password_changed.html` - Password change notification

### Custom Roles

```python
# Add custom role
custom_role = {
    "name": "customer_support",
    "description": "Customer support representative",
    "permissions": [
        "users.read", "users.update",
        "organization.read",
        "api.read"
    ]
}
```

### Custom Permissions

```python
# Add custom permission
custom_permission = {
    "name": "tickets.manage",
    "resource": "tickets",
    "action": "manage",
    "description": "Manage support tickets"
}
```

---

## 📊 Production Considerations

### Performance

- Use Redis for session storage
- Implement connection pooling
- Add database indexing
- Use background tasks for emails

### Security

- Enable HTTPS only
- Implement rate limiting
- Add CSRF protection
- Use secure headers

### Monitoring

- Track user metrics
- Monitor security events
- Alert on suspicious activity
- Log authentication failures

### Scalability

- Database read replicas
- Email queue system
- Distributed sessions
- Load balancer setup

---

## 🎉 **Success!**

You now have a complete SaaS user management system with:

✅ **User Registration & Verification**  
✅ **Password Reset & Security**  
✅ **User Invitations & Onboarding**  
✅ **Profile & Session Management**  
✅ **Role-Based Access Control**  
✅ **Multi-Factor Authentication**  
✅ **Security Event Logging**  
✅ **Email Service Integration**

Your SaaS boilerplate is now production-ready for user management! 🚀

---

## 📞 Support

For questions or issues:

- Create GitHub issues
- Check the API documentation at `/docs`
- Review security logs for troubleshooting
- Test email delivery in development mode
