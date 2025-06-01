import asyncio
from app.main import app

async def test_routes():
    print('🚀 Testing Order Routes in FastAPI App')
    print('=' * 50)
    
    # Check if routes are registered
    order_routes = [r for r in app.routes if hasattr(r, 'path') and '/orders' in r.path]
    print(f'📍 Order routes found: {len(order_routes)}')
    
    for route in order_routes:
        methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'Unknown'
        print(f'  - {route.path} [{methods}]')
    
    print(f'\n✅ Total FastAPI routes: {len([r for r in app.routes if hasattr(r, "path")])}')
    
    # Check plugin status
    try:
        from app.main import _plugin_manager
        if _plugin_manager:
            status = _plugin_manager.get_plugin_status()
            print(f'\n🔌 Plugin Status:')
            for name, info in status.items():
                print(f'  - {name}: {info["status"]}')
    except Exception as e:
        print(f'\n⚠️ Plugin manager not available: {e}')

if __name__ == "__main__":
    asyncio.run(test_routes()) 