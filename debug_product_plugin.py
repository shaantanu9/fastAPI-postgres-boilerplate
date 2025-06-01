#!/usr/bin/env python3
"""
Debug Product plugin loading issue
"""
import sys
sys.path.append('.')

import importlib.util
import inspect
from pathlib import Path
from app.core.plugin_system import PluginBase

def debug_product_plugin():
    """Debug Product plugin loading step by step"""
    print("🔍 Debugging Product Plugin Loading")
    print("=" * 50)
    
    # Step 1: Load module like plugin system does
    print("📂 Step 1: Loading module...")
    file_path = Path("app/plugins/product_plugin.py")
    module_name = file_path.stem
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            print("❌ Failed to create module spec")
            return
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        print("✅ Module loaded successfully")
        
    except Exception as e:
        print(f"❌ Module loading failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Find plugin classes
    print("\n📋 Step 2: Finding plugin classes...")
    plugin_classes = []
    
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and name.endswith('Plugin'):
            print(f"  🔍 Found class: {name}")
            print(f"     Type: {type(obj)}")
            print(f"     Is subclass of PluginBase: {issubclass(obj, PluginBase) if inspect.isclass(obj) else 'Not a class'}")
            print(f"     Abstract methods: {getattr(obj, '__abstractmethods__', set())}")
            plugin_classes.append((name, obj))
    
    # Step 3: Test instantiation
    print("\n🏗️ Step 3: Testing instantiation...")
    for name, cls in plugin_classes:
        print(f"  Testing {name}...")
        try:
            instance = cls()
            print(f"  ✅ {name} instantiated successfully")
            print(f"     Metadata: {instance.metadata}")
        except Exception as e:
            print(f"  ❌ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Step 4: Check for multiple PluginBase classes
    print("\n🔍 Step 4: Checking for multiple PluginBase imports...")
    pluginbase_classes = []
    for name, obj in inspect.getmembers(module):
        if hasattr(obj, '__name__') and 'PluginBase' in str(obj):
            pluginbase_classes.append((name, obj))
    
    print(f"Found {len(pluginbase_classes)} PluginBase-related objects:")
    for name, obj in pluginbase_classes:
        print(f"  - {name}: {obj}")
    
    # Step 5: Compare with known working plugin
    print("\n🔄 Step 5: Comparing with Order plugin...")
    try:
        from app.plugins.order_plugin import OrderPlugin
        order_instance = OrderPlugin()
        print("✅ Order plugin loads fine")
        print(f"   Order PluginBase: {OrderPlugin.__bases__}")
        
        from app.plugins.product_plugin import ProductPlugin
        print(f"   Product PluginBase: {ProductPlugin.__bases__}")
        
        # Check if they're the same class
        print(f"   Same PluginBase class: {OrderPlugin.__bases__[0] is ProductPlugin.__bases__[0]}")
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_product_plugin() 