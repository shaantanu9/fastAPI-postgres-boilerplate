# Plugin Architecture Example

## Current vs Plugin Architecture

### Current Way (Monolithic)

```python
# app/main.py - Everything hardcoded
from app.api.v1.endpoints import user, product, order
from app.core.middleware import setup_middleware
from app.db.models import User, Product, Order

app = FastAPI()

# Must manually add every feature
app.include_router(user.router)
app.include_router(product.router)
app.include_router(order.router)
setup_middleware(app)

# To add new feature = modify main.py
```

### Plugin Way (Modular)

```python
# app/main.py - Clean and extensible
from app.core.plugin_manager import PluginManager

app = FastAPI()
plugin_manager = PluginManager(app)

# Automatically discovers and loads plugins
plugin_manager.load_plugins()

# To add new feature = drop plugin in plugins/ folder
```

## Plugin System Components

### 1. Plugin Interface (Contract)

```python
# app/core/interfaces.py
from abc import ABC, abstractmethod
from fastapi import FastAPI
from typing import Optional

class Plugin(ABC):
    """Base plugin interface that all plugins must implement"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass

    @abstractmethod
    def install(self, app: FastAPI) -> None:
        """Install plugin into FastAPI app"""
        pass

    @abstractmethod
    def uninstall(self, app: FastAPI) -> None:
        """Remove plugin from FastAPI app"""
        pass

    @property
    def dependencies(self) -> list[str]:
        """List of plugin dependencies"""
        return []
```

### 2. Plugin Manager

```python
# app/core/plugin_manager.py
import importlib
import os
from pathlib import Path
from typing import Dict, List
from fastapi import FastAPI
from app.core.interfaces import Plugin

class PluginManager:
    def __init__(self, app: FastAPI):
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_dir = Path("app/plugins")

    def discover_plugins(self) -> List[str]:
        """Discover all available plugins"""
        plugins = []
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                plugin_file = item / "plugin.py"
                if plugin_file.exists():
                    plugins.append(item.name)
        return plugins

    def load_plugin(self, plugin_name: str) -> None:
        """Load a specific plugin"""
        module_path = f"app.plugins.{plugin_name}.plugin"
        module = importlib.import_module(module_path)

        # Find plugin class in module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, Plugin) and
                attr != Plugin):

                plugin_instance = attr()
                self.plugins[plugin_name] = plugin_instance
                plugin_instance.install(self.app)
                print(f"✅ Loaded plugin: {plugin_name}")
                break

    def load_plugins(self, enabled_plugins: List[str] = None) -> None:
        """Load all or specified plugins"""
        available_plugins = self.discover_plugins()

        if enabled_plugins is None:
            enabled_plugins = available_plugins

        for plugin_name in enabled_plugins:
            if plugin_name in available_plugins:
                try:
                    self.load_plugin(plugin_name)
                except Exception as e:
                    print(f"❌ Failed to load plugin {plugin_name}: {e}")
```

### 3. Example Plugin: Authentication

```python
# app/plugins/auth/plugin.py
from fastapi import FastAPI, APIRouter, Depends
from app.core.interfaces import Plugin
from .routes import auth_router
from .middleware import AuthMiddleware
from .dependencies import get_current_user

class AuthPlugin(Plugin):
    @property
    def name(self) -> str:
        return "auth"

    @property
    def version(self) -> str:
        return "1.0.0"

    def install(self, app: FastAPI) -> None:
        """Install authentication features"""
        # Add authentication routes
        app.include_router(auth_router, prefix="/auth", tags=["auth"])

        # Add authentication middleware
        app.add_middleware(AuthMiddleware)

        # Register global dependencies
        app.dependency_overrides[get_current_user] = get_current_user

    def uninstall(self, app: FastAPI) -> None:
        """Remove authentication features"""
        # Remove middleware and dependencies
        pass

# app/plugins/auth/routes.py
from fastapi import APIRouter, Depends
from .services import AuthService
from .schemas import LoginRequest, TokenResponse

auth_router = APIRouter()

@auth_router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, auth_service: AuthService = Depends()):
    return await auth_service.authenticate(request.username, request.password)
```

### 4. Example Plugin: E-commerce Domain

```python
# app/plugins/ecommerce/plugin.py
from fastapi import FastAPI
from app.core.interfaces import Plugin
from .routes import product_router, order_router
from .models import Product, Order

class EcommercePlugin(Plugin):
    @property
    def name(self) -> str:
        return "ecommerce"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def dependencies(self) -> list[str]:
        return ["auth", "cache"]  # Requires auth and cache plugins

    def install(self, app: FastAPI) -> None:
        """Install e-commerce features"""
        # Add e-commerce routes
        app.include_router(product_router, prefix="/products", tags=["products"])
        app.include_router(order_router, prefix="/orders", tags=["orders"])

        # Register models for database
        from app.db.base import Base
        # Models automatically discovered by SQLAlchemy

    def uninstall(self, app: FastAPI) -> None:
        pass
```

## Configuration-Based Plugin Loading

```python
# app/core/config.py
class Settings:
    # Plugin configuration
    enabled_plugins: List[str] = [
        "auth",
        "cache",
        "monitoring",
        "ecommerce"  # Only load what you need
    ]

    # Plugin-specific settings
    auth_plugin_jwt_secret: str = "secret"
    cache_plugin_redis_url: str = "redis://localhost:6379"

# app/main.py
settings = get_settings()
plugin_manager.load_plugins(settings.enabled_plugins)
```

## Benefits of Plugin Architecture

### 1. **Clean Separation**

```python
# Before: Everything mixed in main.py
# After: Each domain is isolated

# Blog plugin
app/plugins/blog/
├── plugin.py       # Plugin definition
├── models.py       # Post, Comment models
├── routes.py       # Blog API endpoints
├── services.py     # Blog business logic
└── schemas.py      # Blog Pydantic models

# E-commerce plugin
app/plugins/ecommerce/
├── plugin.py       # Plugin definition
├── models.py       # Product, Order models
├── routes.py       # Shop API endpoints
├── services.py     # Shop business logic
└── schemas.py      # Shop Pydantic models
```

### 2. **Environment-Specific Features**

```python
# Development environment
enabled_plugins = ["auth", "debug", "dev_tools"]

# Production environment
enabled_plugins = ["auth", "cache", "monitoring", "ecommerce"]

# Testing environment
enabled_plugins = ["auth", "test_helpers"]
```

### 3. **Easy Feature Sharing**

```python
# Package a plugin for reuse
pip install fastapi-auth-plugin
pip install fastapi-ecommerce-plugin

# Use in any FastAPI project
# Just drop in plugins/ folder
```

### 4. **Hot Reloading (Advanced)**

```python
# Reload plugins without restarting app
plugin_manager.reload_plugin("ecommerce")
plugin_manager.disable_plugin("debug")
plugin_manager.enable_plugin("monitoring")
```

## Real-World Example: Adding Blog Feature

### Current Way (Modify core files)

1. Create `app/db/models/blog.py`
2. Create `app/api/v1/endpoints/blog.py`
3. Create `app/services/blog_service.py`
4. **Modify** `app/main.py` to import blog router
5. **Modify** `app/db/base.py` to import blog models
6. **Modify** `app/api/v1/api.py` to register blog routes

### Plugin Way (Zero core changes)

1. Create `app/plugins/blog/` folder
2. Drop in blog plugin files
3. Add `"blog"` to enabled_plugins config
4. **No core file modifications needed!**

## Implementation Impact

### Code Changes Required

1. **Create plugin infrastructure** (new files)
2. **Modify main.py** (simplify, add plugin loading)
3. **Convert existing features** to plugins (optional)
4. **Add configuration** for plugin management

### Backward Compatibility

- ✅ **Existing code keeps working**
- ✅ **Gradual migration** to plugins
- ✅ **No breaking changes** to current APIs
- ✅ **Optional adoption** - use plugins only for new features

This is still **ONE FastAPI app** - plugins just make it modular and extensible! 🚀
