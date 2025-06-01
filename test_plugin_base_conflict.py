#!/usr/bin/env python3
"""
Test for PluginBase class conflicts
"""
import sys
import importlib.util
import inspect
from pathlib import Path

def test_plugin_base_conflict():
    """Test if there are multiple PluginBase classes causing conflicts"""
    print("🔍 Testing PluginBase Class Conflicts")
    print("=" * 50)
    
    # Import PluginBase from the plugin system
    from app.core.plugin_system import PluginBase as SystemPluginBase
    print(f"📋 System PluginBase: {SystemPluginBase}")
    print(f"📋 System PluginBase ID: {id(SystemPluginBase)}")
    
    # Load the Product plugin module fresh
    file_path = Path('app/plugins/product_plugin.py')
    spec = importlib.util.spec_from_file_location('test_product_plugin', file_path)
    module = importlib.util.module_from_spec(spec)
    
    try:
        spec.loader.exec_module(module)
        print("✅ Product plugin module loaded")
        
        # Find the ProductPlugin class
        ProductPlugin = getattr(module, 'ProductPlugin')
        print(f"📋 ProductPlugin: {ProductPlugin}")
        print(f"📋 ProductPlugin bases: {ProductPlugin.__bases__}")
        
        # Get the PluginBase from the module
        ModulePluginBase = ProductPlugin.__bases__[0]
        print(f"📋 Module PluginBase: {ModulePluginBase}")
        print(f"📋 Module PluginBase ID: {id(ModulePluginBase)}")
        
        # Check if they're the same
        print(f"📋 Same PluginBase class: {SystemPluginBase is ModulePluginBase}")
        print(f"📋 issubclass check: {issubclass(ProductPlugin, SystemPluginBase)}")
        
        # Check abstract methods
        print(f"📋 System PluginBase abstract methods: {getattr(SystemPluginBase, '__abstractmethods__', set())}")
        print(f"📋 Module PluginBase abstract methods: {getattr(ModulePluginBase, '__abstractmethods__', set())}")
        print(f"📋 ProductPlugin abstract methods: {getattr(ProductPlugin, '__abstractmethods__', set())}")
        
        # Test the _is_plugin_class logic
        def _is_plugin_class(obj):
            """Replicate the plugin system's _is_plugin_class logic"""
            return (
                inspect.isclass(obj) and
                (
                    issubclass(obj, SystemPluginBase) or
                    (hasattr(obj, 'initialize') and hasattr(obj, 'startup') and hasattr(obj, 'shutdown'))
                )
            )
        
        print(f"📋 _is_plugin_class result: {_is_plugin_class(ProductPlugin)}")
        
        # Try to instantiate
        try:
            instance = ProductPlugin()
            print("✅ Instantiation successful")
            print(f"📋 Instance metadata: {instance.metadata}")
        except Exception as e:
            print(f"❌ Instantiation failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Module loading failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_plugin_base_conflict() 