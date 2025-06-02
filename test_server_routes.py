#!/usr/bin/env python3
"""
Test Server Routes - Check what routes are actually registered
"""
import asyncio
import sys
sys.path.append('.')

async def test_server_routes():
    print("🧪 Testing Server Routes")
    print("=" * 30)
    
    try:
        # Import the actual main app
        from app.main import app
        
        print(f"✅ Successfully imported main app")
        print(f"📊 Total routes: {len(app.routes)}")
        
        # List all routes
        all_routes = []
        product_routes = []
        
        for route in app.routes:
            if hasattr(route, 'path'):
                all_routes.append(route.path)
                if 'product' in route.path.lower():
                    product_routes.append(route.path)
        
        print(f"\n📋 All routes ({len(all_routes)}):")
        for route in sorted(all_routes):
            print(f"  - {route}")
        
        print(f"\n🛍️ Product routes ({len(product_routes)}):")
        if product_routes:
            for route in product_routes:
                print(f"  - {route}")
        else:
            print("  ❌ No product routes found!")
        
        # Check if plugin manager is available
        print(f"\n🔌 Plugin Manager Status:")
        try:
            from app.core.plugin_system import get_plugin_manager
            plugin_manager = get_plugin_manager()
            if plugin_manager:
                print("  ✅ Plugin manager available")
                plugins = plugin_manager.registry.get_all_plugins()
                print(f"  📊 Registered plugins: {len(plugins)}")
                for name, plugin in plugins.items():
                    print(f"    - {name}: {plugin.metadata.status.value}")
            else:
                print("  ❌ Plugin manager not available")
        except Exception as e:
            print(f"  ❌ Error accessing plugin manager: {e}")
        
        # Try to manually trigger plugin loading
        print(f"\n🔄 Manual Plugin Loading Test:")
        try:
            from app.plugins.product_plugin import ProductRoutes
            routes_instance = ProductRoutes()
            router = routes_instance.get_router()
            print(f"  ✅ Product router created successfully")
            print(f"  📊 Router routes: {len(router.routes)}")
            
            # Manually include the router
            app.include_router(router, prefix="/api/v1", tags=["Product"])
            print(f"  ✅ Manually included product router")
            print(f"  📊 App routes after manual inclusion: {len(app.routes)}")
            
        except Exception as e:
            print(f"  ❌ Manual plugin loading failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Failed to test server routes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_server_routes()) 