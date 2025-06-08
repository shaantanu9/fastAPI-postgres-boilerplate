#!/usr/bin/env python3
"""Debug Product plugin loading issue."""

import sys

sys.path.append(".")

import importlib.util
import inspect
from pathlib import Path


def debug_product_plugin() -> None:
    """Debug Product plugin loading step by step."""
    # Step 1: Load module like plugin system does
    file_path = Path("app/plugins/product_plugin.py")
    module_name = file_path.stem

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

    except Exception:
        import traceback

        traceback.print_exc()
        return

    # Step 2: Find plugin classes
    plugin_classes = []

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and name.endswith("Plugin"):
            plugin_classes.append((name, obj))

    # Step 3: Test instantiation
    for name, cls in plugin_classes:
        try:
            cls()
        except Exception:
            import traceback

            traceback.print_exc()

    # Step 4: Check for multiple PluginBase classes
    pluginbase_classes = []
    for name, obj in inspect.getmembers(module):
        if hasattr(obj, "__name__") and "PluginBase" in str(obj):
            pluginbase_classes.append((name, obj))

    for name, obj in pluginbase_classes:
        pass

    # Step 5: Compare with known working plugin
    try:
        from app.plugins.order_plugin import OrderPlugin

        OrderPlugin()



        # Check if they're the same class

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_product_plugin()
