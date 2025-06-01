#!/usr/bin/env python3
"""
Test fresh import of Product plugin
"""
import sys
import importlib.util
from pathlib import Path

def test_fresh_import():
    """Test a completely fresh import of the Product plugin"""
    print("🔍 Testing Fresh Import of Product Plugin")
    print("=" * 50)
    
    # Load the module fresh
    file_path = Path('app/plugins/product_plugin.py')
    spec = importlib.util.spec_from_file_location('fresh_product_plugin', file_path)
    module = importlib.util.module_from_spec(spec)
    
    try:
        spec.loader.exec_module(module)
        print("✅ Module loaded successfully")
        
        # Find the ProductPlugin class
        ProductPlugin = getattr(module, 'ProductPlugin')
        print(f"📋 ProductPlugin class: {ProductPlugin}")
        print(f"📋 Has metadata: {hasattr(ProductPlugin, 'metadata')}")
        print(f"📋 Metadata type: {type(getattr(ProductPlugin, 'metadata', None))}")
        print(f"📋 Abstract methods: {getattr(ProductPlugin, '__abstractmethods__', set())}")
        
        # Try to instantiate
        try:
            instance = ProductPlugin()
            print("✅ Instantiation successful")
            print(f"📋 Metadata: {instance.metadata}")
        except Exception as e:
            print(f"❌ Instantiation failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Module loading failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fresh_import() 