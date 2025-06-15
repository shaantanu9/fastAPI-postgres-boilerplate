#!/usr/bin/env python3
"""
Simple test to isolate import issue
"""
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("Testing very basic import...")

try:
    print("Testing models_template import...")
    import templates.models_template
    print("✅ models_template module imported")
except Exception as e:
    print(f"❌ models_template import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("Testing ModelsTemplate class...")
    from templates.models_template import ModelsTemplate
    print("✅ ModelsTemplate class imported")
except Exception as e:
    print(f"❌ ModelsTemplate class import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("🎉 Basic import test passed!") 