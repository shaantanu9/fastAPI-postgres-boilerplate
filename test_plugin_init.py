import asyncio
from app.main import app
from app.core.plugin_system import PluginManager

async def test_plugin_system():
    print('🚀 Testing Plugin System Startup')
    print('=' * 50)
    
    # Create plugin manager
    plugin_manager = PluginManager(app, '1.0.0')
    
    # Step 1: Discover and load
    print('🔍 Step 1: Discovering plugins...')
    await plugin_manager.discover_and_load_plugins(['app/plugins'])
    plugins = plugin_manager.registry.get_all_plugins()
    print(f'✅ Discovery complete: {len(plugins)} plugins loaded')
    
    for name, plugin in plugins.items():
        print(f'   - {name}: {plugin.metadata.status}')
    
    # Step 2: Initialize
    print('\n🔧 Step 2: Initializing plugins...')
    try:
        await plugin_manager.initialize_plugins()
        print('✅ Initialization complete')
    except Exception as e:
        print(f'❌ Initialization failed: {e}')
        import traceback
        traceback.print_exc()
    
    # Step 3: Check plugin status after initialization
    print('\n📊 Step 3: Plugin status after initialization:')
    status = plugin_manager.get_plugin_status()
    for name, info in status.items():
        print(f'   {name}: {info["status"]}')
    
    # Step 4: Check routes after initialization
    print('\n📍 Step 4: Checking registered routes:')
    all_routes = [r for r in app.routes if hasattr(r, 'path')]
    order_routes = [r for r in all_routes if '/orders' in r.path]
    
    print(f'   Total routes: {len(all_routes)}')
    print(f'   Order routes: {len(order_routes)}')
    
    if order_routes:
        for route in order_routes:
            print(f'     - {route.path} [{", ".join(route.methods)}]')
    else:
        print('   No order routes found!')
        
        # Debug: Check what routes are there
        print('\n   Sample of current routes:')
        for route in all_routes[:10]:
            print(f'     - {route.path}')
    
    # Step 5: Test Order plugin specifically
    print('\n🔌 Step 5: Testing Order plugin specifically:')
    order_plugin = plugin_manager.registry.get_plugin('order_plugin')
    if order_plugin:
        print(f'   Order plugin found: {order_plugin.metadata.name}')
        print(f'   Status: {order_plugin.metadata.status}')
        
        try:
            routes = order_plugin.get_routes()
            print(f'   Plugin routes: {len(routes)}')
            
            for i, route in enumerate(routes):
                if hasattr(route, 'routes'):
                    print(f'     Router {i+1}: {len(route.routes)} endpoints')
                    for endpoint in route.routes[:3]:  # Show first 3
                        if hasattr(endpoint, 'path'):
                            print(f'       - {endpoint.path}')
        except Exception as e:
            print(f'   ❌ Error getting routes: {e}')
    else:
        print('   ❌ Order plugin not found!')

if __name__ == "__main__":
    asyncio.run(test_plugin_system()) 