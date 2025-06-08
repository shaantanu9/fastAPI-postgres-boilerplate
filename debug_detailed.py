#!/usr/bin/env python3
"""Detailed debug script to trace plugin loading."""

import importlib.util
import inspect
import sys
from pathlib import Path

sys.path.append(".")



def debug_module_loading() -> None:
    """Debug the module loading process step by step."""
    file_path = Path("app/plugins/product_plugin.py")
    module_name = file_path.stem


    try:
        # Step 1: Create module spec
        spec = importlib.util.spec_from_file_location(module_name, file_path)

        # Step 2: Create module
        module = importlib.util.module_from_spec(spec)

        # Step 3: Add to sys.modules
        sys.modules[module_name] = module

        # Step 4: Execute module
        spec.loader.exec_module(module)

        # Step 5: Find plugin classes
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name.endswith("Plugin"):

                # Check metadata property
                getattr(obj, "metadata", None)

                # Check abstract methods
                getattr(obj, "__abstractmethods__", set())

                # Try to instantiate
                try:
                    obj()
                except Exception:
                    import traceback

                    traceback.print_exc()


    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_module_loading()
