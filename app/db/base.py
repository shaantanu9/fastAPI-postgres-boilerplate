from sqlalchemy.orm import declarative_base
import os
import importlib
from pathlib import Path
import inspect

Base = declarative_base()

# Import all models here so Alembic's autogenerate can see them
# Models are now auto-discovered from plugins below

# Auto-discover and import all plugin models for Alembic
def import_plugin_models():
    """
    Automatically discover and import all models from plugins
    so they're registered with Base.metadata for Alembic autogenerate
    
    This function should only be called by Alembic, not during normal app startup
    to avoid conflicts with the plugin system.
    """
    plugins_dir = Path(__file__).parent.parent / "plugins"
    
    if not plugins_dir.exists():
        return
    
    # Get all plugin files
    for plugin_file in plugins_dir.glob("*_plugin.py"):
        plugin_name = plugin_file.stem
        
        try:
            # Import the plugin module
            module = importlib.import_module(f"app.plugins.{plugin_name}")
            
            # Look for model classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it's a model class (inherits from Base and has __tablename__)
                if (hasattr(attr, '__tablename__') and 
                    hasattr(attr, '__table__') and 
                    hasattr(attr, 'metadata') and
                    attr.metadata is Base.metadata):
                    
                    # Model is already registered, just ensure it's imported
                    print(f"Discovered model: {attr_name} from {plugin_name}")
                    
        except Exception as e:
            print(f"Warning: Could not import models from {plugin_name}: {e}")

# Only import plugin models if we're running Alembic
# Check if this is being called by Alembic by looking at the call stack
def is_alembic_context():
    """Check if we're running in Alembic context"""
    # Check environment variable first
    if os.getenv('ALEMBIC_CONTEXT') == 'true':
        return True
    
    # Check call stack for Alembic-related frames
    frame = inspect.currentframe()
    while frame:
        filename = frame.f_code.co_filename
        if 'alembic' in filename.lower() or 'env.py' in filename:
            return True
        frame = frame.f_back
    return False

# Only auto-import models when Alembic is running  
# DO NOT import plugin models during normal app startup to avoid conflicts
if is_alembic_context():
    print("🔧 Alembic context detected - importing plugin models for autogenerate")
    import_plugin_models()
else:
    print("🚀 Normal app startup - skipping plugin model import to avoid conflicts")
