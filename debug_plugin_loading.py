#!/usr/bin/env python3
"""
Debug Plugin Loading
"""
import asyncio
import sys
sys.path.append('.')

async def debug_plugin_loading():
    print("🔍 Debug: Plugin Loading Process")
    print("=" * 50)
    
    from app.core.plugin_system import PluginManager
    from fastapi import FastAPI
    
    app = FastAPI()
    manager = PluginManager(app, '1.0.0')
    
    # Step 1: Check plugin discovery
    print("\n📂 Step 1: Plugin Discovery")
    search_paths = ['app/plugins']
    
    for search_path in search_paths:
        from pathlib import Path
        path = Path(search_path)
        print(f"   Checking path: {path} (exists: {path.exists()})")
        
        if path.exists():
            # Check for v4 plugins
            plugin_dirs = [d for d in path.iterdir() if d.is_dir() and d.name.endswith('_plugin')]
            print(f"   Found {len(plugin_dirs)} v4 plugin directories:")
            for plugin_dir in plugin_dirs:
                print(f"     - {plugin_dir.name}")
                init_file = plugin_dir / "__init__.py"
                print(f"       __init__.py exists: {init_file.exists()}")
                
                if init_file.exists():
                    # Check if it has required components
                    try:
                        with open(init_file, 'r') as f:
                            content = f.read()
                        has_register_plugin = 'def register_plugin(' in content
                        has_metadata = 'PLUGIN_METADATA' in content
                        print(f"       has register_plugin: {has_register_plugin}")
                        print(f"       has PLUGIN_METADATA: {has_metadata}")
                    except Exception as e:
                        print(f"       Error reading file: {e}")
    
    # Step 2: Try to discover plugins
    print("\n🔍 Step 2: Discovering Plugins")
    try:
        await manager.discover_and_load_plugins(search_paths)
        plugins = manager.registry.get_all_plugins()
        print(f"   Discovered {len(plugins)} plugins:")
        for name, plugin in plugins.items():
            print(f"     - {name}: {type(plugin).__name__}")
            print(f"       Status: {plugin.metadata.status.value}")
    except Exception as e:
        print(f"   ❌ Error during discovery: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Try to initialize plugins
    print("\n🚀 Step 3: Initializing Plugins")
    try:
        await manager.initialize_plugins()
        print("   ✅ Plugins initialized")
        
        # Check routes after initialization
        print(f"   FastAPI routes after initialization: {len(app.routes)}")
        for route in app.routes:
            if hasattr(route, 'path'):
                print(f"     - {route.path}")
        
    except Exception as e:
        print(f"   ❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Test manual plugin import
    print("\n🧪 Step 4: Manual Plugin Import Test")
    try:
        from app.plugins.product_plugin import register_plugin, PLUGIN_METADATA
        print(f"   ✅ Successfully imported product plugin")
        print(f"   Metadata: {PLUGIN_METADATA}")
        
        # Test register_plugin function
        from app.core.plugin_system import PluginContext
        context = PluginContext(app)
        
        print("   Testing register_plugin function...")
        result = register_plugin(app, context)
        print(f"   register_plugin returned: {result}")
        
        # Check routes after manual registration
        print(f"   FastAPI routes after manual registration: {len(app.routes)}")
        product_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and 'product' in route.path.lower():
                product_routes.append(route.path)
        print(f"   Product routes: {product_routes}")
        
    except Exception as e:
        print(f"   ❌ Error during manual import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_plugin_loading()) 