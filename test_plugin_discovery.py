#!/usr/bin/env python3
"""Test Plugin Discovery.

Quick test to check if plugins are being discovered and routes registered.
"""

import asyncio
import sys

sys.path.append(".")

from fastapi import FastAPI

from app.core.plugin_system import PluginManager


async def test_plugin_discovery() -> None:
    """Test plugin discovery and route registration."""
    # Create a test FastAPI app
    app = FastAPI()

    # Initialize plugin manager
    plugin_manager = PluginManager(app, app_version="1.0.0")

    # Discover plugins
    plugin_search_paths = ["app/plugins"]
    await plugin_manager.discover_and_load_plugins(plugin_search_paths)

    # Get discovered plugins
    plugins = plugin_manager.registry.get_all_plugins()

    for plugin in plugins.values():

        # Check routes
        routes = plugin.get_routes()

        if routes:
            for router in routes:
                if hasattr(router, "routes"):
                    for route in router.routes:
                        if hasattr(route, "path") and hasattr(route, "methods"):
                            pass

    # Initialize plugins
    await plugin_manager.initialize_plugins()

    # Check app routes after initialization

    route_count = 0
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            getattr(route, "methods", ["GET"])
            route_count += 1
        elif hasattr(route, "path_regex"):
            route_count += 1


    # Check plugin status after initialization

    for plugin in plugins.values():
        pass


if __name__ == "__main__":
    asyncio.run(test_plugin_discovery())
