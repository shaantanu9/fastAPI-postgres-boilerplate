"""Enterprise Plugin System for FastAPI Application.

This module implements a comprehensive plugin architecture following enterprise patterns:
- Plugin interface contracts using Python Protocols
- Dependency resolution and loading order management
- Event-driven communication between plugins
- Configuration management and security sandboxing
- Version compatibility checking
- Lifecycle management (install, uninstall, enable, disable)

Based on enterprise patterns from Netflix Dispatch and modern microservice architectures.
"""

import asyncio
import importlib
import importlib.util
import inspect
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI
from loguru import logger
from packaging import version


class PluginStatus(Enum):
    """Plugin lifecycle status."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Plugin metadata and configuration."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    min_app_version: str = "1.0.0"
    max_app_version: str | None = None
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    priority: int = 100  # Lower numbers = higher priority
    status: PluginStatus = PluginStatus.DISCOVERED
    config_schema: dict | None = None


class PluginInterface(Protocol):
    """Core plugin interface using Protocol for structural typing.
    All plugins must implement these methods and properties.
    """

    metadata: PluginMetadata

    async def initialize(self, app: FastAPI, context: "PluginContext") -> None:
        """Initialize the plugin with the FastAPI app and context."""
        ...

    async def startup(self) -> None:
        """Called during application startup."""
        ...

    async def shutdown(self) -> None:
        """Called during application shutdown."""
        ...

    def get_routes(self) -> list[Any]:
        """Return FastAPI routes to be registered."""
        ...

    def get_middleware(self) -> list[Any]:
        """Return middleware to be registered."""
        ...


class PluginBase(ABC):
    """Abstract base class for plugins that prefer inheritance.
    Provides default implementations and helper methods.
    """

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._app: FastAPI | None = None

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata - must be implemented by subclasses."""

    async def initialize(self, app: FastAPI, context: "PluginContext") -> None:
        """Initialize plugin with app and context."""
        self._app = app
        self._context = context
        logger.info(f"Initializing plugin: {self.metadata.name}")

    async def startup(self) -> None:
        """Default startup - can be overridden."""
        logger.debug(f"Starting plugin: {self.metadata.name}")

    async def shutdown(self) -> None:
        """Default shutdown - can be overridden."""
        logger.debug(f"Shutting down plugin: {self.metadata.name}")

    def get_routes(self) -> list[Any]:
        """Default: no routes."""
        return []

    def get_middleware(self) -> list[Any]:
        """Default: no middleware."""
        return []

    def emit_event(self, event_name: str, **kwargs) -> None:
        """Emit an event through the plugin context."""
        if self._context:
            self._context.event_bus.emit(event_name, **kwargs)

    def subscribe_event(self, event_name: str, callback: Callable) -> None:
        """Subscribe to an event through the plugin context."""
        if self._context:
            self._context.event_bus.subscribe(event_name, callback)


class EventBus:
    """Event-driven communication system for plugins.
    Enables loose coupling between plugins.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}
        self._event_history: list[dict] = []
        self._max_history = 1000

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Subscribe to an event."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)
        logger.debug(f"Subscribed to event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Unsubscribe from an event."""
        if event_name in self._subscribers:
            try:
                self._subscribers[event_name].remove(callback)
                logger.debug(f"Unsubscribed from event: {event_name}")
            except ValueError:
                pass

    def emit(self, event_name: str, **kwargs) -> None:
        """Emit an event to all subscribers."""
        event_data = {
            "name": event_name,
            "data": kwargs,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Store in history
        self._event_history.append(event_data)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Notify subscribers
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(**kwargs))
                    else:
                        callback(**kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_name}: {e}")

        logger.debug(f"Emitted event: {event_name} with {len(kwargs)} parameters")

    def get_event_history(self) -> list[dict]:
        """Get recent event history."""
        return self._event_history.copy()


class PluginContext:
    """Shared context for plugins containing services and utilities."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.event_bus = EventBus()
        self.services: dict[str, Any] = {}
        self.config: dict[str, Any] = {}
        self._shared_data: dict[str, Any] = {}

    def register_service(self, name: str, service: Any) -> None:
        """Register a service for use by plugins."""
        self.services[name] = service
        logger.debug(f"Registered service: {name}")

    def get_service(self, name: str) -> Any | None:
        """Get a registered service."""
        return self.services.get(name)

    def set_shared_data(self, key: str, value: Any) -> None:
        """Set shared data accessible by all plugins."""
        self._shared_data[key] = value

    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """Get shared data."""
        return self._shared_data.get(key, default)


class VersionManager:
    """Manages version compatibility between app and plugins."""

    def __init__(self, app_version: str) -> None:
        self.app_version = version.parse(app_version)

    def is_compatible(self, plugin_metadata: PluginMetadata) -> bool:
        """Check if plugin is compatible with current app version."""
        try:
            min_version = version.parse(plugin_metadata.min_app_version)

            if plugin_metadata.max_app_version:
                max_version = version.parse(plugin_metadata.max_app_version)
                return min_version <= self.app_version <= max_version
            return min_version <= self.app_version
        except Exception as e:
            logger.error(f"Version compatibility check failed: {e}")
            return False


class PluginRegistry:
    """Central registry for all plugins.
    Manages plugin metadata, dependencies, and loading order.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInterface] = {}
        self._metadata: dict[str, PluginMetadata] = {}
        self._dependency_graph: dict[str, set[str]] = {}
        self._loading_order: list[str] = []

    def register(self, plugin: PluginInterface) -> None:
        """Register a plugin in the registry."""
        name = plugin.metadata.name

        if name in self._plugins:
            msg = f"Plugin {name} is already registered"
            raise ValueError(msg)

        self._plugins[name] = plugin
        self._metadata[name] = plugin.metadata
        self._dependency_graph[name] = set(plugin.metadata.dependencies)

        logger.info(f"Registered plugin: {name} v{plugin.metadata.version}")

    def unregister(self, plugin_name: str) -> None:
        """Unregister a plugin."""
        if plugin_name in self._plugins:
            del self._plugins[plugin_name]
            del self._metadata[plugin_name]
            del self._dependency_graph[plugin_name]
            self._resolve_loading_order()
            logger.info(f"Unregistered plugin: {plugin_name}")

    def get_plugin(self, name: str) -> PluginInterface | None:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def get_all_plugins(self) -> dict[str, PluginInterface]:
        """Get all registered plugins."""
        return self._plugins.copy()

    def get_metadata(self, name: str) -> PluginMetadata | None:
        """Get plugin metadata."""
        return self._metadata.get(name)

    def get_loading_order(self) -> list[str]:
        """Get plugins in dependency-resolved loading order."""
        if not self._loading_order:
            self._resolve_loading_order()
        return self._loading_order.copy()

    def _resolve_loading_order(self) -> None:
        """Resolve plugin loading order based on dependencies."""
        self._loading_order = []
        visited = set()
        temp_visited = set()

        def visit(name: str) -> None:
            if name in temp_visited:
                msg = f"Circular dependency detected for plugin: {name}"
                raise ValueError(msg)

            if name in visited:
                return

            temp_visited.add(name)

            # Visit dependencies first
            for dep in self._dependency_graph.get(name, set()):
                if dep not in self._plugins:
                    logger.warning(
                        f"Plugin {name} depends on {dep}, which is not available",
                    )
                    continue
                visit(dep)

            temp_visited.remove(name)
            visited.add(name)
            self._loading_order.append(name)

        # Sort by priority first, then resolve dependencies
        plugins_by_priority = sorted(
            self._plugins.keys(), key=lambda name: self._metadata[name].priority,
        )

        for plugin_name in plugins_by_priority:
            if plugin_name not in visited:
                visit(plugin_name)


class V4PluginAdapter(PluginInterface):
    """Adapter for v4 modular plugins to work with the existing plugin system.
    Bridges the gap between v4's register_plugin() pattern and v3's PluginBase pattern.
    """

    def __init__(self, module, plugin_name: str) -> None:
        self.module = module
        self.plugin_name = plugin_name
        self._metadata = None
        self._routes_instance = None

    @property
    def metadata(self) -> PluginMetadata:
        """Get metadata from the v4 plugin module."""
        if self._metadata is None:
            metadata_dict = self.module.PLUGIN_METADATA
            self._metadata = PluginMetadata(
                name=metadata_dict["name"],
                version=metadata_dict["version"],
                description=metadata_dict["description"],
                author=metadata_dict.get("author", ""),
                dependencies=metadata_dict.get("dependencies", []),
                tags=metadata_dict.get("features", []),  # Map features to tags
                priority=50,  # Default priority for v4 plugins
            )
        return self._metadata

    async def initialize(self, app: FastAPI, context: "PluginContext") -> None:
        """Initialize the v4 plugin by calling its register_plugin function."""
        try:
            # Call the plugin's register_plugin function to register routes and services
            # This is the main way v4 plugins register themselves
            success = self.module.register_plugin(app, context)
            if not success:
                msg = "Plugin registration returned False"
                raise Exception(msg)

            # Also initialize the routes instance for our get_routes() method
            if hasattr(self.module, "PLUGIN_COMPONENTS"):
                components = self.module.PLUGIN_COMPONENTS
                if "routes" in components:
                    routes_class = components["routes"]
                    self._routes_instance = routes_class()

            logger.info(f"v4 plugin {self.plugin_name} initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize v4 plugin {self.plugin_name}: {e}")
            raise

    async def startup(self) -> None:
        """Startup hook for v4 plugins."""
        # v4 plugins don't have explicit startup/shutdown hooks
        # but we can call initialize_plugin if it exists
        if hasattr(self.module, "initialize_plugin"):
            try:
                self.module.initialize_plugin()
            except Exception as e:
                logger.warning(f"v4 plugin {self.plugin_name} startup hook failed: {e}")

    async def shutdown(self) -> None:
        """Shutdown hook for v4 plugins."""
        # v4 plugins don't have explicit shutdown hooks

    def get_routes(self) -> list[Any]:
        """Get routes from the v4 plugin - return empty since v4 plugins register routes directly."""
        # v4 plugins register their routes directly through register_plugin() function
        # so we return empty list to avoid duplicate registration
        return []

    def get_middleware(self) -> list[Any]:
        """Get middleware from the v4 plugin (v4 plugins typically don't use middleware)."""
        return []


class PluginLoader:
    """Handles dynamic loading of plugins from various sources."""

    def __init__(self, version_manager: VersionManager) -> None:
        self.version_manager = version_manager
        self._loaded_modules: set[str] = set()

    def discover_plugins(self, search_paths: list[str]) -> list[PluginInterface]:
        """Discover plugins from specified search paths."""
        discovered_plugins = []

        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                logger.warning(f"Plugin search path does not exist: {search_path}")
                continue

            # Add to Python path if not already there
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))

            # Discover Python modules
            if path.is_dir():
                discovered_plugins.extend(self._discover_from_directory(path))
            elif path.suffix == ".py":
                plugin = self._load_from_file(path)
                if plugin:
                    discovered_plugins.append(plugin)

        return discovered_plugins

    def _discover_from_directory(self, directory: Path) -> list[PluginInterface]:
        """Discover plugins from a directory (supports both v3 and v4 patterns)."""
        plugins = []

        # First, look for v3-style single-file plugins (*.py files)
        for file_path in directory.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            plugin = self._load_from_file(file_path)
            if plugin:
                plugins.append(plugin)

        # Then, look for v4-style modular plugins (directories ending with _plugin)
        for plugin_dir in directory.iterdir():
            if plugin_dir.is_dir() and plugin_dir.name.endswith("_plugin"):
                plugin = self._load_v4_plugin(plugin_dir)
                if plugin:
                    plugins.append(plugin)

        return plugins

    def _load_from_file(self, file_path: Path) -> PluginInterface | None:
        """Load a plugin from a Python file."""
        try:
            # Use a unique module name to avoid conflicts
            module_name = f"plugin_loader_{file_path.stem}_{id(file_path)}"

            # Avoid loading the same module multiple times
            if str(file_path) in self._loaded_modules:
                return None

            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            # Only add to sys.modules if not already there
            if module_name not in sys.modules:
                sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module):
                if self._is_plugin_class(obj):
                    logger.debug(f"Found plugin class {name} in {file_path}")
                    try:
                        plugin = obj()
                        logger.debug(f"Successfully instantiated {name}")

                        # Check version compatibility
                        if not self.version_manager.is_compatible(plugin.metadata):
                            logger.warning(
                                f"Plugin {plugin.metadata.name} is not compatible with current app version",
                            )
                            continue

                        self._loaded_modules.add(str(file_path))
                        logger.info(
                            f"Loaded plugin from {file_path}: {plugin.metadata.name}",
                        )
                        return plugin
                    except Exception as instantiation_error:
                        logger.error(
                            f"Failed to instantiate plugin class {name}: {instantiation_error}",
                        )
                        continue

        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")

        return None

    def _load_v4_plugin(self, plugin_dir: Path) -> PluginInterface | None:
        """Load a v4 modular plugin from a directory."""
        try:
            plugin_name = plugin_dir.name
            init_file = plugin_dir / "__init__.py"

            if not init_file.exists():
                logger.debug(f"No __init__.py found in {plugin_dir}")
                return None

            # Import the plugin module
            module_name = f"app.plugins.{plugin_name}"
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                logger.error(f"Failed to import v4 plugin {plugin_name}: {e}")
                return None

            # Check if it has the required components
            if not (
                hasattr(module, "register_plugin")
                and hasattr(module, "PLUGIN_METADATA")
            ):
                logger.debug(f"v4 plugin {plugin_name} missing required components")
                return None

            # Create a v4 plugin adapter
            plugin_adapter = V4PluginAdapter(module, plugin_name)

            # Check version compatibility
            if not self.version_manager.is_compatible(plugin_adapter.metadata):
                logger.warning(
                    f"v4 plugin {plugin_name} is not compatible with current app version",
                )
                return None

            logger.info(f"Loaded v4 plugin: {plugin_name}")
            return plugin_adapter

        except Exception as e:
            logger.error(f"Failed to load v4 plugin from {plugin_dir}: {e}")
            return None

    def _is_plugin_class(self, obj: Any) -> bool:
        """Check if an object is a valid plugin class."""
        if not inspect.isclass(obj):
            return False

        # Check if it's a subclass of PluginBase
        is_pluginbase_subclass = False
        try:
            is_pluginbase_subclass = issubclass(obj, PluginBase)
        except Exception as e:
            logger.debug(f"issubclass check failed for {obj}: {e}")

        # Check if it has the required methods
        has_required_methods = (
            hasattr(obj, "initialize")
            and hasattr(obj, "startup")
            and hasattr(obj, "shutdown")
        )

        result = is_pluginbase_subclass or has_required_methods

        if obj.__name__.endswith("Plugin"):
            logger.debug(
                f"Plugin class check for {obj.__name__}: "
                f"isclass={inspect.isclass(obj)}, "
                f"issubclass={is_pluginbase_subclass}, "
                f"has_methods={has_required_methods}, "
                f"result={result}",
            )

        return result


class PluginManager:
    """Main plugin management system.
    Coordinates discovery, loading, initialization, and lifecycle management.
    """

    def __init__(self, app: FastAPI, app_version: str = "1.0.0") -> None:
        self.app = app
        self.version_manager = VersionManager(app_version)
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.version_manager)
        self.context = PluginContext(app)
        self._initialized = False

    async def discover_and_load_plugins(self, search_paths: list[str]) -> None:
        """Discover and load plugins from search paths."""
        logger.info(f"Discovering plugins from: {search_paths}")

        # Discover plugins
        discovered_plugins = self.loader.discover_plugins(search_paths)

        # Register discovered plugins
        for plugin in discovered_plugins:
            try:
                self.registry.register(plugin)
                plugin.metadata.status = (
                    PluginStatus.LOADED
                )  # Fixed: Set to LOADED after registration
                logger.debug(f"Plugin {plugin.metadata.name} status set to LOADED")
            except Exception as e:
                logger.error(f"Failed to register plugin {plugin.metadata.name}: {e}")
                plugin.metadata.status = PluginStatus.ERROR

        logger.info(f"Discovered and loaded {len(discovered_plugins)} plugins")

    async def initialize_plugins(self) -> None:
        """Initialize all loaded plugins in dependency order."""
        if self._initialized:
            return

        loading_order = self.registry.get_loading_order()
        logger.info(f"Initializing plugins in order: {loading_order}")

        for plugin_name in loading_order:
            plugin = self.registry.get_plugin(plugin_name)
            if not plugin:
                continue

            try:
                await plugin.initialize(self.app, self.context)

                # FORCE status to INITIALIZED here - this is the fix
                plugin.metadata.status = PluginStatus.INITIALIZED
                logger.info(f"Plugin {plugin_name} status FORCED to INITIALIZED")

                # Register routes
                routes = plugin.get_routes()
                for route in routes:
                    self.app.include_router(route)
                    logger.debug(f"Registered route from plugin {plugin_name}")

                # Register middleware - FIX the middleware registration
                middleware = plugin.get_middleware()
                for mw in middleware:
                    # Fix middleware instantiation
                    if hasattr(mw, "__name__") and "Middleware" in mw.__name__:
                        # This is a middleware class, not instance
                        self.app.add_middleware(mw)
                    else:
                        # This might be an instance or callable
                        self.app.add_middleware(type(mw))
                    logger.debug(f"Registered middleware from plugin {plugin_name}")

                # Register Procrastinate blueprint if plugin has one
                if hasattr(plugin, "get_blueprint"):
                    try:
                        blueprint = plugin.get_blueprint()
                        if blueprint:
                            from app.utils.procrastinate_manager import (
                                register_plugin_blueprint,
                            )

                            namespace = f"{plugin_name}_tasks"
                            register_plugin_blueprint(blueprint, namespace)
                            logger.info(
                                f"Registered Procrastinate blueprint for plugin: {plugin_name}",
                            )
                    except Exception as blueprint_error:
                        logger.warning(
                            f"Failed to register blueprint for plugin {plugin_name}: {blueprint_error}",
                        )

                logger.info(
                    f"Initialized plugin: {plugin_name} (Status: {plugin.metadata.status.value})",
                )

                # Emit plugin initialized event
                self.context.event_bus.emit(
                    "plugin_initialized", plugin_name=plugin_name,
                )

            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
                plugin.metadata.status = PluginStatus.ERROR
                import traceback

                logger.error(traceback.format_exc())

        self._initialized = True
        logger.info("All plugins initialized")

    async def startup_plugins(self) -> None:
        """Call startup on all initialized plugins."""
        for plugin_name, plugin in self.registry.get_all_plugins().items():
            if plugin.metadata.status == PluginStatus.INITIALIZED:
                try:
                    await plugin.startup()
                    plugin.metadata.status = PluginStatus.ENABLED
                    logger.info(
                        f"Started plugin: {plugin_name} (Status: {plugin.metadata.status.value})",
                    )
                except Exception as e:
                    logger.error(f"Failed to start plugin {plugin_name}: {e}")
                    plugin.metadata.status = PluginStatus.ERROR
                    import traceback

                    logger.error(traceback.format_exc())

    async def shutdown_plugins(self) -> None:
        """Call shutdown on all plugins in reverse order."""
        loading_order = self.registry.get_loading_order()
        for plugin_name in reversed(loading_order):
            plugin = self.registry.get_plugin(plugin_name)
            if plugin and plugin.metadata.status == PluginStatus.ENABLED:
                try:
                    await plugin.shutdown()
                    plugin.metadata.status = PluginStatus.DISABLED
                    logger.debug(f"Shut down plugin: {plugin_name}")
                except Exception as e:
                    logger.error(f"Failed to shut down plugin {plugin_name}: {e}")

    def get_plugin_status(self) -> dict[str, dict]:
        """Get status of all plugins."""
        status = {}
        for name, plugin in self.registry.get_all_plugins().items():
            metadata = plugin.metadata
            status[name] = {
                "version": metadata.version,
                "status": metadata.status.value,
                "description": metadata.description,
                "dependencies": metadata.dependencies,
                "priority": metadata.priority,
            }
        return status

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a disabled plugin."""
        plugin = self.registry.get_plugin(plugin_name)
        if plugin and plugin.metadata.status == PluginStatus.DISABLED:
            # Could implement hot-loading here
            plugin.metadata.status = PluginStatus.ENABLED
            return True
        return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable an enabled plugin."""
        plugin = self.registry.get_plugin(plugin_name)
        if plugin and plugin.metadata.status == PluginStatus.ENABLED:
            # Could implement hot-unloading here
            plugin.metadata.status = PluginStatus.DISABLED
            return True
        return False


# Global plugin manager instance
_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager | None:
    """Get the global plugin manager instance."""
    return _plugin_manager


def initialize_plugin_system(app: FastAPI, app_version: str = "1.0.0") -> PluginManager:
    """Initialize the plugin system for the FastAPI app."""
    global _plugin_manager
    _plugin_manager = PluginManager(app, app_version)
    return _plugin_manager
