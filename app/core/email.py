# app/core/email.py

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from pathlib import Path
import aiosmtplib
from jinja2 import Environment, FileSystemLoader, Template
import os
from app.core.config import get_settings
from loguru import logger
import secrets
import hashlib
from datetime import datetime, timedelta

settings = get_settings()

class EmailService:
    """Enterprise email service for user management workflows"""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.use_tls = settings.smtp_use_tls
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name
        
        # Setup Jinja2 for email templates
        self.template_dir = Path(__file__).parent.parent / "templates" / "emails"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates"""
        templates = {
            "verification.html": self._get_verification_template(),
            "password_reset.html": self._get_password_reset_template(),
            "invitation.html": self._get_invitation_template(),
            "welcome.html": self._get_welcome_template(),
            "password_changed.html": self._get_password_changed_template(),
        }
        
        for filename, content in templates.items():
            template_path = self.template_dir / filename
            if not template_path.exists():
                template_path.write_text(content)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send email using aiosmtplib for async operation"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {attachment['filename']}"
                    )
                    message.attach(part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=self.use_tls,
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def generate_verification_token(self, user_id: str, email: str) -> str:
        """Generate email verification token"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        data = f"{user_id}:{email}:{timestamp}:{settings.email_secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_verification_token(self, token: str, user_id: str, email: str, max_age_hours: int = 24) -> bool:
        """Verify email verification token"""
        try:
            # Generate expected token
            timestamp = str(int((datetime.utcnow() - timedelta(hours=max_age_hours)).timestamp()))
            for hour_offset in range(max_age_hours + 1):
                ts = str(int((datetime.utcnow() - timedelta(hours=hour_offset)).timestamp()))
                data = f"{user_id}:{email}:{ts}:{settings.email_secret_key}"
                expected_token = hashlib.sha256(data.encode()).hexdigest()
                if token == expected_token:
                    return True
            return False
        except Exception:
            return False
    
    def generate_password_reset_token(self, user_id: str, email: str) -> str:
        """Generate password reset token"""
        random_part = secrets.token_urlsafe(32)
        timestamp = str(int(datetime.utcnow().timestamp()))
        data = f"{user_id}:{email}:{timestamp}:{random_part}:{settings.email_secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def send_verification_email(self, user_email: str, user_name: str, user_id: str) -> bool:
        """Send email verification email"""
        try:
            verification_token = self.generate_verification_token(user_id, user_email)
            verification_link = f"{settings.frontend_url}/verify-email?token={verification_token}&user_id={user_id}"
            
            template = self.jinja_env.get_template("verification.html")
            html_content = template.render(
                user_name=user_name,
                verification_link=verification_link,
                app_name=settings.app_name,
                support_email=settings.support_email
            )
            
            subject = f"Verify your email address - {settings.app_name}"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            return False
    
    async def send_password_reset_email(self, user_email: str, user_name: str, user_id: str) -> bool:
        """Send password reset email"""
        try:
            reset_token = self.generate_password_reset_token(user_id, user_email)
            reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}&user_id={user_id}"
            
            template = self.jinja_env.get_template("password_reset.html")
            html_content = template.render(
                user_name=user_name,
                reset_link=reset_link,
                app_name=settings.app_name,
                support_email=settings.support_email
            )
            
            subject = f"Reset your password - {settings.app_name}"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False
    
    async def send_invitation_email(
        self, 
        invitee_email: str, 
        inviter_name: str, 
        organization_name: str,
        invitation_token: str
    ) -> bool:
        """Send user invitation email"""
        try:
            invitation_link = f"{settings.frontend_url}/accept-invitation?token={invitation_token}"
            
            template = self.jinja_env.get_template("invitation.html")
            html_content = template.render(
                inviter_name=inviter_name,
                organization_name=organization_name,
                invitation_link=invitation_link,
                app_name=settings.app_name,
                support_email=settings.support_email
            )
            
            subject = f"You're invited to join {organization_name} on {settings.app_name}"
            
            return await self.send_email(
                to_email=invitee_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send invitation email: {str(e)}")
            return False
    
    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email after successful verification"""
        try:
            template = self.jinja_env.get_template("welcome.html")
            html_content = template.render(
                user_name=user_name,
                app_name=settings.app_name,
                dashboard_url=f"{settings.frontend_url}/dashboard",
                support_email=settings.support_email
            )
            
            subject = f"Welcome to {settings.app_name}!"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            return False
    
    async def send_password_changed_email(self, user_email: str, user_name: str) -> bool:
        """Send notification when password is changed"""
        try:
            template = self.jinja_env.get_template("password_changed.html")
            html_content = template.render(
                user_name=user_name,
                app_name=settings.app_name,
                support_email=settings.support_email,
                timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            )
            
            subject = f"Password changed - {settings.app_name}"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send password changed email: {str(e)}")
            return False
    
    # Email template content methods
    def _get_verification_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #3498db; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Verify Your Email Address</h1>
    </div>
    <div class="content">
        <h2>Hello {{ user_name }}!</h2>
        <p>Thank you for signing up for {{ app_name }}. To complete your registration, please verify your email address by clicking the button below:</p>
        
        <a href="{{ verification_link }}" class="button">Verify Email Address</a>
        
        <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
        <p><a href="{{ verification_link }}">{{ verification_link }}</a></p>
        
        <p>This verification link will expire in 24 hours for security reasons.</p>
        
        <div class="footer">
            <p>If you didn't create an account with {{ app_name }}, you can safely ignore this email.</p>
            <p>Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_password_reset_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #e74c3c; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Password Reset Request</h1>
    </div>
    <div class="content">
        <h2>Hello {{ user_name }}!</h2>
        <p>We received a request to reset your password for your {{ app_name }} account. Click the button below to create a new password:</p>
        
        <a href="{{ reset_link }}" class="button">Reset Password</a>
        
        <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
        <p><a href="{{ reset_link }}">{{ reset_link }}</a></p>
        
        <p>This reset link will expire in 1 hour for security reasons.</p>
        
        <div class="footer">
            <p>If you didn't request a password reset, you can safely ignore this email. Your password won't be changed.</p>
            <p>Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_invitation_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You're Invited!</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #27ae60; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #27ae60; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>You're Invited!</h1>
    </div>
    <div class="content">
        <h2>Great news!</h2>
        <p>{{ inviter_name }} has invited you to join <strong>{{ organization_name }}</strong> on {{ app_name }}.</p>
        
        <p>Click the button below to accept the invitation and create your account:</p>
        
        <a href="{{ invitation_link }}" class="button">Accept Invitation</a>
        
        <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
        <p><a href="{{ invitation_link }}">{{ invitation_link }}</a></p>
        
        <p>This invitation will expire in 7 days.</p>
        
        <div class="footer">
            <p>If you don't know {{ inviter_name }} or weren't expecting this invitation, you can safely ignore this email.</p>
            <p>Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_welcome_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome!</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #3498db; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Welcome to {{ app_name }}!</h1>
    </div>
    <div class="content">
        <h2>Hello {{ user_name }}!</h2>
        <p>Your email has been successfully verified and your account is now active. Welcome to {{ app_name }}!</p>
        
        <p>You can now access all features of our platform. Get started by visiting your dashboard:</p>
        
        <a href="{{ dashboard_url }}" class="button">Go to Dashboard</a>
        
        <h3>What's next?</h3>
        <ul>
            <li>Complete your profile setup</li>
            <li>Explore our features and tools</li>
            <li>Connect with your team</li>
            <li>Start building amazing things</li>
        </ul>
        
        <div class="footer">
            <p>Thanks for joining {{ app_name }}! We're excited to have you on board.</p>
            <p>Need help getting started? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
        </div>
    </div>
</body>
</html>
        """
    
    def _get_password_changed_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Changed</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f39c12; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Password Changed</h1>
    </div>
    <div class="content">
        <h2>Hello {{ user_name }}!</h2>
        <p>This is a confirmation that your password for {{ app_name }} has been successfully changed on {{ timestamp }}.</p>
        
        <p>If you made this change, no further action is required.</p>
        
        <p><strong>If you did not make this change:</strong></p>
        <ul>
            <li>Your account may have been compromised</li>
            <li>Please contact our support team immediately</li>
            <li>Consider enabling two-factor authentication for additional security</li>
        </ul>
        
        <div class="footer">
            <p>For security reasons, we recommend regularly updating your password and enabling two-factor authentication.</p>
            <p>Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
        </div>
    </div>
</body>
</html>
        """


# Initialize email service
email_service = EmailService() 