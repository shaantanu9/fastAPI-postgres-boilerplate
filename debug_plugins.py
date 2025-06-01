#!/usr/bin/env python3
"""
Debug script to test plugin discovery and loading
"""

import sys
import os
sys.path.append('.')

from app.core.plugin_system import PluginLoader, VersionManager
from pathlib import Path

def debug_plugin_discovery():
    """Debug plugin discovery process"""
    print("🔍 Debugging Plugin Discovery")
    print("=" * 50)
    
    # Initialize version manager and loader
    version_manager = VersionManager("1.0.0")
    loader = PluginLoader(version_manager)
    
    # Test plugin discovery
    search_paths = ["app/plugins"]
    
    print(f"📁 Searching in: {search_paths}")
    
    for search_path in search_paths:
        path = Path(search_path)
        if not path.exists():
            print(f"❌ Path does not exist: {path}")
            continue
            
        print(f"\n📂 Scanning directory: {path}")
        
        # List all Python files
        python_files = list(path.glob("*.py"))
        print(f"🐍 Found Python files: {[f.name for f in python_files]}")
        
        # Try to discover plugins from this directory
        plugins = loader._discover_from_directory(path)
        print(f"🔌 Discovered plugins: {len(plugins)}")
        
        for plugin in plugins:
            print(f"  ✅ {plugin.metadata.name} v{plugin.metadata.version}")
            print(f"     Status: {plugin.metadata.status}")
            print(f"     Description: {plugin.metadata.description}")
            print(f"     Dependencies: {plugin.metadata.dependencies}")
            print()
    
    # Test overall discovery
    print("\n🌍 Overall Discovery Test")
    all_plugins = loader.discover_plugins(search_paths)
    print(f"Total plugins discovered: {len(all_plugins)}")
    
    for plugin in all_plugins:
        print(f"  🔌 {plugin.metadata.name}")

if __name__ == "__main__":
    debug_plugin_discovery() 