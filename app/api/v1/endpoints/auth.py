from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.schemas.user import (
    UserCreate, UserRead, LoginRequest, LoginResponse, 
    RefreshTokenRequest, MFASetupResponse, MFAVerifyRequest,
    PasswordStrengthResponse, UserWithRoles, SecurityEventRead,
    UserSessionRead
)
from app.services.user_service import enhanced_user_service
from app.core.security import security_service
from app.core.jwt import jwt_service
from app.core.email import email_service
from datetime import datetime, timedelta
from typing import List
import json

router = APIRouter()


# Helper function to get current user
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> UserRead:
    """Get current authenticated user"""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt_service.verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = await enhanced_user_service.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Refresh user and convert to Pydantic model
        await db.refresh(user)
        return UserRead.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        # For debugging - show actual error
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user with enterprise security validation and email verification"""
    try:
        user = await enhanced_user_service.create_user(db, user_create)
        
        # Send verification email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            user.email,
            f"{user.first_name} {user.last_name}",
            user.id
        )
        
        # Log registration event
        security_service.log_security_event(
            db, user, "user_registration", "authentication",
            {"username": user.username, "email": user.email}, request
        )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Enhanced login with MFA support and session management"""
    try:
        # Authenticate user
        user = await enhanced_user_service.authenticate_user(
            db, login_data.username_or_email, login_data.password, request
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if MFA is required
        if user.mfa_enabled and not login_data.mfa_token:
            await db.refresh(user)
            user_data = UserRead.from_orm(user)
            return LoginResponse(
                access_token="",
                refresh_token="",
                expires_in=0,
                user=user_data,
                requires_mfa=True
            )
        
        # Verify MFA if provided
        if user.mfa_enabled and login_data.mfa_token:
            if not security_service.verify_mfa_token(user.mfa_secret, login_data.mfa_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA token"
                )
        
        # Create session
        session = await enhanced_user_service.create_session(db, user, request)
        
        # Generate tokens
        access_token = jwt_service.create_access_token(
            data={"sub": user.username, "user_id": user.id, "session_id": session.id}
        )
        refresh_token = jwt_service.create_refresh_token(user.id, session.id)
        
        # Update session with refresh token
        session.refresh_token = refresh_token
        await db.commit()
        
        # Refresh user to ensure all fields are loaded
        await db.refresh(user)
        
        # Convert SQLAlchemy User to Pydantic UserRead
        user_data = UserRead.from_orm(user)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_service.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_data,
            requires_mfa=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # For debugging - show actual error
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


# Legacy token endpoint for backward compatibility
@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Legacy token endpoint for backward compatibility"""
    login_data = LoginRequest(
        username_or_email=form_data.username,
        password=form_data.password
    )
    return await login(login_data, request, db)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = jwt_service.verify_token(refresh_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        
        if not user_id or not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user and session
        user = await enhanced_user_service.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Verify session is still active
        sessions = await enhanced_user_service.get_active_sessions(db, user_id)
        session = next((s for s in sessions if s.id == session_id), None)
        
        if not session or session.refresh_token != refresh_data.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Update session activity
        await enhanced_user_service.update_session_activity(db, session)
        
        # Generate new access token
        access_token = jwt_service.create_access_token(
            data={"sub": user.username, "user_id": user.id, "session_id": session.id}
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_data.refresh_token,
            expires_in=jwt_service.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
            requires_mfa=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout and invalidate session"""
    try:
        # Get session from token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = jwt_service.verify_token(token)
            session_id = payload.get("session_id")
            
            if session_id:
                await enhanced_user_service.deactivate_session(db, session_id)
                
                # Blacklist the token
                jti = payload.get("jti")
                if jti:
                    exp = datetime.fromtimestamp(payload.get("exp"))
                    jwt_service.blacklist_token(jti, exp)
        
        # Log logout event
        security_service.log_security_event(
            db, current_user, "user_logout", "authentication",
            {"user_id": current_user.id}, request
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Setup MFA for the current user"""
    try:
        mfa_data = await enhanced_user_service.enable_mfa(db, current_user.id)
        return MFASetupResponse(**mfa_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup failed"
        )


@router.post("/mfa/verify")
async def verify_mfa_setup(
    mfa_verify: MFAVerifyRequest,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify MFA setup with a token"""
    try:
        is_valid = await enhanced_user_service.verify_mfa_setup(
            db, current_user.id, mfa_verify.token
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA token"
            )
        
        return {"message": "MFA setup verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA verification failed"
        )


@router.post("/password/check", response_model=PasswordStrengthResponse)
async def check_password_strength(password: str):
    """Check password strength against enterprise policies"""
    try:
        result = security_service.validate_password_strength(password)
        return PasswordStrengthResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password validation failed"
        )


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information"""
    try:
        # Simply return the current user that was already verified
        return current_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.get("/me/sessions", response_model=List[UserSessionRead])
async def get_user_sessions(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all active sessions for the current user"""
    try:
        sessions = await enhanced_user_service.get_active_sessions(db, current_user.id)
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user sessions"
        )


@router.delete("/me/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a specific session"""
    try:
        await enhanced_user_service.deactivate_session(db, session_id)
        return {"message": "Session revoked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )


@router.get("/me/security-events", response_model=List[SecurityEventRead])
async def get_security_events(
    limit: int = 50,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get security events for the current user"""
    try:
        events = await enhanced_user_service.get_security_events(db, current_user.id, limit)
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security events"
        )


