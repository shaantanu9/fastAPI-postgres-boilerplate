#!/usr/bin/env python3
"""Test fresh import of Product plugin."""

import importlib.util
from pathlib import Path


def test_fresh_import() -> None:
    """Test a completely fresh import of the Product plugin."""
    # Load the module fresh
    file_path = Path("app/plugins/product_plugin.py")
    spec = importlib.util.spec_from_file_location("fresh_product_plugin", file_path)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)

        # Find the ProductPlugin class
        ProductPlugin = module.ProductPlugin

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
    test_fresh_import()
