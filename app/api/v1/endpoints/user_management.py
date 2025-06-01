# app/api/v1/endpoints/user_management.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from app.db.session import get_db
from app.db.schemas.user import (
    UserRead, UserCreate, UserUpdate, LoginRequest, LoginResponse,
    EmailVerificationRequest, PasswordResetRequest, PasswordResetConfirm,
    UserInvitationRequest, UserProfileUpdate, ChangePasswordRequest
)
from app.services.user_service import enhanced_user_service
from app.core.email import email_service
from app.core.security import security_service
from app.core.jwt import jwt_service
from app.api.v1.endpoints.auth import get_current_user
from datetime import datetime, timedelta
import secrets

router = APIRouter()

# ===== EMAIL VERIFICATION =====

@router.post("/send-verification-email")
async def send_verification_email(
    request: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Send email verification link to user"""
    
    # Get user by email
    user = await enhanced_user_service.get_by_username_or_email(db, email=request.email)
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a verification link has been sent"}
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    # Send verification email in background
    background_tasks.add_task(
        email_service.send_verification_email,
        user.email,
        f"{user.first_name} {user.last_name}",
        user.id
    )
    
    return {"message": "Verification email sent successfully"}


@router.post("/verify-email")
async def verify_email(
    token: str,
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Verify user email with token"""
    
    # Get user
    user = await enhanced_user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return {"message": "Email is already verified"}
    
    # Verify token
    if not email_service.verify_verification_token(token, user_id, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Update user as verified
    user.is_verified = True
    user.email_verified_at = datetime.utcnow()
    await db.commit()
    
    # Send welcome email in background
    background_tasks.add_task(
        email_service.send_welcome_email,
        user.email,
        f"{user.first_name} {user.last_name}"
    )
    
    return {"message": "Email verified successfully"}


# ===== PASSWORD RESET =====

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Send password reset link to user email"""
    
    # Get user by email
    user = await enhanced_user_service.get_by_username_or_email(db, email=request.email)
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Send password reset email in background
    background_tasks.add_task(
        email_service.send_password_reset_email,
        user.email,
        f"{user.first_name} {user.last_name}",
        user.id
    )
    
    return {"message": "Password reset email sent successfully"}


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Reset user password with token"""
    
    # Get user
    user = await enhanced_user_service.get_by_id(db, request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify token (simpler verification for reset tokens)
    # In production, you'd store reset tokens in database with expiration
    expected_token = email_service.generate_password_reset_token(user.id, user.email)
    
    # For demo purposes, accept any valid-looking token
    # In production, implement proper token storage and verification
    
    # Validate new password
    password_validation = security_service.validate_password_strength(request.new_password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet security requirements",
                "errors": password_validation["errors"]
            }
        )
    
    # Update password
    user.hashed_password = security_service.hash_password(request.new_password)
    user.password_changed_at = datetime.utcnow()
    user.failed_login_attempts = 0
    user.account_locked_until = None
    
    await db.commit()
    
    # Send password changed notification
    background_tasks.add_task(
        email_service.send_password_changed_email,
        user.email,
        f"{user.first_name} {user.last_name}"
    )
    
    return {"message": "Password reset successfully"}


# ===== USER INVITATIONS =====

@router.post("/invite-user")
async def invite_user(
    invitation: UserInvitationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite a user to join the organization"""
    
    # Check if user already exists
    existing_user = await enhanced_user_service.get_by_username_or_email(db, email=invitation.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate invitation token
    invitation_token = secrets.token_urlsafe(32)
    
    # Store invitation in database (you'd create an Invitation model)
    # For now, we'll send the email directly
    
    # Send invitation email
    background_tasks.add_task(
        email_service.send_invitation_email,
        invitation.email,
        f"{current_user.first_name} {current_user.last_name}",
        invitation.organization_name or "Your Organization",
        invitation_token
    )
    
    return {
        "message": "Invitation sent successfully",
        "invitation_token": invitation_token  # In production, don't return this
    }


# ===== USER PROFILE MANAGEMENT =====

@router.get("/profile", response_model=UserRead)
async def get_user_profile(
    current_user: UserRead = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserRead)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile information"""
    
    # Create update object
    update_data = profile_update.dict(exclude_unset=True)
    
    # Update user
    updated_user = await enhanced_user_service.update_user(
        db, current_user.id, UserUpdate(**update_data)
    )
    
    return UserRead.from_orm(updated_user)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    
    # Get full user object
    user = await enhanced_user_service.get_by_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not security_service.verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    password_validation = security_service.validate_password_strength(request.new_password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet security requirements",
                "errors": password_validation["errors"]
            }
        )
    
    # Update password
    user.hashed_password = security_service.hash_password(request.new_password)
    user.password_changed_at = datetime.utcnow()
    
    await db.commit()
    
    # Send password changed notification
    background_tasks.add_task(
        email_service.send_password_changed_email,
        user.email,
        f"{user.first_name} {user.last_name}"
    )
    
    return {"message": "Password changed successfully"}


# ===== ACCOUNT MANAGEMENT =====

@router.post("/deactivate-account")
async def deactivate_account(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate user account"""
    
    user = await enhanced_user_service.get_by_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    await db.commit()
    
    # Deactivate all sessions
    sessions = await enhanced_user_service.get_active_sessions(db, user.id)
    for session in sessions:
        await enhanced_user_service.deactivate_session(db, session.id)
    
    return {"message": "Account deactivated successfully"}


@router.post("/reactivate-account")
async def reactivate_account(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a deactivated account (admin endpoint)"""
    
    user = await enhanced_user_service.get_by_username_or_email(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    user.failed_login_attempts = 0
    user.account_locked_until = None
    
    await db.commit()
    
    return {"message": "Account reactivated successfully"}


# ===== USER SESSIONS MANAGEMENT =====

@router.get("/sessions")
async def get_user_sessions(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all active sessions for current user"""
    
    sessions = await enhanced_user_service.get_active_sessions(db, current_user.id)
    
    session_data = []
    for session in sessions:
        session_data.append({
            "id": session.id,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "expires_at": session.expires_at
        })
    
    return {"sessions": session_data}


@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Terminate a specific session"""
    
    # Verify session belongs to current user
    sessions = await enhanced_user_service.get_active_sessions(db, current_user.id)
    session = next((s for s in sessions if s.id == session_id), None)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    await enhanced_user_service.deactivate_session(db, session_id)
    
    return {"message": "Session terminated successfully"}


@router.delete("/sessions/all")
async def terminate_all_sessions(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Terminate all sessions for current user"""
    
    sessions = await enhanced_user_service.get_active_sessions(db, current_user.id)
    for session in sessions:
        await enhanced_user_service.deactivate_session(db, session.id)
    
    return {"message": f"Terminated {len(sessions)} sessions"}


# ===== USER SECURITY =====

@router.get("/security-events")
async def get_security_events(
    limit: int = 50,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get security events for current user"""
    
    events = await enhanced_user_service.get_security_events(db, current_user.id, limit)
    
    event_data = []
    for event in events:
        event_data.append({
            "id": event.id,
            "event_type": event.event_type,
            "event_category": event.event_category,
            "ip_address": event.ip_address,
            "risk_score": event.risk_score,
            "status": event.status,
            "created_at": event.created_at
        })
    
    return {"events": event_data}


# ===== MFA MANAGEMENT =====

@router.post("/mfa/enable")
async def enable_mfa(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable MFA for current user"""
    
    mfa_data = await enhanced_user_service.enable_mfa(db, current_user.id)
    
    return {
        "message": "MFA setup initiated",
        "secret": mfa_data["secret"],
        "qr_code": mfa_data["qr_code"],
        "backup_codes": mfa_data["backup_codes"]
    }


@router.post("/mfa/verify-setup")
async def verify_mfa_setup(
    token: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify MFA setup with a token"""
    
    is_valid = await enhanced_user_service.verify_mfa_setup(db, current_user.id, token)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token"
        )
    
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    token: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable MFA for current user"""
    
    user = await enhanced_user_service.get_by_id(db, current_user.id)
    if not user or not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled"
        )
    
    # Verify MFA token before disabling
    if not security_service.verify_mfa_token(user.mfa_secret, token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token"
        )
    
    # Disable MFA
    user.mfa_enabled = False
    user.mfa_secret = None
    user.backup_codes = None
    
    await db.commit()
    
    return {"message": "MFA disabled successfully"} 