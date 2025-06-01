#!/usr/bin/env python3
"""
Detailed debug script to trace plugin loading
"""

import sys
import importlib.util
import inspect
from pathlib import Path
sys.path.append('.')

from app.core.plugin_system import PluginBase, PluginMetadata

def debug_module_loading():
    """Debug the module loading process step by step"""
    print("🔬 Detailed Plugin Loading Debug")
    print("=" * 50)
    
    file_path = Path("app/plugins/product_plugin.py")
    module_name = file_path.stem
    
    print(f"📁 Loading module: {module_name} from {file_path}")
    
    try:
        # Step 1: Create module spec
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        print(f"✅ Created spec: {spec}")
        
        # Step 2: Create module
        module = importlib.util.module_from_spec(spec)
        print(f"✅ Created module: {module}")
        
        # Step 3: Add to sys.modules
        sys.modules[module_name] = module
        print(f"✅ Added to sys.modules")
        
        # Step 4: Execute module
        spec.loader.exec_module(module)
        print(f"✅ Executed module")
        
        # Step 5: Find plugin classes
        print(f"\n🔍 Scanning module members:")
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name.endswith('Plugin'):
                print(f"  📋 Found class: {name}")
                print(f"     Type: {type(obj)}")
                print(f"     MRO: {obj.__mro__}")
                print(f"     Is subclass of PluginBase: {issubclass(obj, PluginBase)}")
                print(f"     Has metadata: {hasattr(obj, 'metadata')}")
                
                # Check metadata property
                metadata_attr = getattr(obj, 'metadata', None)
                print(f"     Metadata attr type: {type(metadata_attr)}")
                print(f"     Is property: {isinstance(metadata_attr, property)}")
                
                # Check abstract methods
                abstract_methods = getattr(obj, '__abstractmethods__', set())
                print(f"     Abstract methods: {abstract_methods}")
                
                # Try to instantiate
                print(f"     🏗️  Attempting instantiation...")
                try:
                    instance = obj()
                    print(f"     ✅ Success! Instance: {instance}")
                    print(f"     📋 Metadata: {instance.metadata}")
                except Exception as e:
                    print(f"     ❌ Failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                print()
        
    except Exception as e:
        print(f"❌ Module loading failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_module_loading() 