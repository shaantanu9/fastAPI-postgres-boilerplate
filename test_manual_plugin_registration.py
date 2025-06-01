#!/usr/bin/env python3
"""
Test script to manually register the Product plugin
"""

import sys
import asyncio
sys.path.append('.')

async def test_manual_registration():
    """Test manual plugin registration"""
    print("🧪 Testing Manual Plugin Registration")
    print("=" * 50)
    
    try:
        # Import required components
        from app.plugins.product_plugin import ProductPlugin
        from app.core.plugin_system import PluginManager, PluginContext
        from fastapi import FastAPI
        
        # Create a test FastAPI app
        app = FastAPI()
        
        # Create plugin manager
        manager = PluginManager(app, "1.0.0")
        
        # Create plugin instance
        plugin = ProductPlugin()
        print(f"✅ Plugin created: {plugin.metadata.name}")
        
        # Register plugin manually
        manager.registry.register(plugin)
        print(f"✅ Plugin registered: {plugin.metadata.name}")
        
        # Initialize plugin
        await plugin.initialize(app, manager.context)
        print(f"✅ Plugin initialized: {plugin.metadata.name}")
        
        # Get routes
        routes = plugin.get_routes()
        print(f"✅ Plugin routes: {len(routes)} routes found")
        
        # Register routes with app
        for route in routes:
            app.include_router(route)
        print(f"✅ Routes registered with FastAPI app")
        
        # Check if routes are in the app
        route_paths = [route.path for route in app.routes]
        product_routes = [path for path in route_paths if 'product' in path]
        print(f"📋 Product routes in app: {product_routes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Manual registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_manual_registration())
    if success:
        print("\n🎉 Manual registration successful!")
    else:
        print("\n💥 Manual registration failed!") 