#!/usr/bin/env python3
"""
PLUGIN DISCOVERY DEBUGGING TEST

PURPOSE:
    Debug plugin discovery system to identify why plugins aren't loading properly
    
WHEN TO USE:
    - When plugins are not being discovered or loaded
    - When plugin system initialization fails
    - When specific plugins (like book_plugin) are missing
    - Debugging plugin registration issues
    - Testing plugin system step-by-step
    
WHAT IT TESTS:
    1. Plugin system imports and initialization
    2. Plugin discovery from app/plugins directory
    3. Plugin metadata validation
    4. Plugin registration process
    5. Plugin initialization and status
    6. Route registration for plugins
    7. Manual import testing for specific plugins
    
CREATED: Pre-2025-06-14 (legacy debugging test)
DEPENDENCIES: Requires plugin system and plugins in app/plugins/
RESULT: Identifies plugin discovery and loading issues

HOW TO RUN:
    python3 tests/plugins/test_plugin_discovery.py

EXPECTED OUTPUT:
    ✅ All plugins should be discovered
    ✅ Plugin metadata should be valid
    ✅ Plugins should initialize successfully
    ✅ Routes should be registered

DEBUGGING FEATURES:
    - Step-by-step plugin discovery process
    - Manual import testing for failed plugins
    - Directory and file existence checks
    - Metadata validation
    - Route registration verification
"""

import asyncio
import sys
sys.path.append(".")

async def test_plugin_discovery():
    """Test plugin discovery step by step."""
    
    print("🔍 Testing Plugin Discovery...")
    print("=" * 50)
    
    # Step 1: Import required modules
    print("\n📦 Step 1: Testing imports...")
    try:
        from fastapi import FastAPI
        from app.core.plugin_system import PluginManager
        print("✅ Imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Create app and manager
    print("\n🏗️ Step 2: Creating PluginManager...")
    try:
        app = FastAPI()
        manager = PluginManager(app, "1.0.0")
        print("✅ PluginManager created successfully")
        print(f"   📝 App version: 1.0.0")
    except Exception as e:
        print(f"❌ PluginManager creation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Test discovery
    print("\n🔍 Step 3: Discovering plugins...")
    try:
        print("📂 Discovering plugins from app/plugins...")
        await manager.discover_and_load_plugins(["app/plugins"])
        
        # Check what was discovered
        plugins = manager.registry.get_all_plugins()
        print(f"✅ Discovery completed. Found {len(plugins)} plugins:")
        
        for name, plugin in plugins.items():
            status = plugin.metadata.status.value
            version = plugin.metadata.version
            print(f"  - {name}: {status} (v{version})")
            
    except Exception as e:
        print(f"❌ Plugin discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Check specifically for book_plugin
    print("\n📖 Step 4: Checking book_plugin specifically...")
    book_plugin = manager.registry.get_plugin("book_plugin")
    if book_plugin:
        print(f"✅ Book plugin found!")
        print(f"   📝 Status: {book_plugin.metadata.status.value}")
        print(f"   📝 Version: {book_plugin.metadata.version}")
        print(f"   📝 Description: {book_plugin.metadata.description}")
    else:
        print(f"❌ Book plugin NOT found")
        
        # Debug: Check if the directory exists
        print("\n🔍 Debugging book_plugin absence...")
        from pathlib import Path
        book_dir = Path("app/plugins/book_plugin")
        if book_dir.exists():
            print(f"✅ Book plugin directory exists: {book_dir}")
            init_file = book_dir / "__init__.py"
            if init_file.exists():
                print(f"✅ __init__.py exists")
                
                # Try to manually import
                try:
                    print("🔄 Attempting manual import...")
                    import app.plugins.book_plugin as book_module
                    print(f"✅ Book module imported successfully")
                    
                    if hasattr(book_module, 'register_plugin'):
                        print(f"✅ register_plugin function found")
                    else:
                        print(f"❌ register_plugin function NOT found")
                        print(f"   📝 Available attributes: {dir(book_module)}")
                        
                    if hasattr(book_module, 'PLUGIN_METADATA'):
                        print(f"✅ PLUGIN_METADATA found")
                        metadata = book_module.PLUGIN_METADATA
                        print(f"   📝 Metadata: {metadata}")
                    else:
                        print(f"❌ PLUGIN_METADATA NOT found")
                        print(f"   📝 Available attributes: {dir(book_module)}")
                        
                except Exception as import_error:
                    print(f"❌ Manual import failed: {import_error}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"❌ __init__.py does NOT exist in {book_dir}")
        else:
            print(f"❌ Book plugin directory does NOT exist: {book_dir}")
    
    # Step 5: Try initialization
    print("\n🔧 Step 5: Initializing plugins...")
    if plugins:
        try:
            print(f"Attempting to initialize {len(plugins)} plugins...")
            await manager.initialize_plugins()
            
            # Check status after initialization
            print("📊 Plugin status after initialization:")
            for name, plugin in plugins.items():
                status = plugin.metadata.status.value
                print(f"  - {name}: {status}")
                
            # Check app routes
            print("\n🛣️ Checking registered routes...")
            book_routes = [r for r in app.routes if hasattr(r, 'path') and 'book' in r.path.lower()]
            print(f"Found {len(book_routes)} book-related routes:")
            for route in book_routes[:5]:  # Show first 5
                method = getattr(route, 'methods', ['Unknown'])
                print(f"  - {list(method)[0] if method else 'GET'} {route.path}")
                
            # Check all plugin routes
            plugin_routes = [r for r in app.routes if hasattr(r, 'path') and '/api/v1/' in r.path]
            print(f"\nTotal API routes: {len(plugin_routes)}")
            
        except Exception as e:
            print(f"❌ Plugin initialization failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️ No plugins found to initialize")
    
    # Step 6: Summary
    print("\n" + "=" * 50)
    print("📊 PLUGIN DISCOVERY SUMMARY")
    print("=" * 50)
    
    if plugins:
        print(f"✅ Successfully discovered {len(plugins)} plugins")
        for name, plugin in plugins.items():
            status = plugin.metadata.status.value
            emoji = "✅" if status == "enabled" else "⚠️" if status == "initialized" else "❌"
            print(f"   {emoji} {name}: {status}")
    else:
        print("❌ No plugins discovered")
        
    print("\n💡 Troubleshooting tips:")
    print("   - Check that plugin directories exist in app/plugins/")
    print("   - Verify __init__.py files are present in plugin directories")
    print("   - Ensure PLUGIN_METADATA is defined in plugin modules")
    print("   - Check that register_plugin function exists")
    print("   - Review server logs for detailed error messages")

if __name__ == "__main__":
    print("🚀 Plugin Discovery Debug Test")
    print("=" * 50)
    asyncio.run(test_plugin_discovery()) 