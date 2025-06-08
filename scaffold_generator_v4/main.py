#!/usr/bin/env python3
"""FastAPI Scaffold Generator v4.0 - Main CLI Interface.

A modular, enterprise-grade scaffold generator for FastAPI plugins.
Creates plugins with modern architecture patterns:
- Modular file structure (models.py, schemas.py, services.py, routes.py, tasks.py)
- Infrastructure compatibility (Alembic + Procrastinate)
- Comprehensive validation and testing
- Industry best practices

Usage:
    python scaffold_generator_v4/main.py add User name:str email:email age:int --with-tasks --with-bulk
    python scaffold_generator_v4/main.py infra-check
    python scaffold_generator_v4/main.py test User name:str email:email
    python scaffold_generator_v4/main.py health-check
"""

import argparse
import sys
from pathlib import Path

from .analyzers import ArchitectureAnalyzer

# Import modular components
from .core import (
    FieldValidator,
    InfrastructureChecker,
    MigrationManager,
    PluginValidator,
)
from .migrations import SmartMigrationManager
from .templates import (
    EnhancedRoutesTemplate,
    InitTemplate,
    ModelsTemplate,
    RoutesTemplate,
    SchemasTemplate,
    ServicesTemplate,
    TasksTemplate,
)
from .templates.auth_models_template import AuthModelsTemplate
from .templates.auth_routes_template import AuthRoutesTemplate
from .testing import TestConfig, TestGenerator


class ScaffoldGeneratorV4:
    """Main scaffold generator orchestrator."""

    def __init__(self) -> None:
        # Initialize core components
        self.field_validator = FieldValidator()
        self.infrastructure_checker = InfrastructureChecker()
        self.migration_manager = MigrationManager(self.infrastructure_checker)
        self.plugin_validator = PluginValidator()

        # Initialize new advanced components
        self.architecture_analyzer = ArchitectureAnalyzer()
        self.test_generator = TestGenerator()
        self.smart_migration_manager = SmartMigrationManager()

        # Initialize templates
        self.templates = {
            "models": ModelsTemplate(),
            "schemas": SchemasTemplate(),
            "services": ServicesTemplate(),
            "routes": RoutesTemplate(),
            "enhanced_routes": EnhancedRoutesTemplate(),
            "tasks": TasksTemplate(),
            "init": InitTemplate(),
        }

        # Initialize auth templates
        self.auth_templates = {
            "models": AuthModelsTemplate(),
            "routes": AuthRoutesTemplate(),
        }

    def add_plugin(
        self,
        model_name: str,
        fields: list,
        with_tasks: bool = False,
        with_bulk: bool = False,
        with_auth: bool = False,
        auth_config: dict | None = None,
        with_timeouts: bool = True,
    ) -> bool | None:
        """Generate a new modular plugin."""
        try:
            # 1. Validate infrastructure compatibility
            if not self.infrastructure_checker.check_compatibility():
                return False

            if not self.infrastructure_checker.validate_table_name_compatibility(
                model_name,
            ):
                return False

            # 2. Validate fields
            validated_fields = self.field_validator.validate_fields_batch(fields)

            # 3. Create plugin directory
            plugin_dir = self._create_plugin_directory(model_name)

            # 4. Generate modular files
            self._generate_plugin_files(
                plugin_dir,
                model_name,
                validated_fields,
                with_tasks,
                with_bulk,
                with_auth,
                auth_config,
                with_timeouts,
            )

            # 5. Generate migration
            migration_success = self.migration_manager.generate_migration(model_name)

            return bool(migration_success)

        except Exception:
            return False

    def _create_plugin_directory(self, model_name: str) -> Path:
        """Create the plugin directory structure."""
        import re

        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()
        plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return plugin_dir

    def _generate_plugin_files(
        self,
        plugin_dir: Path,
        model_name: str,
        validated_fields: list,
        with_tasks: bool,
        with_bulk: bool,
        with_auth: bool = False,
        auth_config: dict | None = None,
        with_timeouts: bool = True,
    ) -> None:
        """Generate all modular plugin files."""
        # Choose templates based on authentication requirement
        if with_auth:
            # Generate models.py with auth features
            models_content = self.auth_templates["models"].generate(
                model_name, validated_fields, self.field_validator, auth_config,
            )
            (plugin_dir / "models.py").write_text(models_content)

            # Generate routes.py with auth features
            routes_content = self.auth_templates["routes"].generate(
                model_name, validated_fields, auth_config, with_bulk,
            )
            (plugin_dir / "routes.py").write_text(routes_content)
        else:
            # Generate models.py (standard)
            models_content = self.templates["models"].generate(
                model_name, validated_fields, self.field_validator,
            )
            (plugin_dir / "models.py").write_text(models_content)

            # Generate routes.py (choose enhanced or standard)
            if with_timeouts:
                routes_content = self.templates["enhanced_routes"].generate(
                    model_name, validated_fields, with_bulk,
                )
                (plugin_dir / "routes.py").write_text(routes_content)
            else:
                routes_content = self.templates["routes"].generate(
                    model_name, validated_fields, with_bulk,
                )
                (plugin_dir / "routes.py").write_text(routes_content)

        # Generate schemas.py (always use standard for now)
        schemas_content = self.templates["schemas"].generate(
            model_name, validated_fields, self.field_validator,
        )
        (plugin_dir / "schemas.py").write_text(schemas_content)

        # Generate services.py (always use standard for now)
        services_content = self.templates["services"].generate(
            model_name, validated_fields,
        )
        (plugin_dir / "services.py").write_text(services_content)

        # Generate tasks.py (if requested)
        if with_tasks:
            tasks_content = self.templates["tasks"].generate(model_name)
            (plugin_dir / "tasks.py").write_text(tasks_content)

        # Generate __init__.py
        init_content = self.templates["init"].generate(
            model_name, with_tasks, with_bulk,
        )
        (plugin_dir / "__init__.py").write_text(init_content)

    def infra_check(self):
        """Run infrastructure compatibility check."""
        success = self.infrastructure_checker.check_compatibility()
        if success:
            pass
        else:
            pass
        return success

    def test_plugin(self, model_name: str, fields: list) -> bool | None:
        """Test plugin generation without creating files."""
        try:
            # Test infrastructure
            if not self.infrastructure_checker.check_compatibility():
                return False

            # Test fields
            self.field_validator.validate_fields_batch(fields)

            # Test plugin validation
            return bool(self.plugin_validator.test_plugin_generation(model_name, fields))

        except Exception:
            return False

    def health_check(self):
        """Comprehensive health check."""
        checks = []

        # Infrastructure check
        infra_ok = self.infrastructure_checker.check_compatibility()
        checks.append(("Infrastructure", infra_ok))

        # Alembic state check
        alembic_ok, alembic_msg = self.infrastructure_checker.check_alembic_state()
        checks.append(("Alembic State", alembic_ok))
        if not alembic_ok:
            pass

        # Template validation
        template_ok = all(
            hasattr(template, "generate") for template in self.templates.values()
        )
        checks.append(("Template Modules", template_ok))

        # Summary
        passed_checks = sum(1 for _, status in checks if status)
        total_checks = len(checks)


        for _check_name, _status in checks:
            pass

        health_percentage = (passed_checks / total_checks) * 100

        return health_percentage >= 80

    def list_plugins(self) -> None:
        """List all existing plugins."""
        plugins_dir = Path("app/plugins")

        if not plugins_dir.exists():
            return

        # Look for plugin directories (v4 style)
        plugin_dirs = [
            d
            for d in plugins_dir.iterdir()
            if d.is_dir() and d.name.endswith("_plugin")
        ]

        # Also look for plugin files (v3 style)
        plugin_files = list(plugins_dir.glob("*_plugin.py"))

        total_plugins = len(plugin_dirs) + len(plugin_files)

        if total_plugins == 0:
            return


        # List v4 modular plugins
        for plugin_dir in plugin_dirs:
            plugin_dir.name.replace("_plugin", "").title()

            # Check files in directory
            list(plugin_dir.glob("*.py"))

            # Try to read metadata from __init__.py
            init_file = plugin_dir / "__init__.py"
            if init_file.exists():
                try:
                    with open(init_file) as f:
                        content = f.read()

                    # Extract version and description
                    import re

                    version_match = re.search(r'"version":\s*"([^"]+)"', content)
                    desc_match = re.search(r'"description":\s*"([^"]+)"', content)

                    version_match.group(1) if version_match else "Unknown"
                    (
                        desc_match.group(1) if desc_match else "No description"
                    )


                except Exception:
                    pass


        # List v3 single-file plugins
        for plugin_file in plugin_files:
            plugin_file.stem.replace("_plugin", "").title()
            plugin_file.stat().st_size


            try:
                with open(plugin_file) as f:
                    content = f.read()

                # Extract metadata
                import re

                version_match = re.search(r'version="([^"]+)"', content)
                desc_match = re.search(r'description="([^"]+)"', content)

                version_match.group(1) if version_match else "Unknown"
                desc_match.group(1) if desc_match else "No description"


            except Exception:
                pass


    def remove_plugin(self, model_name: str) -> bool:
        """Remove a plugin (both v3 and v4 styles)."""
        try:
            import re

            snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()


            removed_items = []

            # Check for v4 modular plugin directory
            plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
            if plugin_dir.exists() and plugin_dir.is_dir():
                # Remove directory and all files
                import shutil

                shutil.rmtree(plugin_dir)
                removed_items.append(f"Directory: {plugin_dir}")

            # Check for v3 single plugin file
            plugin_file = Path(f"app/plugins/{snake_name}_plugin.py")
            if plugin_file.exists():
                plugin_file.unlink()
                removed_items.append(f"File: {plugin_file}")

            return removed_items

        except Exception:
            return False

    def fix_plugins(self) -> None:
        """Fix common issues in existing plugins."""
        plugins_dir = Path("app/plugins")
        if not plugins_dir.exists():
            return

        # Find all plugins (both v3 and v4)
        plugin_dirs = [
            d
            for d in plugins_dir.iterdir()
            if d.is_dir() and d.name.endswith("_plugin")
        ]
        plugin_files = list(plugins_dir.glob("*_plugin.py"))

        if not plugin_dirs and not plugin_files:
            return

        total_fixes = 0

        # Fix v4 modular plugins
        for plugin_dir in plugin_dirs:
            fixes_applied = self.plugin_validator.fix_common_issues(plugin_dir)
            if fixes_applied:
                for _fix in fixes_applied:
                    pass
                total_fixes += len(fixes_applied)
            else:
                pass

        # Fix v3 single-file plugins
        for plugin_file in plugin_files:

            try:
                with open(plugin_file) as f:
                    content = f.read()

                original_content = content
                fixes_applied = []

                # Fix common issues (similar to v3 logic)
                if 'features=["crud", "search"(' in content:
                    import re

                    content = re.sub(
                        r'features=\["crud", "search"\([^)]*\)\([^)]*\)\]',
                        'features=["crud", "search", "tasks", "bulk"]',
                        content,
                    )
                    fixes_applied.append("Fixed malformed features list")

                if "self.metadata.status = PluginStatus.INITIALIZED" in content:
                    content = content.replace(
                        "self.metadata.status = PluginStatus.INITIALIZED",
                        "# Status will be set by plugin manager - don't override here",
                    )
                    fixes_applied.append("Removed status override")

                if "settings.SECRET_KEY" in content:
                    content = content.replace(
                        "settings.SECRET_KEY", "settings.jwt_secret_token",
                    )
                    fixes_applied.append("Fixed SECRET_KEY reference")

                # Write back if changes were made
                if content != original_content:
                    with open(plugin_file, "w") as f:
                        f.write(content)

                if fixes_applied:
                    for _fix in fixes_applied:
                        pass
                    total_fixes += len(fixes_applied)
                else:
                    pass

            except Exception:
                pass


    def cleanup_plugin(
        self, model_name: str, force: bool = False, keep_migrations: bool = False,
    ) -> bool | None:
        """Completely remove a plugin with database cleanup."""
        import re
        import subprocess
        from pathlib import Path

        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()


        if not force:
            if not keep_migrations:
                pass

            confirm = (
                input("Are you sure you want to continue? (y/N): ").strip().lower()
            )
            if confirm not in ["y", "yes"]:
                return False

        cleanup_steps = []

        try:
            # Step 1: Find and analyze the plugin

            plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
            plugin_file = Path(f"app/plugins/{snake_name}_plugin.py")

            if (plugin_dir.exists() and plugin_dir.is_dir()) or plugin_file.exists():
                pass
            else:
                return False

            # Step 2: Find related migration files
            migration_files = []
            migrations_dir = Path("alembic/versions")

            if migrations_dir.exists():
                # Look for migration files that mention the model
                for migration_file in migrations_dir.glob("*.py"):
                    try:
                        content = migration_file.read_text()
                        # Check if this migration creates the table
                        table_patterns = [
                            f"create_table('{snake_name}s'",  # Plural form
                            f"create_table('{snake_name}'",  # Singular form
                            f"op.create_table('{snake_name}s'",
                            f"op.create_table('{snake_name}'",
                            f"table_name='{snake_name}s'",
                            f"table_name='{snake_name}'",
                            f"'{model_name.lower()}s'",  # Lowercase variants
                            f"'{model_name.lower()}'",
                        ]

                        if any(pattern in content for pattern in table_patterns):
                            migration_files.append(migration_file)
                    except Exception:
                        pass

            if migration_files:
                pass
            else:
                pass

            # Step 3: Drop database tables
            try:
                # Get table names to drop
                table_names = [
                    f"{snake_name}s",
                    f"{snake_name}",
                    snake_name.lower() + "s",
                    snake_name.lower(),
                ]

                # Try to connect and drop tables
                from app.core.config import get_settings

                settings = get_settings()

                drop_commands = []
                for table_name in table_names:
                    drop_commands.append(f"DROP TABLE IF EXISTS {table_name} CASCADE;")

                # Execute drop commands
                for drop_cmd in drop_commands:
                    try:
                        result = subprocess.run(
                            [
                                "psql",
                                settings.database_url_without_async,
                                "-c",
                                drop_cmd,
                            ],
                            capture_output=True,
                            text=True,
                            timeout=30, check=False,
                        )

                        if result.returncode == 0:
                            # Check if anything was actually dropped
                            if "DROP TABLE" in result.stderr or not result.stderr:
                                cleanup_steps.append(
                                    f"Dropped table: {drop_cmd.split()[4]}",
                                )
                        else:
                            pass
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        pass

            except Exception:
                pass

            # Step 4: Remove migration files (if not keeping them)
            if not keep_migrations and migration_files:

                for migration_file in migration_files:
                    try:
                        migration_file.unlink()
                        cleanup_steps.append(
                            f"Removed migration: {migration_file.name}",
                        )
                    except Exception:
                        pass
            elif keep_migrations:
                pass
            else:
                pass

            # Step 5: Remove plugin files

            if plugin_dir.exists():
                import shutil

                shutil.rmtree(plugin_dir)
                cleanup_steps.append(f"Removed plugin directory: {plugin_dir}")

            if plugin_file.exists():
                plugin_file.unlink()
                cleanup_steps.append(f"Removed plugin file: {plugin_file}")

            # Step 6: Update Alembic state (if migrations were removed)
            if not keep_migrations and migration_files:
                try:
                    # Get current head
                    result = subprocess.run(
                        ["alembic", "current"], capture_output=True, text=True, check=False,
                    )
                    if result.returncode == 0:
                        pass
                    else:
                        pass
                except Exception:
                    pass

            # Summary
            for _step in cleanup_steps:
                pass

            if not keep_migrations and migration_files:
                pass
            else:
                pass

            return True

        except Exception:
            return False

    def auth_check(self) -> bool:
        """Check authentication system compatibility."""
        checks = []

        # Check if authentication components exist
        auth_components = [
            ("JWT Service", "app/core/jwt.py"),
            ("Security Service", "app/core/security.py"),
            ("User Model", "app/db/models/user.py"),
            ("Auth Routes", "app/api/v1/endpoints/auth.py"),
            ("User Service", "app/services/user_service.py"),
        ]

        for component_name, component_path in auth_components:
            exists = Path(component_path).exists()
            checks.append((component_name, exists))

        # Check authentication dependencies
        try:
            from app.core.jwt import jwt_service

            checks.append(("JWT Service Import", True))
        except ImportError:
            checks.append(("JWT Service Import", False))

        try:
            from app.core.security import security_service

            checks.append(("Security Service Import", True))
        except ImportError:
            checks.append(("Security Service Import", False))

        # Check database models
        try:
            from app.db.models.user import User

            checks.append(("User Model Import", True))
        except ImportError:
            checks.append(("User Model Import", False))

        # Summary
        passed = sum(1 for _, status in checks if status)
        total = len(checks)


        return passed == total

    def add_authentication_to_plugin(self, model_name: str, auth_config: dict) -> bool | None:
        """Add authentication to an existing plugin."""
        import re

        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()
        plugin_dir = Path(f"app/plugins/{snake_name}_plugin")

        if not plugin_dir.exists():
            return False

        try:
            # Backup existing files
            backup_dir = plugin_dir / "backup"
            backup_dir.mkdir(exist_ok=True)

            for file_name in ["models.py", "routes.py"]:
                source = plugin_dir / file_name
                if source.exists():
                    backup = backup_dir / f"{file_name}.backup"
                    backup.write_text(source.read_text())

            # Read existing fields from models.py
            fields = self._extract_fields_from_model(plugin_dir / "models.py")

            # Generate enhanced model with auth
            enhanced_config = {
                "enable_auth": True,
                "enable_ownership": auth_config.get("enable_ownership", False),
                "enable_audit": auth_config.get("enable_audit", True),
                "enable_soft_delete": auth_config.get("enable_soft_delete", False),
                "enable_versioning": False,
            }

            models_content = self.auth_templates["models"].generate(
                model_name, fields, self.field_validator, enhanced_config,
            )
            (plugin_dir / "models.py").write_text(models_content)

            # Generate enhanced routes with auth
            routes_config = {
                "enable_auth": True,
                "require_permissions": True,
                "enable_audit": auth_config.get("enable_audit", True),
                "enable_rate_limiting": True,
                "owner_based_access": auth_config.get("enable_ownership", False),
                "require_roles": auth_config.get("require_roles", []),
            }

            routes_content = self.auth_templates["routes"].generate(
                model_name,
                fields,
                routes_config,
                False,  # Assume no bulk for existing plugins
            )
            (plugin_dir / "routes.py").write_text(routes_content)

            # Generate migration for auth fields
            migration_success = self.migration_manager.generate_migration(
                f"{model_name}_add_auth",
            )

            if migration_success:
                return True
            return True

        except Exception:
            return False

    def generate_with_auth_preset(
        self,
        preset: str,
        model_name: str,
        fields: list,
        with_tasks: bool = False,
        with_bulk: bool = False,
    ):
        """Generate plugin with authentication presets."""
        # Define preset configurations
        presets = {
            "basic": {
                "enable_auth": True,
                "simple_token_auth": True,  # Simple JWT authentication
                "enable_ownership": False,
                "enable_audit": True,
                "enable_soft_delete": False,
                "enable_versioning": False,
                "enable_rate_limiting": True,
                "require_permissions": False,  # No role checks for basic
                "require_roles": [],
                "owner_based_access": False,
            },
            "secure": {
                "enable_auth": True,
                "simple_token_auth": False,  # Use permissions for secure
                "enable_ownership": True,
                "enable_audit": True,
                "enable_soft_delete": True,
                "enable_versioning": False,
                "enable_rate_limiting": True,
                "require_permissions": True,
                "require_roles": ["user"],
                "owner_based_access": True,
            },
            "enterprise": {
                "enable_auth": True,
                "simple_token_auth": False,  # Use full RBAC for enterprise
                "enable_ownership": True,
                "enable_audit": True,
                "enable_soft_delete": True,
                "enable_versioning": True,
                "enable_rate_limiting": True,
                "require_permissions": True,
                "require_roles": ["user"],
                "owner_based_access": True,
            },
        }

        auth_config = presets.get(preset)
        if not auth_config:
            return False

        for _key, _value in auth_config.items():
            pass

        return self.add_plugin(
            model_name, fields, with_tasks, with_bulk, True, auth_config,
        )

    def analyze_architecture(
        self, output_file: str | None = None, format_type: str = "text",
    ) -> bool:
        """Analyze project architecture and generate report."""
        try:
            # Run architecture analysis
            report = self.architecture_analyzer.analyze_project()

            # Generate report
            output_path = Path(output_file) if output_file else None

            if format_type == "json":
                # Convert report to JSON
                report_data = {
                    "health_score": report.health_score,
                    "metrics": report.metrics,
                    "plugins": [
                        {
                            "name": p.name,
                            "models": p.models,
                            "routes": p.routes,
                            "dependencies": p.dependencies,
                            "size_metrics": p.size_metrics,
                            "complexity_score": p.complexity_score,
                        }
                        for p in report.plugins
                    ],
                    "issues": [
                        {
                            "type": i.type,
                            "source": i.source,
                            "target": i.target,
                            "severity": i.severity,
                            "description": i.description,
                            "suggestion": i.suggestion,
                        }
                        for i in report.issues
                    ],
                    "recommendations": report.recommendations,
                    "dependency_graph": report.dependency_graph,
                }

                if output_path:
                    import json

                    output_path.write_text(json.dumps(report_data, indent=2))
                else:
                    import json

            else:
                # Generate text report
                self.architecture_analyzer.generate_report(
                    report, output_path,
                )
                if not output_path:
                    pass

            return True

        except Exception:
            return False

    def generate_test_suite(
        self,
        model_name: str,
        test_types: list[str],
        output_dir: str | None = None,
        with_auth: bool = False,
    ) -> bool:
        """Generate comprehensive test suite for a plugin."""
        try:
            # Find the plugin to get its details
            import re

            snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()
            plugin_dir = Path(f"app/plugins/{snake_name}_plugin")

            if not plugin_dir.exists():
                return False

            # Extract models and routes from plugin
            models = self._extract_models_from_plugin(plugin_dir)
            routes = self._extract_routes_from_plugin(plugin_dir)

            # Set up test configuration
            test_output_dir = (
                Path(output_dir)
                if output_dir
                else Path(f"tests/plugins/{snake_name}_plugin")
            )

            config = TestConfig(
                plugin_name=model_name,
                models=models,
                routes=routes,
                test_types=test_types,
                output_dir=test_output_dir,
                include_auth=with_auth,
                include_performance="load" in test_types,
            )

            # Generate test suite
            success = self.test_generator.generate_test_suite(config)

            if success and "load" in test_types:
                pass

            return success

        except Exception:
            return False

    def generate_smart_migration(
        self, model_name: str, changes: list[str] | None = None, auto_apply: bool = False,
    ) -> bool:
        """Generate smart migration with zero-downtime strategies."""
        try:
            # Set auto-apply mode in the migration manager
            if auto_apply:
                # Temporarily override the input function for auto-apply
                import builtins

                original_input = builtins.input
                builtins.input = lambda prompt: "y"

                try:
                    success = self.smart_migration_manager.generate_smart_migration(
                        model_name, changes,
                    )
                finally:
                    builtins.input = original_input
            else:
                success = self.smart_migration_manager.generate_smart_migration(
                    model_name, changes,
                )

            if success:
                pass

            return success

        except Exception:
            return False

    def _extract_models_from_plugin(self, plugin_dir: Path) -> list[str]:
        """Extract model names from plugin directory."""
        models_file = plugin_dir / "models.py"
        if not models_file.exists():
            return []

        try:
            import ast

            with open(models_file) as f:
                tree = ast.parse(f.read())

            models = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a SQLAlchemy model
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "Base":
                            models.append(node.name)
                            break
            return models
        except Exception:
            return []

    def _extract_routes_from_plugin(self, plugin_dir: Path) -> list[str]:
        """Extract route information from plugin directory."""
        routes_file = plugin_dir / "routes.py"
        if not routes_file.exists():
            return []

        try:
            import ast

            with open(routes_file) as f:
                tree = ast.parse(f.read())

            routes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Look for FastAPI route decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                if decorator.func.attr in [
                                    "get",
                                    "post",
                                    "put",
                                    "delete",
                                    "patch",
                                ]:
                                    routes.append(
                                        f"{decorator.func.attr.upper()} {node.name}",
                                    )
            return routes
        except Exception:
            return []

    def _extract_fields_from_model(self, model_file: Path) -> list:
        """Extract field definitions from existing model file."""
        if not model_file.exists():
            return []

        # This is a simplified field extraction
        # In a real implementation, you'd parse the Python AST
        content = model_file.read_text()
        fields = []

        # Extract basic field patterns (simplified)
        import re

        field_pattern = r"(\w+)\s*=\s*Column\((.*?)\)"
        matches = re.findall(field_pattern, content, re.MULTILINE)

        for field_name, column_def in matches:
            if field_name not in ["id", "created_at", "updated_at"]:
                # Extract basic type information
                if "String" in column_def:
                    field_type = "str"
                elif "Integer" in column_def:
                    field_type = "int"
                elif "Boolean" in column_def:
                    field_type = "bool"
                elif "Float" in column_def:
                    field_type = "float"
                else:
                    field_type = "str"  # Default

                fields.append(
                    {"name": field_name, "type": field_type, "constraints": []},
                )

        return fields


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FastAPI Scaffold Generator v4.0 - Modular Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add User name:str email:email age:int --with-tasks --with-bulk
  %(prog)s list
  %(prog)s remove Product
  %(prog)s cleanup Product --force --keep-migrations
  %(prog)s infra-check
  %(prog)s test Product name:str price:float:gt=0
  %(prog)s health-check
        """,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Generate a new plugin")
    add_parser.add_argument("model", help="Model name (PascalCase)")
    add_parser.add_argument(
        "fields", nargs="*", help="Field definitions (name:type[:constraints])",
    )
    add_parser.add_argument(
        "--with-tasks", action="store_true", help="Include background tasks",
    )
    add_parser.add_argument(
        "--with-bulk", action="store_true", help="Include bulk operations",
    )
    add_parser.add_argument(
        "--with-auth", action="store_true", help="Enable enterprise authentication",
    )
    add_parser.add_argument(
        "--auth-ownership",
        action="store_true",
        help="Enable owner-based access control",
    )
    add_parser.add_argument(
        "--auth-audit", action="store_true", default=True, help="Enable audit logging",
    )
    add_parser.add_argument(
        "--auth-soft-delete", action="store_true", help="Enable soft delete",
    )
    add_parser.add_argument(
        "--auth-versioning", action="store_true", help="Enable versioning",
    )
    add_parser.add_argument("--auth-roles", help="Required roles (comma-separated)")
    add_parser.add_argument(
        "--auth-rate-limit",
        action="store_true",
        default=True,
        help="Enable rate limiting",
    )

    # List command
    subparsers.add_parser("list", help="List all existing plugins")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a plugin")
    remove_parser.add_argument("model", help="Model name to remove")

    # Cleanup command (enhanced removal with database cleanup)
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Completely remove plugin with database cleanup",
    )
    cleanup_parser.add_argument("model", help="Model name to clean up")
    cleanup_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts",
    )
    cleanup_parser.add_argument(
        "--keep-migrations",
        action="store_true",
        help="Keep migration files (only remove plugin code)",
    )

    # Fix plugins command
    subparsers.add_parser("fix-plugins", help="Fix common plugin issues")

    # Infrastructure check command
    subparsers.add_parser("infra-check", help="Check infrastructure compatibility")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test plugin generation")
    test_parser.add_argument("model", help="Model name (PascalCase)")
    test_parser.add_argument(
        "fields", nargs="*", help="Field definitions (name:type[:constraints])",
    )

    # Health check command
    subparsers.add_parser("health-check", help="Run comprehensive system health check")

    # Fix Alembic command
    subparsers.add_parser("fix-alembic", help="Fix corrupted Alembic state")

    # Authentication commands
    add_auth_parser = subparsers.add_parser(
        "add-auth", help="Add authentication to existing plugin",
    )
    add_auth_parser.add_argument("model", help="Model name to add authentication to")
    add_auth_parser.add_argument(
        "--ownership", action="store_true", help="Enable owner-based access control",
    )
    add_auth_parser.add_argument(
        "--audit", action="store_true", default=True, help="Enable audit logging",
    )
    add_auth_parser.add_argument(
        "--soft-delete", action="store_true", help="Enable soft delete",
    )
    add_auth_parser.add_argument("--roles", help="Required roles (comma-separated)")

    # Auth check command
    subparsers.add_parser(
        "auth-check", help="Check authentication system compatibility",
    )

    # Generate auth preset command
    auth_preset_parser = subparsers.add_parser(
        "auth-preset", help="Generate with authentication presets",
    )
    auth_preset_parser.add_argument(
        "preset",
        choices=["basic", "secure", "enterprise"],
        help="Authentication preset level",
    )
    auth_preset_parser.add_argument("model", help="Model name (PascalCase)")
    auth_preset_parser.add_argument(
        "fields", nargs="*", help="Field definitions (name:type[:constraints])",
    )
    auth_preset_parser.add_argument(
        "--with-tasks", action="store_true", help="Include background tasks",
    )
    auth_preset_parser.add_argument(
        "--with-bulk", action="store_true", help="Include bulk operations",
    )

    # Architecture analysis command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze project architecture",
    )
    analyze_parser.add_argument("--output", help="Output file for analysis report")
    analyze_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format",
    )

    # Test generation command
    test_parser = subparsers.add_parser(
        "generate-tests", help="Generate comprehensive test suite",
    )
    test_parser.add_argument("model", help="Model name to generate tests for")
    test_parser.add_argument(
        "--types",
        nargs="+",
        choices=["unit", "integration", "e2e", "load"],
        default=["unit", "integration"],
        help="Types of tests to generate",
    )
    test_parser.add_argument("--output-dir", help="Output directory for tests")
    test_parser.add_argument(
        "--with-auth", action="store_true", help="Include authentication in tests",
    )

    # Smart migration command
    smart_migration_parser = subparsers.add_parser(
        "smart-migration", help="Generate smart migration with zero-downtime strategies",
    )
    smart_migration_parser.add_argument("model", help="Model name for migration")
    smart_migration_parser.add_argument(
        "--changes",
        nargs="*",
        help="Specific changes to apply (e.g. add_column:status:str:default=active, drop_column:old_field)",
    )
    smart_migration_parser.add_argument(
        "--auto-apply",
        action="store_true",
        help="Automatically apply the migration without prompting",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize generator
    generator = ScaffoldGeneratorV4()

    # Execute commands
    if args.command == "add":
        if not args.fields:
            return

        # Build auth configuration from arguments
        auth_config = None
        if args.with_auth:
            auth_config = {
                "enable_auth": True,
                "simple_token_auth": True,  # Use simple JWT token authentication by default
                "enable_ownership": args.auth_ownership,
                "enable_audit": args.auth_audit,
                "enable_soft_delete": args.auth_soft_delete,
                "enable_versioning": args.auth_versioning,
                "enable_rate_limiting": args.auth_rate_limit,
                "require_permissions": bool(
                    args.auth_roles,
                ),  # Only if roles are specified
                "require_roles": args.auth_roles.split(",") if args.auth_roles else [],
                "owner_based_access": args.auth_ownership,
            }

        success = generator.add_plugin(
            args.model,
            args.fields,
            args.with_tasks,
            args.with_bulk,
            args.with_auth,
            auth_config,
        )
        sys.exit(0 if success else 1)

    elif args.command == "infra-check":
        success = generator.infra_check()
        sys.exit(0 if success else 1)

    elif args.command == "test":
        if not args.fields:
            return

        success = generator.test_plugin(args.model, args.fields)
        sys.exit(0 if success else 1)

    elif args.command == "list":
        generator.list_plugins()

    elif args.command == "remove":
        success = generator.remove_plugin(args.model)
        sys.exit(0 if success else 1)

    elif args.command == "cleanup":
        success = generator.cleanup_plugin(
            args.model, force=args.force, keep_migrations=args.keep_migrations,
        )
        sys.exit(0 if success else 1)

    elif args.command == "fix-plugins":
        generator.fix_plugins()

    elif args.command == "health-check":
        healthy = generator.health_check()
        sys.exit(0 if healthy else 1)

    elif args.command == "fix-alembic":
        success = generator.migration_manager.fix_alembic_state()
        sys.exit(0 if success else 1)

    elif args.command == "add-auth":
        success = generator.add_authentication_to_plugin(
            args.model,
            {
                "enable_ownership": args.ownership,
                "enable_audit": args.audit,
                "enable_soft_delete": args.soft_delete,
                "require_roles": args.roles.split(",") if args.roles else [],
            },
        )
        sys.exit(0 if success else 1)

    elif args.command == "auth-check":
        success = generator.auth_check()
        sys.exit(0 if success else 1)

    elif args.command == "auth-preset":
        if not args.fields:
            return

        success = generator.generate_with_auth_preset(
            args.preset, args.model, args.fields, args.with_tasks, args.with_bulk,
        )
        sys.exit(0 if success else 1)

    elif args.command == "analyze":
        success = generator.analyze_architecture(args.output, args.format)
        sys.exit(0 if success else 1)

    elif args.command == "generate-tests":
        success = generator.generate_test_suite(
            args.model, args.types, args.output_dir, args.with_auth,
        )
        sys.exit(0 if success else 1)

    elif args.command == "smart-migration":
        success = generator.generate_smart_migration(
            args.model, args.changes, args.auto_apply,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
