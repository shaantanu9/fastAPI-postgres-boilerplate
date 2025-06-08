#!/usr/bin/env python3
"""Debug script to test plugin discovery and loading."""

import sys

sys.path.append(".")

from pathlib import Path

from app.core.plugin_system import PluginLoader, VersionManager


def debug_plugin_discovery() -> None:
    """Debug plugin discovery process."""
    # Initialize version manager and loader
    version_manager = VersionManager("1.0.0")
    loader = PluginLoader(version_manager)

    # Test plugin discovery
    search_paths = ["app/plugins"]


    for search_path in search_paths:
        path = Path(search_path)
        if not path.exists():
            continue


        # List all Python files
        list(path.glob("*.py"))

        # Try to discover plugins from this directory
        plugins = loader._discover_from_directory(path)

        for _plugin in plugins:
            pass

    # Test overall discovery
    all_plugins = loader.discover_plugins(search_paths)

    for _plugin in all_plugins:
        pass


if __name__ == "__main__":
    debug_plugin_discovery()
