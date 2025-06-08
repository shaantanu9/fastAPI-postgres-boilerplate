import asyncio

from app.main import app


async def test_routes() -> None:

    # Check if routes are registered
    order_routes = [r for r in app.routes if hasattr(r, "path") and "/orders" in r.path]

    for route in order_routes:
        ", ".join(route.methods) if hasattr(route, "methods") else "Unknown"


    # Check plugin status
    try:
        from app.main import _plugin_manager

        if _plugin_manager:
            status = _plugin_manager.get_plugin_status()
            for _name, _info in status.items():
                pass
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(test_routes())
