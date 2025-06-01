#!/usr/bin/env python3
"""
FastAPI Scaffold Generator v4.0 - Standalone Script

This is a convenience script that imports and uses the modular scaffold generator v4.
The actual generator logic is organized in the scaffold_generator_v4/ package.

Usage:
    python scaffold_plugin_generator_v4.py add Product name:str price:float:gt=0 --with-tasks --with-bulk
    python scaffold_plugin_generator_v4.py infra-check
    python scaffold_plugin_generator_v4.py test User name:str email:email
    python scaffold_plugin_generator_v4.py health-check

Features:
✅ Modular architecture (models.py, schemas.py, services.py, routes.py, tasks.py)
✅ Infrastructure compatibility (Alembic + Procrastinate)
✅ Comprehensive validation and testing
✅ Industry best practices and patterns
✅ Enterprise-grade code quality
"""

from scaffold_generator_v4.main import main

if __name__ == "__main__":
    main() 