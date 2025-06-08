import asyncio

from app.core.plugin_system import PluginManager
from app.main import app


async def test_plugin_system() -> None:

    # Create plugin manager
    plugin_manager = PluginManager(app, "1.0.0")

    # Step 1: Discover and load
    await plugin_manager.discover_and_load_plugins(["app/plugins"])
    plugins = plugin_manager.registry.get_all_plugins()

    for _name, _plugin in plugins.items():
        pass

    # Step 2: Initialize
    try:
        await plugin_manager.initialize_plugins()
    except Exception:
        import traceback

        traceback.print_exc()

    # Step 3: Check plugin status after initialization
    status = plugin_manager.get_plugin_status()
    for _name, _info in status.items():
        pass

    # Step 4: Check routes after initialization
    all_routes = [r for r in app.routes if hasattr(r, "path")]
    order_routes = [r for r in all_routes if "/orders" in r.path]


    if order_routes:
        for route in order_routes:
            pass
    else:

        # Debug: Check what routes are there
        for route in all_routes[:10]:
            pass

    # Step 5: Test Order plugin specifically
    order_plugin = plugin_manager.registry.get_plugin("order_plugin")
    if order_plugin:

        try:
            routes = order_plugin.get_routes()

            for _i, route in enumerate(routes):
                if hasattr(route, "routes"):
                    for endpoint in route.routes[:3]:  # Show first 3
                        if hasattr(endpoint, "path"):
                            pass
        except Exception:
            pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(test_plugin_system())
