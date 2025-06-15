"""
ShoppingCart FastAPI routes with Enterprise Authentication
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.core.security import security_service
# Note: require_permission, require_role, get_current_active_user not available yet

# Optional rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    HAS_RATE_LIMITING = True
except ImportError:
    # Create a dummy limiter that does nothing
    class DummyLimiter:
        def limit(self, rate):
            def decorator(func):
                return func
            return decorator
    limiter = DummyLimiter()
    HAS_RATE_LIMITING = False

from .schemas import (
    ShoppingCartCreate, 
    ShoppingCartUpdate, 
    ShoppingCartResponse,
    ShoppingCartSearch
)
from .services import ShoppingCartService


class ShoppingCartRoutes:
    """FastAPI routes for ShoppingCart with enterprise security"""
    
    def __init__(self):
        self.router = APIRouter()
        self.service = ShoppingCartService()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup CRUD routes for ShoppingCart with authentication"""
        
        @self.router.post("/shopping_carts/", response_model=ShoppingCartResponse, tags=["ShoppingCart"])
        @limiter.limit('10/minute')
        async def create_shopping_cart(
            item: ShoppingCartCreate,
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Create a new shopping_cart"""
            try:
                # Security: Check permissions
                # Token authentication only - user is authenticated via JWT
                
                # Create the item
                result = await self.service.create(**item.dict())
                
                # Audit logging
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_create', 'resource_access',
                    {"resource": "shopping_cart", "action": "create", "resource_id": getattr(result, 'id', None)},
                    request
                )
                
                # Emit creation event
                self.emit_event("shopping_cart_created", 
                              id=result.id, 
                              user_id=current_user.id,
                              plugin="shopping_cart_plugin")
                
                return result
            except HTTPException:
                raise
            except Exception as e:
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_create_failed', 'resource_access',
                    {"resource": "shopping_cart", "action": "create_failed"},
                    request
                )
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/shopping_carts/", response_model=List[ShoppingCartResponse], tags=["ShoppingCart"])
        @limiter.limit('100/minute')
        async def get_shopping_carts(
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            """Get all shopping_carts with pagination"""
            try:
                # Security: Check permissions
                # Token authentication only - user is authenticated via JWT
                
                # Apply row-level security if configured
                # No row-level security applied
                
                results = await self.service.get_all(skip=skip, limit=limit)
                
                # Audit logging for bulk read
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_read_bulk', 'resource_access',
                    {"resource": "shopping_cart", "action": "read_bulk", "count": len(results)},
                    request
                )
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/shopping_carts/{item_id}", response_model=ShoppingCartResponse, tags=["ShoppingCart"])
        @limiter.limit('100/minute')
        async def get_shopping_cart(
            item_id: int,
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Get a specific shopping_cart by ID"""
            try:
                # Security: Check permissions
                # Token authentication only - user is authenticated via JWT
                
                result = await self.service.get(item_id)
                if not result:
                    raise HTTPException(status_code=404, detail="ShoppingCart not found")
                
                # Security: Check owner-based access
                # No owner-based access control
                
                # Audit logging
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_read', 'resource_access',
                    {"resource": "shopping_cart", "action": "read", "resource_id": getattr(result, 'id', None)},
                    request
                )
                
                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/shopping_carts/{item_id}", response_model=ShoppingCartResponse, tags=["ShoppingCart"])
        @limiter.limit('20/minute')
        async def update_shopping_cart(
            item_id: int,
            item: ShoppingCartUpdate,
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Update a shopping_cart"""
            try:
                # Security: Check permissions
                # Token authentication only - user is authenticated via JWT
                
                # Get existing item for owner check
                existing = await self.service.get(item_id)
                if not existing:
                    raise HTTPException(status_code=404, detail="ShoppingCart not found")
                
                # Security: Check owner-based access
                # No owner-based access control
                
                result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                
                # Audit logging
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_update', 'resource_access',
                    {"resource": "shopping_cart", "action": "update", "resource_id": getattr(result, 'id', None)},
                    request
                )
                
                return result
            except HTTPException:
                raise
            except Exception as e:
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_update_failed', 'resource_access',
                    {"resource": "shopping_cart", "action": "update_failed"},
                    request
                )
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/shopping_carts/{item_id}", tags=["ShoppingCart"])
        @limiter.limit('5/minute')
        async def delete_shopping_cart(
            item_id: int,
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Delete a shopping_cart"""
            try:
                # Security: Check permissions
                # Token authentication only - user is authenticated via JWT
                
                # Get existing item for owner check
                existing = await self.service.get(item_id)
                if not existing:
                    raise HTTPException(status_code=404, detail="ShoppingCart not found")
                
                # Security: Check owner-based access
                # No owner-based access control
                
                success = await self.service.delete(item_id)
                if not success:
                    raise HTTPException(status_code=404, detail="ShoppingCart not found")
                
                # Audit logging
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_delete', 'resource_access',
                    {"resource": "shopping_cart", "action": "delete", "resource_id": item_id},
                    request
                )
                
                return {"message": "ShoppingCart deleted successfully"}
            except HTTPException:
                raise
            except Exception as e:
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_delete_failed', 'resource_access',
                    {"resource": "shopping_cart", "action": "delete_failed"},
                    request
                )
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/shopping_carts/search/", response_model=List[ShoppingCartResponse], tags=["ShoppingCart"])
        @limiter.limit('50/minute')
        async def search_shopping_carts(
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100)
        ):
            """Search shopping_carts"""
            try:
                # Security: Check permissions
                # Token authentication only - user is authenticated via JWT
                
                results = await self.service.search(q, limit=limit)
                
                # Audit logging
                
                # Log security event for audit trail
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_search', 'resource_access',
                    {"resource": "shopping_cart", "action": "search", "count": len(results)},
                    request
                )
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.post("/shopping_carts/bulk", response_model=List[ShoppingCartResponse], tags=["ShoppingCart"])
        @limiter.limit('10/minute')
        async def create_bulk_shopping_carts(
            items: List[ShoppingCartCreate],
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Create multiple shopping_carts (Admin only)"""
            try:
                # Bulk operations require admin privileges
                if not await security_service.is_admin(current_user):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bulk operations require admin privileges"
                    )
                
                results = await self.service.bulk_create(items)
                self.emit_event("shopping_cart_bulk_created", 
                              count=len(results), 
                              user_id=current_user.id)
                
                # Audit log
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_bulk_create', 'admin_action',
                    {"count": len(results)}, request
                )
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/shopping_carts/bulk", response_model=List[ShoppingCartResponse], tags=["ShoppingCart"])
        @limiter.limit('10/minute')
        async def update_bulk_shopping_carts(
            updates: List[ShoppingCartUpdate],
            request: Request,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            """Update multiple shopping_carts (Admin only)"""
            try:
                # Bulk operations require admin privileges
                if not await security_service.is_admin(current_user):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bulk operations require admin privileges"
                    )
                
                results = await self.service.bulk_update(updates)
                self.emit_event("shopping_cart_bulk_updated", 
                              count=len(results), 
                              user_id=current_user.id)
                
                # Audit log
                await security_service.log_security_event(
                    db, current_user, 'shopping_cart_bulk_update', 'admin_action',
                    {"count": len(results)}, request
                )
                
                return results
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    def get_router(self) -> APIRouter:
        """Get the FastAPI router"""
        return self.router
    
    def emit_event(self, event_name: str, **kwargs):
        """Emit plugin events for monitoring and integration"""
        try:
            # Try to use the plugin system's event emitter
            from app.core.plugin_system import get_plugin_manager
            plugin_manager = get_plugin_manager()
            if plugin_manager and hasattr(plugin_manager, 'emit_event'):
                plugin_manager.emit_event(event_name, **kwargs)
        except ImportError:
            # Fallback: just log the event
            print(f"📡 Event: {event_name} - {kwargs}")
        except Exception as e:
            # Don't let event emission break the main functionality
            print(f"⚠️ Event emission failed: {e}")

    
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

