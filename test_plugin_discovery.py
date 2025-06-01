#!/usr/bin/env python3
"""
Test Plugin Discovery

Quick test to check if plugins are being discovered and routes registered.
"""

import asyncio
import sys
sys.path.append('.')

from app.core.plugin_system import PluginManager
from fastapi import FastAPI

async def test_plugin_discovery():
    """Test plugin discovery and route registration"""
    
    print("🔍 Testing Plugin Discovery")
    print("=" * 40)
    
    # Create a test FastAPI app
    app = FastAPI()
    
    # Initialize plugin manager
    plugin_manager = PluginManager(app, app_version="1.0.0")
    
    # Discover plugins
    plugin_search_paths = ["app/plugins"]
    await plugin_manager.discover_and_load_plugins(plugin_search_paths)
    
    # Get discovered plugins
    plugins = plugin_manager.registry.get_all_plugins()
    print(f"📊 Discovered {len(plugins)} plugins:")
    
    for name, plugin in plugins.items():
        print(f"   🔌 {name}: {plugin.metadata.description}")
        print(f"      Status: {plugin.metadata.status.value}")
        print(f"      Version: {plugin.metadata.version}")
        
        # Check routes
        routes = plugin.get_routes()
        print(f"      Routes: {len(routes)} router(s)")
        
        if routes:
            for router in routes:
                if hasattr(router, 'routes'):
                    for route in router.routes:
                        if hasattr(route, 'path') and hasattr(route, 'methods'):
                            print(f"         {list(route.methods)[0]} {route.path}")
        print()
    
    # Initialize plugins
    await plugin_manager.initialize_plugins()
    
    # Check app routes after initialization
    print("🛣️  App Routes After Plugin Initialization:")
    print("=" * 50)
    
    route_count = 0
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = getattr(route, 'methods', ['GET'])
            print(f"   {list(methods)[0] if methods else 'GET'} {route.path}")
            route_count += 1
        elif hasattr(route, 'path_regex'):
            print(f"   MOUNT {route.path}")
            route_count += 1
    
    print(f"\n📊 Total routes registered: {route_count}")
    
    # Check plugin status after initialization
    print("\n📊 Plugin Status After Initialization:")
    print("=" * 45)
    
    for name, plugin in plugins.items():
        print(f"   🔌 {name}: {plugin.metadata.status.value}")

if __name__ == "__main__":
    asyncio.run(test_plugin_discovery()) 