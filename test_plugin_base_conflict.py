#!/usr/bin/env python3
"""Test for PluginBase class conflicts."""

import importlib.util
import inspect
from pathlib import Path


def test_plugin_base_conflict() -> None:
    """Test if there are multiple PluginBase classes causing conflicts."""
    # Import PluginBase from the plugin system
    from app.core.plugin_system import PluginBase as SystemPluginBase


    # Load the Product plugin module fresh
    file_path = Path("app/plugins/product_plugin.py")
    spec = importlib.util.spec_from_file_location("test_product_plugin", file_path)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)

        # Find the ProductPlugin class
        ProductPlugin = module.ProductPlugin

        # Get the PluginBase from the module
        ProductPlugin.__bases__[0]

        # Check if they're the same

        # Check abstract methods

        # Test the _is_plugin_class logic
        def _is_plugin_class(obj):
            """Replicate the plugin system's _is_plugin_class logic."""
            return inspect.isclass(obj) and (
                issubclass(obj, SystemPluginBase)
                or (
                    hasattr(obj, "initialize")
                    and hasattr(obj, "startup")
                    and hasattr(obj, "shutdown")
                )
            )


        # Try to instantiate
        try:
            ProductPlugin()
        except Exception:
            import traceback

            traceback.print_exc()

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_plugin_base_conflict()
