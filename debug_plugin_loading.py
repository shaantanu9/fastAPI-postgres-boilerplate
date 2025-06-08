#!/usr/bin/env python3
"""Debug Plugin Loading."""

import asyncio
import sys

sys.path.append(".")


async def debug_plugin_loading() -> None:

    from fastapi import FastAPI

    from app.core.plugin_system import PluginManager

    app = FastAPI()
    manager = PluginManager(app, "1.0.0")

    # Step 1: Check plugin discovery
    search_paths = ["app/plugins"]

    for search_path in search_paths:
        from pathlib import Path

        path = Path(search_path)

        if path.exists():
            # Check for v4 plugins
            plugin_dirs = [
                d for d in path.iterdir() if d.is_dir() and d.name.endswith("_plugin")
            ]
            for plugin_dir in plugin_dirs:
                init_file = plugin_dir / "__init__.py"

                if init_file.exists():
                    # Check if it has required components
                    try:
                        with open(init_file) as f:
                            f.read()
                    except Exception:
                        pass

    # Step 2: Try to discover plugins
    try:
        await manager.discover_and_load_plugins(search_paths)
        plugins = manager.registry.get_all_plugins()
        for _name, _plugin in plugins.items():
            pass
    except Exception:
        import traceback

        traceback.print_exc()

    # Step 3: Try to initialize plugins
    try:
        await manager.initialize_plugins()

        # Check routes after initialization
        for route in app.routes:
            if hasattr(route, "path"):
                pass

    except Exception:
        import traceback

        traceback.print_exc()

    # Step 4: Test manual plugin import
    try:
        # Test register_plugin function
        from app.core.plugin_system import PluginContext
        from app.plugins.product_plugin import register_plugin

        context = PluginContext(app)

        register_plugin(app, context)

        # Check routes after manual registration
        product_routes = []
        for route in app.routes:
            if hasattr(route, "path") and "product" in route.path.lower():
                product_routes.append(route.path)

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_plugin_loading())
