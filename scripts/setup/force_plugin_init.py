#!/usr/bin/env python3
"""Force plugin initialization in main app."""

import asyncio
import sys
sys.path.append(".")

async def force_plugin_init():
    """Force plugin initialization in the main app."""
    
    print("🔧 Forcing plugin initialization in main app...")
    
    try:
        # Import main app
        from app.main import app, _plugin_manager
        
        # Check if plugin manager exists
        if _plugin_manager:
            print(f"✅ Plugin manager already exists")
            status = _plugin_manager.get_plugin_status()
            print(f"📊 Current status: {len(status)} plugins")
            for name, info in status.items():
                print(f"  - {name}: {info['status']}")
        else:
            print("❌ Plugin manager does not exist, creating new one...")
            
            # Force create plugin manager and initialize
            from app.core.plugin_system import PluginManager
            manager = PluginManager(app, "1.0.0")
            
            # Discover and load
            await manager.discover_and_load_plugins(["app/plugins"])
            
            # Initialize
            await manager.initialize_plugins()
            
            # Start
            await manager.startup_plugins()
            
            # Set global reference
            import app.main as main_module
            main_module._plugin_manager = manager
            
            print("✅ Plugin manager created and initialized")
            
            status = manager.get_plugin_status()
            print(f"📊 New status: {len(status)} plugins")
            for name, info in status.items():
                print(f"  - {name}: {info['status']}")
        
        # Check routes
        book_routes = [r for r in app.routes if hasattr(r, 'path') and 'book' in r.path.lower()]
        print(f"📋 Main app has {len(book_routes)} book routes")
        
        # Check OpenAPI
        openapi_spec = app.openapi()
        book_paths = [path for path in openapi_spec.get('paths', {}).keys() if 'book' in path.lower()]
        print(f"📄 Main app OpenAPI has {len(book_paths)} book paths")
        
        return len(book_routes) > 0
        
    except Exception as e:
        print(f"❌ Force init failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(force_plugin_init())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Book routes {'found' if success else 'not found'}") 