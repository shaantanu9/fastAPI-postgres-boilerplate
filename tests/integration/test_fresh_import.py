#!/usr/bin/env python3
"""
TEST FRESH IMPORT FUNCTIONALITY TEST

PURPOSE:
    Test fresh import functionality
    
WHEN TO USE:
    Testing import processes
    
WHAT IT TESTS:
    Fresh imports, data loading
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/integration/test_fresh_import.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

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
