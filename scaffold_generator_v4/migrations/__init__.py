"""
Smart Migration & Schema Evolution System for FastAPI Scaffold Generator v4.0

This module provides intelligent database migration capabilities:
- Zero-downtime migration generation
- Schema comparison and diffing
- Data migration script generation
- Rollback strategy planning
- Schema versioning across environments
"""

from .smart_migration_manager import SmartMigrationManager

__all__ = [
    'SmartMigrationManager'
] 