#!/usr/bin/env python3
"""Test script to manually register the Product plugin."""

import asyncio
import sys

sys.path.append(".")


async def test_manual_registration() -> bool | None:
    """Test manual plugin registration."""
    try:
        # Import required components
        from fastapi import FastAPI

        from app.core.plugin_system import PluginManager
        from app.plugins.product_plugin import ProductPlugin

        # Create a test FastAPI app
        app = FastAPI()

        # Create plugin manager
        manager = PluginManager(app, "1.0.0")

        # Create plugin instance
        plugin = ProductPlugin()

        # Register plugin manually
        manager.registry.register(plugin)

        # Initialize plugin
        await plugin.initialize(app, manager.context)

        # Get routes
        routes = plugin.get_routes()

        # Register routes with app
        for route in routes:
            app.include_router(route)

        # Check if routes are in the app
        route_paths = [route.path for route in app.routes]
        [path for path in route_paths if "product" in path]

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_manual_registration())
    if success:
        pass
    else:
        pass
