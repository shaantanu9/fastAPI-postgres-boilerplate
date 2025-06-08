"""FastAPI Scaffold Generator v4.0 - Modular Architecture.

A comprehensive, modular scaffold generator for FastAPI plugins with:
- Modular file structure (models.py, schemas.py, services.py, routes.py, tasks.py)
- Enterprise-grade patterns and best practices
- Infrastructure compatibility (Alembic + Procrastinate)
- Comprehensive validation and testing
- Modern CLI interface

Version: 4.0.0
Author: FastAPI Scaffold Generator Team
"""

__version__ = "4.0.0"
__author__ = "FastAPI Scaffold Generator Team"

from .core import (
    FieldValidator,
    InfrastructureChecker,
    MigrationManager,
    PluginValidator,
)
from .templates import (
    InitTemplate,
    ModelsTemplate,
    RoutesTemplate,
    SchemasTemplate,
    ServicesTemplate,
    TasksTemplate,
)

__all__ = [
    "FieldValidator",
    "InfrastructureChecker",
    "InitTemplate",
    "MigrationManager",
    "ModelsTemplate",
    "PluginValidator",
    "RoutesTemplate",
    "SchemasTemplate",
    "ServicesTemplate",
    "TasksTemplate",
]
