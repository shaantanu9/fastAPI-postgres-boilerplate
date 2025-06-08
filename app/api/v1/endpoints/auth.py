from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import email_service
from app.core.jwt import jwt_service
from app.core.security_base import EnterpriseSecurityService
from app.core.security_codes import security_codes_service
from app.db.schemas.user import (
    BackupCodePasswordReset,
    LoginRequest,
    LoginResponse,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordResetRequest,
    PasswordStrengthResponse,
    RefreshTokenRequest,
    SecurityEventRead,
    UserCreate,
    UserRead,
)
from app.db.session import get_db
from app.services.user_service import enhanced_user_service


def get_security_service() -> EnterpriseSecurityService:
    return security_service


router = APIRouter()


# Helper function to get current user
async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Dependency to retrieve the current authenticated user from the request.

    Args:
        request (Request): The incoming FastAPI request object.
        db (AsyncSession): The async database session.

    Returns:
        UserRead: The authenticated user as a Pydantic model.

    Raises:
        HTTPException: If authentication fails or the user is not found/active.

    """
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header.split(" ")[1]

    try:
        payload = jwt_service.verify_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token",
            )

        user = await enhanced_user_service.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
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
            detail=f"Token validation failed: {e!s}",
        )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    security_service: Annotated[EnterpriseSecurityService, Depends(get_security_service)],
):
    """Register a new user with enterprise security validation and email verification.

    Args:
        user_create (UserCreate): The user registration data.
        request (Request): The incoming request object.
        background_tasks (BackgroundTasks): For running background jobs.
        db (AsyncSession): The async database session.
        security_service (EnterpriseSecurityService): Security service dependency.

    Returns:
        UserRead: The registered user as a Pydantic model.

    Raises:
        HTTPException: On registration failure or validation errors.

    """
    try:
        user = await enhanced_user_service.create_user(
            db, user_create, security_service,
        )

        # Send verification email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            user.email,
            f"{user.first_name} {user.last_name}",
            user.id,
        )

        # Log registration event
        security_service.log_security_event(
            db,
            user,
            "user_registration",
            "authentication",
            {"username": user.username, "email": user.email},
            request,
        )

        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    security_service: Annotated[EnterpriseSecurityService, Depends(get_security_service)],
):
    """Enhanced login endpoint with multi-factor authentication (MFA) and session management.

    Args:
        login_data (LoginRequest): The login credentials and MFA token.
        request (Request): The incoming request object.
        db (AsyncSession): The async database session.
        security_service (EnterpriseSecurityService): Security service dependency.

    Returns:
        LoginResponse: The login response including tokens and user info.

    Raises:
        HTTPException: On authentication or MFA failure.

    """
    try:
        # Authenticate user
        user = await enhanced_user_service.authenticate_user(
            db,
            login_data.username_or_email,
            login_data.password,
            request,
            security_service,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials",
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
                requires_mfa=True,
            )

        # Verify MFA if provided
        if user.mfa_enabled and login_data.mfa_token:
            if not security_service.verify_mfa_token(
                user.mfa_secret, login_data.mfa_token,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA token",
                )

        # Create session
        session = await enhanced_user_service.create_session(db, user, request)

        # Generate tokens
        access_token = jwt_service.create_access_token(
            data={"sub": user.username, "user_id": user.id, "session_id": session.id},
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
            requires_mfa=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        # For debugging - show actual error
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {e!s}",
        )


# Legacy token endpoint for backward compatibility
@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    security_service: Annotated[EnterpriseSecurityService, Depends(get_security_service)],
):
    """Legacy token endpoint for backward compatibility with OAuth2PasswordRequestForm.

    Args:
        request (Request): The incoming request object.
        form_data (OAuth2PasswordRequestForm): OAuth2 form data.
        db (AsyncSession): The async database session.
        security_service (EnterpriseSecurityService): Security service dependency.

    Returns:
        LoginResponse: The login response including tokens and user info.

    """
    login_data = LoginRequest(
        username_or_email=form_data.username, password=form_data.password,
    )
    return await login(login_data, request, db, security_service)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_token_request: RefreshTokenRequest, db: Annotated[AsyncSession, Depends(get_db)],
):
    """Refresh the access token using a valid refresh token.

    Args:
        refresh_token_request (RefreshTokenRequest): The refresh token request payload.
        db (AsyncSession): The async database session.

    Returns:
        LoginResponse: The refreshed login response with new access token.

    Raises:
        HTTPException: If the refresh token is invalid or expired.

    """
    try:
        payload = jwt_service.verify_refresh_token(refresh_token_request.refresh_token)
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")

        # Get user and session
        user = await enhanced_user_service.get_by_id(db, user_id)
        session = await enhanced_user_service.get_session(db, session_id)

        if not user or not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token",
            )

        # Check if session is still valid
        if session.refresh_token != refresh_token_request.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token",
            )

        # Generate new access token
        access_token = jwt_service.create_access_token(
            data={"sub": user.username, "user_id": user.id, "session_id": session.id},
        )

        # Refresh user data
        await db.refresh(user)
        user_data = UserRead.from_orm(user)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token_request.refresh_token,
            expires_in=jwt_service.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_data,
            requires_mfa=False,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token",
        )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    """Set up multi-factor authentication (MFA) for a user.

    Args:
        request (Request): The incoming request object.
        db (AsyncSession): The async database session.
        current_user (UserRead): The currently authenticated user.

    Returns:
        MFASetupResponse: The MFA setup response data.

    Raises:
        HTTPException: If setup fails.

    """
    try:
        mfa_data = await enhanced_user_service.enable_mfa(db, current_user.id)
        return MFASetupResponse(**mfa_data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MFA setup failed",
        )


@router.post("/mfa/verify", response_model=bool)
async def verify_mfa(
    mfa_verify: MFAVerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    """Verify Multi-Factor Authentication (MFA) setup with a provided token.

    Args:
        mfa_verify (MFAVerifyRequest): The MFA verification request containing the token.
        db (AsyncSession): The async database session.
        current_user (UserRead): The currently authenticated user.

    Returns:
        bool: True if the MFA token is valid, False otherwise.

    Raises:
        HTTPException: If verification fails due to server error or invalid token.

    """
    try:
        return await enhanced_user_service.verify_mfa_setup(
            db, current_user.id, mfa_verify.token,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA verification failed",
        )


@router.get("/password/strength", response_model=PasswordStrengthResponse)
async def check_password_strength(password: str):
    """Check password strength against enterprise security policy requirements.

    Args:
        password (str): The password string to evaluate.

    Returns:
        PasswordStrengthResponse: Object containing password validity status and any validation errors.

    Raises:
        None: This endpoint does not raise exceptions for weak passwords, just returns validation results.

    """
    return security_service.validate_password_strength(password)


@router.post("/password/reset")
async def reset_password(
    reset_password_request: PasswordResetRequest, db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reset a user's password using a valid reset token.

    Args:
        reset_password_request (PasswordResetRequest): The password reset request containing user ID and token.
        db (AsyncSession): The async database session.

    Returns:
        dict: Status message indicating if the password was reset successfully.

    Raises:
        HTTPException: If the token is invalid, expired, or the user is not found.

    """
    try:
        user = await enhanced_user_service.get_by_email(
            db, reset_password_request.email,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found",
            )

        # Generate reset token
        reset_token = jwt_service.create_reset_token(user.id)

        # Send reset email
        await email_service.send_reset_password_email(
            reset_password_request.email,
            f"{user.first_name} {user.last_name}",
            reset_token,
        )

        return {"message": "Password reset email sent"}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )


@router.post("/password/forgot")
async def forgot_password(
    reset_password_request: PasswordResetRequest, db: Annotated[AsyncSession, Depends(get_db)],
):
    """Initiate the password reset flow by sending a reset link to the user's email.

    Args:
        reset_password_request (PasswordResetRequest): The password reset request containing the user's email.
        db (AsyncSession): The async database session.

    Returns:
        dict: Status message indicating if the reset email was sent.

    Raises:
        HTTPException: If the user is not found or email sending fails.

    """
    try:
        user = await enhanced_user_service.get_by_email(
            db, reset_password_request.email,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found",
            )

        # Generate reset token
        reset_token = jwt_service.create_reset_token(user.id)

        # Send reset email
        await email_service.send_reset_password_email(
            reset_password_request.email,
            f"{user.first_name} {user.last_name}",
            reset_token,
        )

        return {"message": "Password reset email sent"}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )


@router.post("/password/reset-with-backup-code")
async def reset_password_with_backup_code(
    request: BackupCodePasswordReset,
    db: Annotated[AsyncSession, Depends(get_db)],
    security_service: Annotated[EnterpriseSecurityService, Depends(get_security_service)],
):
    """Reset a user's password using a backup code (one-time use).

    Args:
        request (BackupCodePasswordReset): The reset request containing email, backup code, and new password.
        db (AsyncSession): The async database session.
        security_service (EnterpriseSecurityService): The security service for password validation.

    Returns:
        dict: Status message indicating if the password was reset successfully.

    Raises:
        HTTPException: If the backup code is invalid or the user is not found.

    """
    try:
        # Initialize security codes service
        await security_codes_service.initialize()

        # Find user by username or email
        user = await enhanced_user_service.get_by_username_or_email(
            db,
            username=request.username_or_email
            if "@" not in request.username_or_email
            else None,
            email=request.username_or_email
            if "@" in request.username_or_email
            else None,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found",
            )

        # Verify and consume backup code
        is_valid = await security_codes_service.verify_backup_code_for_password_reset(
            user.id, request.backup_code, db,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid backup code",
            )

        # Validate new password
        password_validation = security_service.validate_password_strength(
            request.new_password,
        )
        if not password_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet security requirements",
                    "errors": password_validation["errors"],
                },
            )

        # Update password
        user.hashed_password = security_service.hash_password(request.new_password)
        user.password_changed_at = datetime.utcnow()
        user.failed_login_attempts = 0
        user.account_locked_until = None

        await db.commit()

        # Get remaining backup codes count
        remaining_codes = await security_codes_service.get_user_code_status(user.id, db)

        return {
            "message": "Password reset successful using backup code",
            "user_id": user.id,
            "remaining_backup_codes": remaining_codes["backup_codes_count"],
            "warning": "Backup code has been consumed. Consider regenerating codes if running low.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup code password reset failed: {e!s}",
        )


@router.get("/security/events", response_model=list[SecurityEventRead])
async def get_security_events(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    """Retrieve security events for the currently authenticated user.

    Args:
        request (Request): The incoming request object.
        db (AsyncSession): The async database session.
        current_user (UserRead): The currently authenticated user.

    Returns:
        List[SecurityEventRead]: List of security events associated with the user.

    Raises:
        HTTPException: If retrieval fails or user is not authenticated.

    """
    try:
        return await enhanced_user_service.get_security_events(db, current_user.id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security events",
        )
