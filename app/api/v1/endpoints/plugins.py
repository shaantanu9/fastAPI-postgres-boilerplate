"""Plugin Management API Endpoints.

Provides REST API for managing plugins at runtime:
- View plugin status
- Enable/disable plugins
- View plugin configurations
- Monitor plugin health
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.plugin_system import get_plugin_manager


# Response models
class PluginStatusResponse(BaseModel):
    name: str
    version: str
    status: str
    description: str
    dependencies: list[str]
    priority: int
    tags: list[str]


class PluginListResponse(BaseModel):
    plugins: list[PluginStatusResponse]
    total_count: int
    enabled_count: int
    disabled_count: int
    error_count: int


class PluginOperationResponse(BaseModel):
    success: bool
    message: str
    plugin_name: str
    operation: str


class SystemHealthResponse(BaseModel):
    overall_status: str
    plugin_count: int
    plugins_healthy: int
    plugins_warning: int
    plugins_error: int
    system_services: dict[str, bool]


router = APIRouter()


@router.get("/plugins", response_model=PluginListResponse, tags=["Plugin Management"])
async def list_plugins(
    status_filter: Annotated[str | None, Query(description="Filter by status: enabled, disabled, error")] = None,
    tag_filter: Annotated[str | None, Query(description="Filter by tag")] = None,
):
    """Get list of all plugins with their status and metadata."""
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    plugin_status = plugin_manager.get_plugin_status()

    plugins = []
    enabled_count = 0
    disabled_count = 0
    error_count = 0

    for name, info in plugin_status.items():
        plugin_data = PluginStatusResponse(
            name=name,
            version=info["version"],
            status=info["status"],
            description=info["description"],
            dependencies=info["dependencies"],
            priority=info["priority"],
            tags=plugin_manager.registry.get_metadata(name).tags
            if plugin_manager.registry.get_metadata(name)
            else [],
        )

        # Apply filters
        if status_filter and info["status"] != status_filter:
            continue

        if tag_filter:
            plugin_tags = (
                plugin_manager.registry.get_metadata(name).tags
                if plugin_manager.registry.get_metadata(name)
                else []
            )
            if tag_filter not in plugin_tags:
                continue

        plugins.append(plugin_data)

        # Count by status
        if info["status"] == "enabled":
            enabled_count += 1
        elif info["status"] == "disabled":
            disabled_count += 1
        elif info["status"] == "error":
            error_count += 1

    return PluginListResponse(
        plugins=plugins,
        total_count=len(plugins),
        enabled_count=enabled_count,
        disabled_count=disabled_count,
        error_count=error_count,
    )


@router.get(
    "/plugins/{plugin_name}", response_model=dict[str, Any], tags=["Plugin Management"],
)
async def get_plugin_details(plugin_name: str):
    """Get detailed information about a specific plugin.

    Retrieves comprehensive details about a plugin including its configuration,
    dependencies, hooks, extension points, and runtime statistics.

    Args:
        plugin_name (str): The name of the plugin to retrieve details for.

    Returns:
        Dict[str, Any]: Detailed plugin information including configuration,
                       status, dependencies, and runtime statistics.

    Raises:
        HTTPException: If the plugin system is not initialized or the plugin is not found.

    """
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    plugin = plugin_manager.registry.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found",
        )

    metadata = plugin.metadata

    return {
        "name": metadata.name,
        "version": metadata.version,
        "status": metadata.status.value,
        "description": metadata.description,
        "dependencies": metadata.dependencies,
        "priority": metadata.priority,
        "tags": metadata.tags,
    }


@router.post(
    "/plugins/{plugin_name}/enable",
    response_model=PluginOperationResponse,
    tags=["Plugin Management"],
)
async def enable_plugin(plugin_name: str):
    """Enable a disabled plugin.

    Activates a previously disabled plugin, making its functionality available
    to the application. This operation may trigger dependency resolution and
    initialization of the plugin.

    Args:
        plugin_name (str): The name of the plugin to enable.

    Returns:
        PluginOperationResponse: Result of the enable operation including success status
                                and any relevant messages.

    Raises:
        HTTPException: If the plugin system is not initialized, the plugin is not found,
                      or the plugin cannot be enabled due to dependency issues.

    """
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    success = plugin_manager.enable_plugin(plugin_name)

    if success:
        return PluginOperationResponse(
            success=True,
            message=f"Plugin '{plugin_name}' enabled successfully",
            plugin_name=plugin_name,
            operation="enable",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Failed to enable plugin '{plugin_name}'. Plugin may not exist or is already enabled.",
    )


@router.post(
    "/plugins/{plugin_name}/disable",
    response_model=PluginOperationResponse,
    tags=["Plugin Management"],
)
async def disable_plugin(plugin_name: str):
    """Disable an enabled plugin.

    Deactivates an active plugin, removing its functionality from the application.
    This operation may trigger cleanup routines and notify dependent plugins.

    Args:
        plugin_name (str): The name of the plugin to disable.

    Returns:
        PluginOperationResponse: Result of the disable operation including success status
                                and any relevant messages.

    Raises:
        HTTPException: If the plugin system is not initialized, the plugin is not found,
                      or the plugin cannot be disabled due to dependency issues.

    """
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    success = plugin_manager.disable_plugin(plugin_name)

    if success:
        return PluginOperationResponse(
            success=True,
            message=f"Plugin '{plugin_name}' disabled successfully",
            plugin_name=plugin_name,
            operation="disable",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Failed to disable plugin '{plugin_name}'. Plugin may not exist or is already disabled.",
    )


@router.get(
    "/plugins/system/health",
    response_model=SystemHealthResponse,
    tags=["Plugin Management"],
)
async def get_system_health():
    """Get overall system health including plugin status.

    Provides a comprehensive health check of the plugin system and its components,
    including counts of healthy and problematic plugins, system service availability,
    and overall system status.

    Returns:
        SystemHealthResponse: System health information including plugin counts by status
                            and system service availability.

    Raises:
        HTTPException: If the plugin system is not initialized or health check fails.

    """
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    plugin_status = plugin_manager.get_plugin_status()

    plugins_healthy = 0
    plugins_warning = 0
    plugins_error = 0

    for info in plugin_status.values():
        if info["status"] == "enabled":
            plugins_healthy += 1
        elif info["status"] == "disabled":
            plugins_warning += 1
        elif info["status"] == "error":
            plugins_error += 1

    # Check system services
    system_services = {
        "plugin_manager": plugin_manager is not None,
        "event_bus": plugin_manager.context.event_bus is not None,
        "service_registry": len(plugin_manager.context.services) > 0,
    }

    # Check for specific services
    monitoring_service = plugin_manager.context.get_service("monitoring")
    cache_service = plugin_manager.context.get_service("cache")

    system_services.update(
        {
            "monitoring": monitoring_service is not None,
            "cache": cache_service is not None,
        },
    )

    # Determine overall status
    overall_status = "healthy"
    if plugins_error > 0:
        overall_status = "degraded"
    elif plugins_warning > len(plugin_status) // 2:  # More than half disabled
        overall_status = "warning"

    return SystemHealthResponse(
        overall_status=overall_status,
        plugin_count=len(plugin_status),
        plugins_healthy=plugins_healthy,
        plugins_warning=plugins_warning,
        plugins_error=plugins_error,
        system_services=system_services,
    )


@router.get("/plugins/events/history", tags=["Plugin Management"])
async def get_event_history(limit: Annotated[int, Query(ge=1, le=1000)] = 50):
    """Get recent plugin system events.

    Retrieves a chronological history of events from the plugin system, such as
    plugin loading, activation, deactivation, and errors. Useful for debugging
    and monitoring plugin activity.

    Args:
        limit (int): Maximum number of events to return (1-1000).

    Returns:
        Dict[str, Any]: List of plugin system events with timestamps, event types,
                       and related information.

    Raises:
        HTTPException: If the plugin system is not initialized or event retrieval fails.

    """
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    event_history = plugin_manager.context.event_bus.get_event_history()

    # Return last N events
    recent_events = (
        event_history[-limit:] if len(event_history) > limit else event_history
    )

    return {
        "events": recent_events,
        "total_events": len(event_history),
        "returned_count": len(recent_events),
    }


@router.get("/plugins/services", tags=["Plugin Management"])
async def get_registered_services():
    """Get list of all registered services.

    Returns a mapping of service types to the plugins that provide implementations
    of those services. Useful for understanding the available service ecosystem
    and plugin capabilities.

    Returns:
        Dict[str, Any]: Dictionary mapping service types to lists of plugin names
                       that provide those services.

    Raises:
        HTTPException: If the plugin system is not initialized or service discovery fails.

    """
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    services = {}
    for name, service in plugin_manager.context.services.items():
        services[name] = {
            "type": str(type(service).__name__),
            "module": str(type(service).__module__),
            "available": service is not None,
        }

    return {"services": services, "service_count": len(services)}


@router.get("/plugins/loading-order", tags=["Plugin Management"])
async def get_loading_order():
    """Get the plugin loading order based on dependencies.

    Calculates and returns the order in which plugins are loaded based on their
    dependencies. This information is useful for understanding the initialization
    sequence and diagnosing dependency-related issues.

    Returns:
        Dict[str, Any]: Information about plugin loading order, including the ordered list
                      of plugins and any circular dependency warnings.

    Raises:
        HTTPException: If the plugin system is not initialized or dependency resolution fails.

    """
    plugin_manager = get_plugin_manager()
    if not plugin_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    loading_order = plugin_manager.registry.get_loading_order()

    # Get detailed info for each plugin in order
    ordered_plugins = []
    for plugin_name in loading_order:
        metadata = plugin_manager.registry.get_metadata(plugin_name)
        if metadata:
            ordered_plugins.append(
                {
                    "name": plugin_name,
                    "priority": metadata.priority,
                    "dependencies": metadata.dependencies,
                    "status": metadata.status.value,
                },
            )

    return {"loading_order": ordered_plugins, "total_plugins": len(ordered_plugins)}
