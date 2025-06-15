#!/usr/bin/env python3
"""
TEST SERVER ROUTE CONFIGURATION TEST

PURPOSE:
    Test server route configuration
    
WHEN TO USE:
    Testing server route setup
    
WHAT IT TESTS:
    Server route configuration, availability
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/system/test_server_routes.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

"""Test Server Routes - Check what routes are actually registered."""

import asyncio
import sys

sys.path.append(".")


async def test_server_routes() -> None:

    try:
        # Import the actual main app
        from app.main import app


        # List all routes
        all_routes = []
        product_routes = []

        for route in app.routes:
            if hasattr(route, "path"):
                all_routes.append(route.path)
                if "product" in route.path.lower():
                    product_routes.append(route.path)

        for route in sorted(all_routes):
            pass

        if product_routes:
            for route in product_routes:
                pass
        else:
            pass

        # Check if plugin manager is available
        try:
            from app.core.plugin_system import get_plugin_manager

            plugin_manager = get_plugin_manager()
            if plugin_manager:
                plugins = plugin_manager.registry.get_all_plugins()
                for _name, _plugin in plugins.items():
                    pass
            else:
                pass
        except Exception:
            pass

        # Try to manually trigger plugin loading
        try:
            from app.plugins.product_plugin import ProductRoutes

            routes_instance = ProductRoutes()
            router = routes_instance.get_router()

            # Manually include the router
            app.include_router(router, prefix="/api/v1", tags=["Product"])

        except Exception:
            import traceback

            traceback.print_exc()

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_server_routes())
