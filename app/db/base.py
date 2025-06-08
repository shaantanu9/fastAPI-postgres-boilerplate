import contextlib
import importlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here so Alembic's autogenerate can see them
# Models are now auto-discovered from plugins below


# Auto-discover and import all plugin models for Alembic
def import_plugin_models() -> None:
    """Automatically discover and import all models from plugins
    so they're registered with Base.metadata for Alembic autogenerate.

    This function handles both v3 (single file) and v4 (modular) plugin structures.
    Should only be called by Alembic, not during normal app startup.
    """
    plugins_dir = Path(__file__).parent.parent / "plugins"

    if not plugins_dir.exists():
        return


    # Handle v3 single-file plugins (*_plugin.py)
    for plugin_file in plugins_dir.glob("*_plugin.py"):
        plugin_name = plugin_file.stem

        try:
            # Import the plugin module
            module = importlib.import_module(f"app.plugins.{plugin_name}")

            # Look for model classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # Check if it's a model class (inherits from Base and has __tablename__)
                if (
                    hasattr(attr, "__tablename__")
                    and hasattr(attr, "__table__")
                    and hasattr(attr, "metadata")
                    and attr.metadata is Base.metadata
                ):
                    # Model is already registered, just ensure it's imported
                    pass

        except Exception:
            pass

    # Handle v4 modular plugins (*_plugin/ directories)
    for plugin_dir in plugins_dir.iterdir():
        if plugin_dir.is_dir() and plugin_dir.name.endswith("_plugin"):
            plugin_name = plugin_dir.name
            models_file = plugin_dir / "models.py"

            if models_file.exists():
                try:
                    # Import only the models module from the plugin directory
                    # Use a more isolated import approach to avoid dependency issues
                    module_name = f"app.plugins.{plugin_name}.models"

                    # Try to import the models module with better error handling
                    try:
                        module = importlib.import_module(module_name)
                    except ImportError:
                        # If direct import fails, try loading from file path
                        models_file_path = models_file
                        spec = importlib.util.spec_from_file_location(
                            module_name, models_file_path,
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[module_name] = module
                            spec.loader.exec_module(module)
                        else:
                            raise

                    # Look for model classes in the models module
                    model_count = 0
                    for attr_name in dir(module):
                        if attr_name.startswith("_"):  # Skip private attributes
                            continue

                        try:
                            attr = getattr(module, attr_name)

                            # Check if it's a model class (inherits from Base and has __tablename__)
                            if (
                                inspect.isclass(attr)
                                and hasattr(attr, "__tablename__")
                                and hasattr(attr, "__table__")
                                and hasattr(attr, "metadata")
                                and attr.metadata is Base.metadata
                            ):
                                # Model is already registered, just ensure it's imported
                                model_count += 1
                        except Exception:
                            # Skip attributes that can't be accessed
                            continue

                    if model_count == 0:
                        pass

                except Exception:
                    pass
            else:
                pass


# Only import plugin models if we're running Alembic
# Check if this is being called by Alembic by looking at the call stack
def is_alembic_context() -> bool:
    """Check if we're running in Alembic context."""
    # Check environment variable first
    if os.getenv("ALEMBIC_CONTEXT") == "true":
        return True

    # Check call stack for Alembic-related frames
    frame = inspect.currentframe()
    while frame:
        filename = frame.f_code.co_filename
        if "alembic" in filename.lower() or "env.py" in filename:
            return True
        frame = frame.f_back
    return False


# Only auto-import models when Alembic is running
# DO NOT import plugin models during normal app startup to avoid conflicts
if is_alembic_context():

    # Import core models for Alembic
    with contextlib.suppress(Exception):
        pass

    import_plugin_models()
else:
    pass
