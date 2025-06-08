#!/usr/bin/env python3
"""Test v4 Plugin Discovery."""

import asyncio
import contextlib
import sys

sys.path.append(".")


async def test_v4_discovery() -> None:
    from fastapi import FastAPI

    from app.core.plugin_system import PluginManager


    app = FastAPI()
    manager = PluginManager(app, "1.0.0")

    # Discover plugins
    await manager.discover_and_load_plugins(["app/plugins"])

    # Check discovered plugins
    plugins = manager.registry.get_all_plugins()

    for plugin in plugins.values():
        "v4" if "V4PluginAdapter" in str(type(plugin)) else "v3"

        # Check routes
        with contextlib.suppress(Exception):
            plugin.get_routes()

    # Test initialization

    try:
        await manager.initialize_plugins()

        # Check FastAPI routes
        len([r for r in app.routes if hasattr(r, "path")])

        # List some routes
        for route in app.routes:
            if hasattr(route, "path") and (
                "/products" in route.path or "/orders" in route.path
            ):
                (
                    ", ".join(route.methods) if hasattr(route, "methods") else "Unknown"
                )

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_v4_discovery())
