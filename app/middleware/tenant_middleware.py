# app/middleware/tenant_middleware.py

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import re

from app.db.session import get_db
from app.services.organization_service import organization_service
from app.core.jwt import jwt_service
from loguru import logger


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware for handling tenant isolation in multi-tenant SaaS"""
    
    def __init__(self, app, tenant_header: str = "X-Organization-ID"):
        super().__init__(app)
        self.tenant_header = tenant_header
        
        # Routes that don't require tenant isolation
        self.excluded_routes = [
            r'^/api/v1/auth/.*',
            r'^/api/v1/users/.*',  # User management
            r'^/api/v1/organizations/?$',  # List/create organizations
            r'^/api/v1/organizations/invitations/accept',
            r'^/api/v1/health/.*',
            r'^/docs.*',
            r'^/redoc.*',
            r'^/openapi.json',
            r'^/favicon.ico'
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request with tenant isolation"""
        
        # Skip tenant isolation for excluded routes
        if self._is_excluded_route(request.url.path):
            return await call_next(request)
        
        # Skip tenant isolation for non-API routes
        if not request.url.path.startswith('/api/'):
            return await call_next(request)
        
        try:
            # Extract tenant context
            tenant_context = await self._extract_tenant_context(request)
            
            if tenant_context:
                # Add tenant context to request state
                request.state.organization_id = tenant_context['organization_id']
                request.state.organization_slug = tenant_context['organization_slug']
                request.state.user_role = tenant_context['user_role']
                request.state.is_tenant_member = True
            else:
                request.state.organization_id = None
                request.state.organization_slug = None
                request.state.user_role = None
                request.state.is_tenant_member = False
            
            # Continue with request
            response = await call_next(request)
            
            # Add tenant headers to response
            if tenant_context:
                response.headers["X-Organization-ID"] = tenant_context['organization_id']
                response.headers["X-Organization-Slug"] = tenant_context['organization_slug']
                response.headers["X-User-Role"] = tenant_context['user_role']
            
            return response
            
        except HTTPException as e:
            # Return structured error response
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
    
    async def _extract_tenant_context(self, request: Request) -> Optional[dict]:
        """Extract tenant context from request"""
        
        # Method 1: Organization ID from header
        org_id = request.headers.get(self.tenant_header)
        
        # Method 2: Organization slug from URL path
        org_slug = self._extract_org_slug_from_path(request.url.path)
        
        # Method 3: Organization ID from URL path
        if not org_id:
            org_id = self._extract_org_id_from_path(request.url.path)
        
        # Get user from JWT token
        user_id = await self._get_user_from_token(request)
        
        if not user_id:
            # No user context, allow request to proceed without tenant
            return None
        
        # Get organization and verify user membership
        async for db in get_db():
            organization = None
            
            if org_slug:
                organization = await organization_service.get_organization_by_slug(
                    db, org_slug, user_id
                )
            elif org_id:
                # Check if user is member of this organization
                is_member = await organization_service.is_user_member(db, org_id, user_id)
                if is_member:
                    organization = await organization_service.get_by_id(db, org_id)
            
            if organization:
                # Get user role in organization
                user_role = await organization_service.get_user_role_in_organization(
                    db, organization.id, user_id
                )
                
                return {
                    'organization_id': organization.id,
                    'organization_slug': organization.slug,
                    'user_role': user_role,
                    'organization': organization
                }
            break  # Exit the async generator loop
        
        return None
    
    def _is_excluded_route(self, path: str) -> bool:
        """Check if route is excluded from tenant isolation"""
        
        for pattern in self.excluded_routes:
            if re.match(pattern, path):
                return True
        return False
    
    def _extract_org_slug_from_path(self, path: str) -> Optional[str]:
        """Extract organization slug from URL path"""
        
        # Pattern: /api/v1/org/{slug}/...
        org_pattern = r'^/api/v1/org/([a-z0-9-]+)'
        match = re.match(org_pattern, path)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_org_id_from_path(self, path: str) -> Optional[str]:
        """Extract organization ID from URL path"""
        
        # Pattern: /api/v1/organizations/{org_id}/...
        org_pattern = r'^/api/v1/organizations/([a-f0-9-]{36})'
        match = re.match(org_pattern, path)
        if match:
            return match.group(1)
        
        return None
    
    async def _get_user_from_token(self, request: Request) -> Optional[str]:
        """Extract user ID from JWT token"""
        
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        
        try:
            payload = jwt_service.verify_token(token)
            return payload.get("user_id")
        except Exception:
            return None


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for strict tenant data isolation"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Routes that require tenant isolation
        self.tenant_required_routes = [
            r'^/api/v1/organizations/[a-f0-9-]{36}/.*',  # Organization-specific routes
            r'^/api/v1/org/[a-z0-9-]+/.*',  # Organization slug routes
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Enforce tenant isolation for specific routes"""
        
        path = request.url.path
        
        # Check if route requires tenant isolation
        requires_tenant = any(
            re.match(pattern, path) for pattern in self.tenant_required_routes
        )
        
        if requires_tenant:
            # Ensure tenant context exists
            if not hasattr(request.state, 'organization_id') or not request.state.organization_id:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Access denied: Organization context required",
                        "error_code": "TENANT_CONTEXT_REQUIRED"
                    }
                )
            
            # Ensure user is a member
            if not getattr(request.state, 'is_tenant_member', False):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Access denied: You are not a member of this organization",
                        "error_code": "TENANT_MEMBERSHIP_REQUIRED"
                    }
                )
        
        return await call_next(request)


# Utility functions for use in route handlers
def get_current_organization_id(request: Request) -> Optional[str]:
    """Get current organization ID from request state"""
    return getattr(request.state, 'organization_id', None)


def get_current_organization_slug(request: Request) -> Optional[str]:
    """Get current organization slug from request state"""
    return getattr(request.state, 'organization_slug', None)


def get_current_user_role(request: Request) -> Optional[str]:
    """Get current user role in organization from request state"""
    return getattr(request.state, 'user_role', None)


def require_organization_context(request: Request) -> str:
    """Require organization context, raise exception if not present"""
    org_id = get_current_organization_id(request)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization context required"
        )
    return org_id


def require_organization_role(request: Request, required_roles: list) -> str:
    """Require specific organization role, raise exception if not met"""
    org_id = require_organization_context(request)
    user_role = get_current_user_role(request)
    
    if not user_role or user_role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required role: {', '.join(required_roles)}"
        )
    
    return org_id


# Dependency functions for FastAPI
def get_organization_context(request: Request) -> dict:
    """Get organization context as FastAPI dependency"""
    return {
        'organization_id': get_current_organization_id(request),
        'organization_slug': get_current_organization_slug(request),
        'user_role': get_current_user_role(request),
        'is_member': getattr(request.state, 'is_tenant_member', False)
    } 