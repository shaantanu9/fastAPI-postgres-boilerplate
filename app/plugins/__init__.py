"""
Plugins package for the FastAPI application.

This package contains all plugins that extend the application functionality.
Each plugin should be in its own subdirectory or file.
"""

from app.core.plugin_system import (
    PluginInterface,
    PluginBase,
    PluginMetadata,
    PluginStatus,
    get_plugin_manager
)

__all__ = [
    "PluginInterface",
    "PluginBase", 
    "PluginMetadata",
    "PluginStatus",
    "get_plugin_manager"
] 