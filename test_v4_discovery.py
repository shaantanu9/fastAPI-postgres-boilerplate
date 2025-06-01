#!/usr/bin/env python3
"""
Test v4 Plugin Discovery
"""
import asyncio
import sys
sys.path.append('.')

async def test_v4_discovery():
    from app.core.plugin_system import PluginManager
    from fastapi import FastAPI
    
    print('🔍 Testing v4 Plugin Discovery')
    print('=' * 40)
    
    app = FastAPI()
    manager = PluginManager(app, '1.0.0')
    
    # Discover plugins
    await manager.discover_and_load_plugins(['app/plugins'])
    
    # Check discovered plugins
    plugins = manager.registry.get_all_plugins()
    print(f'📊 Discovered {len(plugins)} plugins:')
    
    for name, plugin in plugins.items():
        plugin_type = 'v4' if 'V4PluginAdapter' in str(type(plugin)) else 'v3'
        print(f'  🔌 {name} ({plugin_type}): {plugin.metadata.description}')
        
        # Check routes
        try:
            routes = plugin.get_routes()
            print(f'     📍 Routes: {len(routes)} router(s)')
        except Exception as e:
            print(f'     ❌ Route error: {e}')
    
    # Test initialization
    print('\n🚀 Testing Plugin Initialization')
    print('=' * 40)
    
    try:
        await manager.initialize_plugins()
        print('✅ Plugins initialized successfully')
        
        # Check FastAPI routes
        total_routes = len([r for r in app.routes if hasattr(r, 'path')])
        print(f'📍 Total FastAPI routes: {total_routes}')
        
        # List some routes
        for route in app.routes:
            if hasattr(route, 'path') and ('/products' in route.path or '/orders' in route.path):
                methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'Unknown'
                print(f'  - {route.path} [{methods}]')
                
    except Exception as e:
        print(f'❌ Initialization failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_v4_discovery()) 