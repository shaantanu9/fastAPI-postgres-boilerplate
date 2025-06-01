"""
Enhanced FastAPI routes template with authentication and authorization
"""
from typing import List, Dict, Any
import re


class AuthRoutesTemplate:
    """Generates FastAPI routes templates with enterprise authentication"""
    
    def generate(self, model_name: str, fields: List[Dict[str, Any]], 
                auth_config: Dict[str, Any] = None, with_bulk: bool = False) -> str:
        """Generate FastAPI routes file content with authentication"""
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        pascal_name = model_name
        
        # Default auth configuration
        if auth_config is None:
            auth_config = {
                "enable_auth": True,
                "require_roles": [],
                "require_permissions": True,
                "enable_audit": True,
                "enable_rate_limiting": True,
                "owner_based_access": False
            }
        
        # Generate authentication imports and dependencies
        auth_imports = self._generate_auth_imports(auth_config)
        auth_dependencies = self._generate_auth_dependencies(auth_config, snake_name)
        
        # Generate rate limiting decorators
        rate_limiting = self._generate_rate_limiting(auth_config, snake_name)
        
        # Generate bulk routes with auth
        bulk_routes = ""
        if with_bulk:
            bulk_routes = self._generate_bulk_routes(pascal_name, snake_name, auth_config)
        
        # Generate audit logging helpers
        audit_helpers = self._generate_audit_helpers(auth_config)
        
        template = f'''"""
{pascal_name} FastAPI routes with Enterprise Authentication
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
{auth_imports}

from .schemas import (
    {pascal_name}Create, 
    {pascal_name}Update, 
    {pascal_name}Response,
    {pascal_name}Search
)
from .services import {pascal_name}Service


class {pascal_name}Routes:
    """FastAPI routes for {pascal_name} with enterprise security"""
    
    def __init__(self):
        self.router = APIRouter()
        self.service = {pascal_name}Service()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup CRUD routes for {pascal_name} with authentication"""
        
        @self.router.post("/{snake_name}s/", response_model={pascal_name}Response, tags=["{pascal_name}"])
        {rate_limiting.get('create', '')}
        async def create_{snake_name}(
            item: {pascal_name}Create,
            request: Request,
            {auth_dependencies.get('create', 'current_user = Depends(get_current_user)')},
            db: AsyncSession = Depends(get_db)
        ):
            \"\"\"Create a new {snake_name}\"\"\"
            try:
                # Security: Check permissions
                {self._generate_permission_check(auth_config, snake_name, 'create')}
                
                # Create the item
                result = await self.service.create(**item.dict())
                
                # Audit logging
                {self._generate_audit_log(auth_config, snake_name, 'create')}
                
                # Emit creation event
                self.emit_event("{snake_name}_created", 
                              id=result.id, 
                              user_id=current_user.id,
                              plugin="{snake_name}_plugin")
                
                return result
            except HTTPException:
                raise
            except Exception as e:
                {self._generate_audit_log(auth_config, snake_name, 'create_failed')}
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/{snake_name}s/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        {rate_limiting.get('read', '')}
        async def get_{snake_name}s(
            request: Request,
            {auth_dependencies.get('read', 'current_user = Depends(get_current_user)')},
            db: AsyncSession = Depends(get_db),
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            \"\"\"Get all {snake_name}s with pagination\"\"\"
            try:
                # Security: Check permissions
                {self._generate_permission_check(auth_config, snake_name, 'read')}
                
                # Apply row-level security if configured
                {self._generate_row_level_security(auth_config, snake_name)}
                
                results = await self.service.get_all(skip=skip, limit=limit{self._generate_owner_filter(auth_config)})
                
                # Audit logging for bulk read
                {self._generate_audit_log(auth_config, snake_name, 'read_bulk')}
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        {rate_limiting.get('read', '')}
        async def get_{snake_name}(
            item_id: int,
            request: Request,
            {auth_dependencies.get('read', 'current_user = Depends(get_current_user)')},
            db: AsyncSession = Depends(get_db)
        ):
            \"\"\"Get a specific {snake_name} by ID\"\"\"
            try:
                # Security: Check permissions
                {self._generate_permission_check(auth_config, snake_name, 'read')}
                
                result = await self.service.get(item_id)
                if not result:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                
                # Security: Check owner-based access
                {self._generate_owner_check(auth_config, snake_name)}
                
                # Audit logging
                {self._generate_audit_log(auth_config, snake_name, 'read')}
                
                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        {rate_limiting.get('update', '')}
        async def update_{snake_name}(
            item_id: int,
            item: {pascal_name}Update,
            request: Request,
            {auth_dependencies.get('update', 'current_user = Depends(get_current_user)')},
            db: AsyncSession = Depends(get_db)
        ):
            \"\"\"Update a {snake_name}\"\"\"
            try:
                # Security: Check permissions
                {self._generate_permission_check(auth_config, snake_name, 'update')}
                
                # Get existing item for owner check
                existing = await self.service.get(item_id)
                if not existing:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                
                # Security: Check owner-based access
                {self._generate_owner_check(auth_config, snake_name, 'existing')}
                
                result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                
                # Audit logging
                {self._generate_audit_log(auth_config, snake_name, 'update')}
                
                return result
            except HTTPException:
                raise
            except Exception as e:
                {self._generate_audit_log(auth_config, snake_name, 'update_failed')}
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/{snake_name}s/{{item_id}}", tags=["{pascal_name}"])
        {rate_limiting.get('delete', '')}
        async def delete_{snake_name}(
            item_id: int,
            request: Request,
            {auth_dependencies.get('delete', 'current_user = Depends(get_current_user)')},
            db: AsyncSession = Depends(get_db)
        ):
            \"\"\"Delete a {snake_name}\"\"\"
            try:
                # Security: Check permissions
                {self._generate_permission_check(auth_config, snake_name, 'delete')}
                
                # Get existing item for owner check
                existing = await self.service.get(item_id)
                if not existing:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                
                # Security: Check owner-based access
                {self._generate_owner_check(auth_config, snake_name, 'existing')}
                
                success = await self.service.delete(item_id)
                if not success:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                
                # Audit logging
                {self._generate_audit_log(auth_config, snake_name, 'delete')}
                
                return {{"message": "{pascal_name} deleted successfully"}}
            except HTTPException:
                raise
            except Exception as e:
                {self._generate_audit_log(auth_config, snake_name, 'delete_failed')}
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/{snake_name}s/search/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        {rate_limiting.get('search', '')}
        async def search_{snake_name}s(
            q: str = Query(..., min_length=1),
            request: Request,
            {auth_dependencies.get('read', 'current_user = Depends(get_current_user)')},
            db: AsyncSession = Depends(get_db),
            limit: int = Query(10, ge=1, le=100)
        ):
            \"\"\"Search {snake_name}s\"\"\"
            try:
                # Security: Check permissions
                {self._generate_permission_check(auth_config, snake_name, 'read')}
                
                results = await self.service.search(q, limit=limit{self._generate_owner_filter(auth_config)})
                
                # Audit logging
                {self._generate_audit_log(auth_config, snake_name, 'search')}
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e)){bulk_routes}
    
    def get_router(self) -> APIRouter:
        \"\"\"Get the FastAPI router\"\"\"
        return self.router
    
    def emit_event(self, event_name: str, **kwargs):
        \"\"\"Emit plugin events for monitoring and integration\"\"\"
        try:
            # Try to use the plugin system's event emitter
            from app.core.plugin_system import get_plugin_manager
            plugin_manager = get_plugin_manager()
            if plugin_manager and hasattr(plugin_manager, 'emit_event'):
                plugin_manager.emit_event(event_name, **kwargs)
        except ImportError:
            # Fallback: just log the event
            print(f"📡 Event: {{event_name}} - {{kwargs}}")
        except Exception as e:
            # Don't let event emission break the main functionality
            print(f"⚠️ Event emission failed: {{e}}")
{audit_helpers}
'''
        
        return template
    
    def _generate_auth_imports(self, auth_config: Dict[str, Any]) -> str:
        """Generate authentication-related imports"""
        imports = []
        
        if auth_config.get("enable_auth", True):
            imports.append("from sqlalchemy.ext.asyncio import AsyncSession")
            imports.append("from app.db.session import get_db")
            imports.append("from app.api.v1.endpoints.auth import get_current_user")
            
            if auth_config.get("require_permissions", True):
                imports.append("from app.core.security import require_permission")
            
            if auth_config.get("require_roles"):
                imports.append("from app.core.security import require_role")
                
            if auth_config.get("enable_audit", True):
                imports.append("from app.core.security import security_service")
                
            if auth_config.get("enable_rate_limiting", True):
                imports.append("from slowapi import Limiter, _rate_limit_exceeded_handler")
                imports.append("from slowapi.util import get_remote_address")
        
        return '\n'.join(imports)
    
    def _generate_auth_dependencies(self, auth_config: Dict[str, Any], snake_name: str) -> Dict[str, str]:
        """Generate authentication dependencies for each operation"""
        deps = {}
        
        if not auth_config.get("enable_auth", True):
            return {"create": "", "read": "", "update": "", "delete": ""}
        
        base_dep = "current_user = Depends(get_current_user)"
        
        # Add role requirements
        if auth_config.get("require_roles"):
            roles = auth_config["require_roles"]
            if isinstance(roles, dict):
                # Different roles for different operations
                for op in ["create", "read", "update", "delete"]:
                    role = roles.get(op, roles.get("default", "user"))
                    deps[op] = f"current_user = Depends(require_role('{role}'))"
            else:
                # Same role for all operations
                if isinstance(roles, list) and len(roles) == 1:
                    role_dep = f"current_user = Depends(require_role('{roles[0]}'))"
                elif isinstance(roles, list):
                    roles_str = "', '".join(roles)
                    role_dep = f"current_user = Depends(require_role(['{roles_str}']))"
                else:
                    role_dep = f"current_user = Depends(require_role('{roles}'))"
                deps = {"create": role_dep, "read": role_dep, "update": role_dep, "delete": role_dep}
        
        # Add permission requirements
        elif auth_config.get("require_permissions", True):
            resource = snake_name
            deps = {
                "create": f"current_user = Depends(require_permission('{resource}', 'create'))",
                "read": f"current_user = Depends(require_permission('{resource}', 'read'))",
                "update": f"current_user = Depends(require_permission('{resource}', 'update'))",
                "delete": f"current_user = Depends(require_permission('{resource}', 'delete'))"
            }
        else:
            deps = {"create": base_dep, "read": base_dep, "update": base_dep, "delete": base_dep}
        
        return deps
    
    def _generate_rate_limiting(self, auth_config: Dict[str, Any], snake_name: str) -> Dict[str, str]:
        """Generate rate limiting decorators"""
        if not auth_config.get("enable_rate_limiting", True):
            return {}
        
        # Default rate limits
        return {
            "create": f"@limiter.limit('10/minute')",
            "read": f"@limiter.limit('100/minute')",
            "update": f"@limiter.limit('20/minute')",
            "delete": f"@limiter.limit('5/minute')",
            "search": f"@limiter.limit('50/minute')"
        }
    
    def _generate_permission_check(self, auth_config: Dict[str, Any], snake_name: str, action: str) -> str:
        """Generate permission check code"""
        if not auth_config.get("require_permissions", True):
            return "# No additional permission checks required"
        
        return f'''
                # Check if user has permission for this action
                if not await security_service.check_permission(
                    db, current_user, '{snake_name}', '{action}'
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )'''
    
    def _generate_owner_check(self, auth_config: Dict[str, Any], snake_name: str, result_var: str = "result") -> str:
        """Generate owner-based access control"""
        if not auth_config.get("owner_based_access", False):
            return "# No owner-based access control"
        
        return f'''
                # Check if user owns this resource or has admin privileges
                if hasattr({result_var}, 'user_id') and {result_var}.user_id != current_user.id:
                    if not await security_service.is_admin(current_user):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied: You can only access your own {snake_name}s"
                        )'''
    
    def _generate_row_level_security(self, auth_config: Dict[str, Any], snake_name: str) -> str:
        """Generate row-level security for listing operations"""
        if not auth_config.get("owner_based_access", False):
            return "# No row-level security applied"
        
        return f'''
                # Apply row-level security for data access
                if not await security_service.is_admin(current_user):
                    # Non-admin users can only see their own data
                    pass  # This will be handled in the service layer'''
    
    def _generate_owner_filter(self, auth_config: Dict[str, Any]) -> str:
        """Generate owner filter for queries"""
        if not auth_config.get("owner_based_access", False):
            return ""
        
        return ", owner_id=current_user.id"
    
    def _generate_audit_log(self, auth_config: Dict[str, Any], snake_name: str, action: str) -> str:
        """Generate audit logging code"""
        if not auth_config.get("enable_audit", True):
            return "# No audit logging configured"
        
        return f'''
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, '{snake_name}_{action}', 'resource_access',
                    {{"resource": "{snake_name}", "action": "{action}", "resource_id": getattr(result, 'id', None)}},
                    request
                )'''
    
    def _generate_bulk_routes(self, pascal_name: str, snake_name: str, auth_config: Dict[str, Any]) -> str:
        """Generate bulk operation routes with authentication"""
        auth_dep = self._generate_auth_dependencies(auth_config, snake_name).get("create", "")
        rate_limit = self._generate_rate_limiting(auth_config, snake_name).get("create", "")
        
        return f'''
        
        @self.router.post("/{snake_name}s/bulk", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        {rate_limit}
        async def create_bulk_{snake_name}s(
            items: List[{pascal_name}Create],
            request: Request,
            {auth_dep},
            db: AsyncSession = Depends(get_db)
        ):
            \"\"\"Create multiple {snake_name}s (Admin only)\"\"\"
            try:
                # Bulk operations require admin privileges
                if not await security_service.is_admin(current_user):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bulk operations require admin privileges"
                    )
                
                results = await self.service.bulk_create(items)
                self.emit_event("{snake_name}_bulk_created", 
                              count=len(results), 
                              user_id=current_user.id)
                
                # Audit log
                await security_service.log_security_event(
                    db, current_user, '{snake_name}_bulk_create', 'admin_action',
                    {{"count": len(results)}}, request
                )
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/{snake_name}s/bulk", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        {rate_limit}
        async def update_bulk_{snake_name}s(
            updates: List[{pascal_name}Update],
            request: Request,
            {auth_dep},
            db: AsyncSession = Depends(get_db)
        ):
            \"\"\"Update multiple {snake_name}s (Admin only)\"\"\"
            try:
                # Bulk operations require admin privileges
                if not await security_service.is_admin(current_user):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bulk operations require admin privileges"
                    )
                
                results = await self.service.bulk_update(updates)
                self.emit_event("{snake_name}_bulk_updated", 
                              count=len(results), 
                              user_id=current_user.id)
                
                # Audit log
                await security_service.log_security_event(
                    db, current_user, '{snake_name}_bulk_update', 'admin_action',
                    {{"count": len(results)}}, request
                )
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))'''
    
    def _generate_audit_helpers(self, auth_config: Dict[str, Any]) -> str:
        """Generate audit helper methods"""
        if not auth_config.get("enable_audit", True):
            return ""
        
        return '''
    
    async def log_access_event(self, db: AsyncSession, user, action: str, resource_id: int = None):
        """Helper method for logging access events"""
        try:
            await security_service.log_security_event(
                db, user, f"{self.__class__.__name__.lower()}_{action}", "resource_access",
                {"resource_id": resource_id}, None
            )
        except Exception as e:
            # Don't let audit logging break the main functionality
            print(f"⚠️ Audit logging failed: {e}")
''' 