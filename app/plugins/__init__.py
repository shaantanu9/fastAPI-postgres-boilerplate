"""Plugins package for the FastAPI application.

This package contains all plugins that extend the application functionality.
Each plugin should be in its own subdirectory or file.
"""

from app.core.plugin_system import (
    PluginBase,
    PluginInterface,
    PluginMetadata,
    PluginStatus,
    get_plugin_manager,
)

__all__ = [
    "PluginBase",
    "PluginInterface",
    "PluginMetadata",
    "PluginStatus",
    "get_plugin_manager",
]
