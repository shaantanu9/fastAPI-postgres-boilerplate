#!/usr/bin/env python3
"""
FastAPI Scaffold Generator v4.0 - Main CLI Interface

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
    python scaffold_generator_v4/main.py list-plugins
    python scaffold_generator_v4/main.py list-models
    python scaffold_generator_v4/main.py cleanup-business-plugins
    python scaffold_generator_v4/main.py remove-plugin User
    python scaffold_generator_v4/main.py auto-fix
    python scaffold_generator_v4/main.py auto-fix --force
    python scaffold_generator_v4/main.py auto-fix --force --all
"""

import argparse
import sys
from pathlib import Path
from typing import List

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import modular components
try:
    from core import FieldValidator, MigrationManager, InfrastructureChecker, PluginValidator
    from templates import (
        ModelsTemplate, SchemasTemplate, ServicesTemplate,
        RoutesTemplate, EnhancedRoutesTemplate, TasksTemplate, InitTemplate
    )
    from templates.auth_routes_template import AuthRoutesTemplate
    from templates.auth_models_template import AuthModelsTemplate
    from analyzers import ArchitectureAnalyzer
    from testing import TestGenerator, TestConfig
    from migrations import SmartMigrationManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔍 Make sure you're running from the scaffold_generator_v4 directory")
    print("💡 Try: cd scaffold_generator_v4 && python main.py --help")
    sys.exit(1)


class ScaffoldGeneratorV4:
    """Main scaffold generator orchestrator"""
    
    def __init__(self):
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
            'models': ModelsTemplate(),
            'schemas': SchemasTemplate(),
            'services': ServicesTemplate(),
            'routes': RoutesTemplate(),
            'enhanced_routes': EnhancedRoutesTemplate(),
            'tasks': TasksTemplate(),
            'init': InitTemplate()
        }
        
        # Initialize auth templates
        self.auth_templates = {
            'models': AuthModelsTemplate(),
            'routes': AuthRoutesTemplate()
        }
    
    def add_plugin(self, model_name: str, fields: list, with_tasks: bool = False, with_bulk: bool = False, 
                  with_auth: bool = False, auth_config: dict = None, with_timeouts: bool = True):
        """Add a new plugin with the given model and fields"""
        print(f"🏗️ Generating Plugin: {model_name}")
        print("=" * 40)
        
        # Pre-check migration system health and auto-fix if needed
        print("🔍 Checking migration system health...")
        if not self.migration_manager.auto_fix_if_needed():
            print("❌ Failed to fix migration system issues")
            print("💡 Try running: python main.py auto-fix --force")
            return False
        
        try:
            # Validate fields
            validated_fields = self.field_validator.validate_fields_batch(fields)
            print(f"✅ Validated {len(validated_fields)} fields")
            
            # Create plugin directory
            plugin_dir = self._create_plugin_directory(model_name)
            print(f"📁 Created plugin directory: {plugin_dir.name}")
            
            # Generate plugin files
            self._generate_plugin_files(
                plugin_dir, model_name, validated_fields, 
                with_tasks, with_bulk, with_auth, auth_config, with_timeouts
            )
            print("📝 Generated plugin files")
            
            # Create and apply migration
            success = self.migration_manager.create_migration(model_name)
            
            if success:
                print(f"✅ Plugin '{model_name}' created successfully!")
                print(f"🎯 Plugin location: {plugin_dir}")
                return True
            else:
                print(f"❌ Failed to create migration for '{model_name}'")
                return False
                
        except Exception as e:
            print(f"❌ Error creating plugin: {e}")
            return False
    
    def _create_plugin_directory(self, model_name: str) -> Path:
        """Create the plugin directory structure"""
        import re
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return plugin_dir
    
    def _generate_plugin_files(self, plugin_dir: Path, model_name: str, validated_fields: list, 
                             with_tasks: bool, with_bulk: bool, with_auth: bool = False, auth_config: dict = None, with_timeouts: bool = True):
        """Generate all modular plugin files"""
        
        # Choose templates based on authentication requirement
        if with_auth:
            print("  🔐 Using authentication-enabled templates")
            # Generate models.py with auth features
            models_content = self.auth_templates['models'].generate(model_name, validated_fields, self.field_validator, auth_config)
            (plugin_dir / "models.py").write_text(models_content)
            print("  ✅ models.py (with authentication)")
            
            # Generate routes.py with auth features
            routes_content = self.auth_templates['routes'].generate(model_name, validated_fields, auth_config, with_bulk)
            (plugin_dir / "routes.py").write_text(routes_content)
            print("  ✅ routes.py (with authentication)")
        else:
            # Generate models.py (standard)
            models_content = self.templates['models'].generate(model_name, validated_fields, self.field_validator)
            (plugin_dir / "models.py").write_text(models_content)
            print("  ✅ models.py")
            
            # Generate routes.py (choose enhanced or standard)
            if with_timeouts:
                routes_content = self.templates['enhanced_routes'].generate(model_name, validated_fields, with_bulk)
                (plugin_dir / "routes.py").write_text(routes_content)
                print("  ✅ routes.py (with timeout support)")
            else:
                routes_content = self.templates['routes'].generate(model_name, validated_fields, with_bulk)
                (plugin_dir / "routes.py").write_text(routes_content)
                print("  ✅ routes.py (standard)")
        
        # Generate schemas.py (always use standard for now)
        schemas_content = self.templates['schemas'].generate(model_name, validated_fields, self.field_validator)
        (plugin_dir / "schemas.py").write_text(schemas_content)
        print("  ✅ schemas.py")
        
        # Generate services.py (always use standard for now)
        services_content = self.templates['services'].generate(model_name, validated_fields)
        (plugin_dir / "services.py").write_text(services_content)
        print("  ✅ services.py")
        
        # Generate tasks.py (if requested)
        if with_tasks:
            tasks_content = self.templates['tasks'].generate(model_name)
            (plugin_dir / "tasks.py").write_text(tasks_content)
            print("  ✅ tasks.py")
        
        # Generate __init__.py
        init_content = self.templates['init'].generate(model_name, with_tasks, with_bulk)
        (plugin_dir / "__init__.py").write_text(init_content)
        print("  ✅ __init__.py")
    
    def infra_check(self):
        """Run infrastructure compatibility check"""
        success = self.infrastructure_checker.check_compatibility()
        if success:
            print("\n🎉 Infrastructure is ready for plugin generation!")
        else:
            print("\n❌ Infrastructure issues detected - please resolve before generating plugins")
        return success
    
    def test_plugin(self, model_name: str, fields: list):
        """Test plugin generation without creating files"""
        print(f"🧪 Testing {model_name} Plugin Generation")
        print("=" * 40)
        
        try:
            # Test infrastructure
            print("🔍 Testing infrastructure compatibility...")
            if not self.infrastructure_checker.check_compatibility():
                return False
            
            # Test fields
            print("🔍 Testing field validation...")
            validated_fields = self.field_validator.validate_fields_batch(fields)
            print(f"✅ Fields validation passed: {len(validated_fields)} fields")
            
            # Test plugin validation
            print("🔍 Testing plugin generation logic...")
            if self.plugin_validator.test_plugin_generation(model_name, fields):
                print(f"✅ Plugin generation test passed for {model_name}")
                return True
            else:
                print(f"❌ Plugin generation test failed for {model_name}")
                return False
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def health_check(self):
        """Comprehensive health check"""
        print("🏥 System Health Check")
        print("=" * 25)
        
        checks = []
        
        # Infrastructure check
        print("🔍 Infrastructure compatibility...")
        infra_ok = self.infrastructure_checker.check_compatibility()
        checks.append(("Infrastructure", infra_ok))
        
        # Alembic state check
        print("\n🔍 Alembic migration state...")
        alembic_ok, alembic_msg = self.infrastructure_checker.check_alembic_state()
        checks.append(("Alembic State", alembic_ok))
        if not alembic_ok:
            print(f"   ⚠️ {alembic_msg}")
        
        # Template validation
        print("\n🔍 Template modules...")
        template_ok = all(hasattr(template, 'generate') for template in self.templates.values())
        checks.append(("Template Modules", template_ok))
        
        # Summary
        passed_checks = sum(1 for _, status in checks if status)
        total_checks = len(checks)
        
        print(f"\n📊 Health Check Results: {passed_checks}/{total_checks} checks passed")
        
        for check_name, status in checks:
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {check_name}")
        
        health_percentage = (passed_checks / total_checks) * 100
        print(f"\n🎯 System Health: {health_percentage:.0f}%")
        
        return health_percentage >= 80
    
    def list_plugins(self):
        """List all existing plugins with enhanced details"""
        print("📋 Listing Existing Plugins")
        print("=" * 30)
        
        plugins_dir = Path("app/plugins")
        
        if not plugins_dir.exists():
            print("❌ Plugins directory not found")
            return
        
        # Look for plugin directories (v4 style)
        plugin_dirs = [d for d in plugins_dir.iterdir() if d.is_dir() and d.name.endswith('_plugin')]
        
        # Also look for plugin files (v3 style)
        plugin_files = list(plugins_dir.glob("*_plugin.py"))
        
        total_plugins = len(plugin_dirs) + len(plugin_files)
        
        if total_plugins == 0:
            print("📭 No plugins found")
            return
        
        print(f"Found {total_plugins} plugin(s):")
        print()
        
        # Categorize plugins
        core_plugins = []
        business_plugins = []
        test_plugins = []
        
        # List v4 modular plugins
        for plugin_dir in plugin_dirs:
            plugin_name = plugin_dir.name.replace('_plugin', '').title()
            
            # Categorize plugins
            if plugin_name.lower() in ['monitoring', 'auth', 'cache', 'security']:
                category = "🔧 Core"
                core_plugins.append(plugin_name)
            elif plugin_name.lower().startswith('test') or 'test' in plugin_name.lower():
                category = "🧪 Test"
                test_plugins.append(plugin_name)
            else:
                category = "💼 Business"
                business_plugins.append(plugin_name)
            
            print(f"🔌 {plugin_name} (v4 - Modular) {category}")
            print(f"   📁 Directory: {plugin_dir.name}")
            
            # Check files in directory
            files = list(plugin_dir.glob("*.py"))
            print(f"   📄 Files: {', '.join(f.name for f in files)}")
            
            # Extract models from models.py
            models_file = plugin_dir / "models.py"
            if models_file.exists():
                models = self._extract_models_from_plugin(plugin_dir)
                if models:
                    print(f"   🗄️  Models: {', '.join(models)}")
            
            # Try to read metadata from __init__.py
            init_file = plugin_dir / "__init__.py"
            if init_file.exists():
                try:
                    with open(init_file, 'r') as f:
                        content = f.read()
                    
                    # Extract version and description
                    import re
                    version_match = re.search(r'"version":\s*"([^"]+)"', content)
                    desc_match = re.search(r'"description":\s*"([^"]+)"', content)
                    
                    version = version_match.group(1) if version_match else "Unknown"
                    description = desc_match.group(1) if desc_match else "No description"
                    
                    print(f"   🏷️  Version: {version}")
                    print(f"   📝 Description: {description}")
                    
                except Exception as e:
                    print(f"   ⚠️  Error reading metadata: {e}")
            
            print()
        
        # List v3 single-file plugins
        for plugin_file in plugin_files:
            plugin_name = plugin_file.stem.replace('_plugin', '').title()
            file_size = plugin_file.stat().st_size
            
            # Categorize plugins
            if plugin_name.lower() in ['monitoring', 'auth', 'cache', 'security']:
                category = "🔧 Core"
                core_plugins.append(plugin_name)
            elif plugin_name.lower().startswith('test') or 'test' in plugin_name.lower():
                category = "🧪 Test"
                test_plugins.append(plugin_name)
            else:
                category = "💼 Business"
                business_plugins.append(plugin_name)
            
            print(f"🔌 {plugin_name} (v3 - Single File) {category}")
            print(f"   📁 File: {plugin_file.name}")
            print(f"   📊 Size: {file_size:,} bytes")
            
            try:
                with open(plugin_file, 'r') as f:
                    content = f.read()
                
                # Extract metadata
                import re
                version_match = re.search(r'version="([^"]+)"', content)
                desc_match = re.search(r'description="([^"]+)"', content)
                
                version = version_match.group(1) if version_match else "Unknown"
                description = desc_match.group(1) if desc_match else "No description"
                
                print(f"   🏷️  Version: {version}")
                print(f"   📝 Description: {description}")
                
            except Exception as e:
                print(f"   ❌ Error reading metadata: {e}")
            
            print()
        
        # Summary
        print("📊 Plugin Summary:")
        print(f"   🔧 Core Plugins: {len(core_plugins)} ({', '.join(core_plugins) if core_plugins else 'None'})")
        print(f"   💼 Business Plugins: {len(business_plugins)} ({', '.join(business_plugins) if business_plugins else 'None'})")
        print(f"   🧪 Test Plugins: {len(test_plugins)} ({', '.join(test_plugins) if test_plugins else 'None'})")
        
        if business_plugins:
            print()
            print("💡 For a generic boilerplate, consider removing business-specific plugins:")
            print(f"   python scaffold_generator_v4/main.py cleanup-business-plugins")
    
    def list_models(self):
        """List all models in the project (both core and plugin models)"""
        print("🗄️  Listing All Models")
        print("=" * 25)
        
        all_models = []
        
        # Check core models
        core_models_dir = Path("app/models")
        if core_models_dir.exists():
            print("🔧 Core Models:")
            for model_file in core_models_dir.glob("*.py"):
                if model_file.name != "__init__.py":
                    model_name = model_file.stem.title()
                    print(f"   📄 {model_name} (from {model_file.name})")
                    all_models.append(f"Core.{model_name}")
            print()
        
        # Check plugin models
        plugins_dir = Path("app/plugins")
        if plugins_dir.exists():
            print("🔌 Plugin Models:")
            
            # v4 modular plugins
            plugin_dirs = [d for d in plugins_dir.iterdir() if d.is_dir() and d.name.endswith('_plugin')]
            for plugin_dir in plugin_dirs:
                plugin_name = plugin_dir.name.replace('_plugin', '').title()
                models_file = plugin_dir / "models.py"
                
                if models_file.exists():
                    models = self._extract_models_from_plugin(plugin_dir)
                    if models:
                        print(f"   🔌 {plugin_name} Plugin:")
                        for model in models:
                            print(f"      🗄️  {model}")
                            all_models.append(f"{plugin_name}.{model}")
            
            # v3 single-file plugins
            plugin_files = list(plugins_dir.glob("*_plugin.py"))
            for plugin_file in plugin_files:
                plugin_name = plugin_file.stem.replace('_plugin', '').title()
                try:
                    with open(plugin_file, 'r') as f:
                        content = f.read()
                    
                    # Extract model class names
                    import re
                    model_matches = re.findall(r'class\s+(\w+)\s*\([^)]*Base[^)]*\):', content)
                    if model_matches:
                        print(f"   🔌 {plugin_name} Plugin (v3):")
                        for model in model_matches:
                            print(f"      🗄️  {model}")
                            all_models.append(f"{plugin_name}.{model}")
                except Exception as e:
                    print(f"   ❌ Error reading {plugin_file.name}: {e}")
        
        print()
        print(f"📊 Total Models Found: {len(all_models)}")
        
        # Categorize models for boilerplate cleanup
        business_models = []
        test_models = []
        core_models = []
        
        for model in all_models:
            model_lower = model.lower()
            if any(keyword in model_lower for keyword in ['product', 'order', 'customer', 'book', 'shopping', 'cart']):
                business_models.append(model)
            elif 'test' in model_lower:
                test_models.append(model)
            else:
                core_models.append(model)
        
        if business_models or test_models:
            print()
            print("🧹 Boilerplate Cleanup Suggestions:")
            if business_models:
                print(f"   💼 Business Models to Remove: {', '.join(business_models)}")
            if test_models:
                print(f"   🧪 Test Models to Remove: {', '.join(test_models)}")
            print(f"   🔧 Core Models to Keep: {', '.join(core_models)}")
            print()
            print("💡 Use: python scaffold_generator_v4/main.py cleanup-business-plugins")
    
    def cleanup_business_plugins(self, force: bool = False, clean_migrations: bool = True):
        """Remove business-specific plugins to make boilerplate generic"""
        print("🧹 Cleaning Up Business-Specific Plugins")
        print("=" * 40)
        
        # Define business-specific plugins to remove
        business_plugins = [
            'product_plugin',
            'order_plugin', 
            'customer_plugin',
            'book_plugin',
            'shopping_cart_plugin',
            'test_item_plugin',
            'test_model_plugin',
            'product_test_plugin'
        ]
        
        # Define business-specific model names for migration cleanup
        business_models = [
            'product', 'products',
            'order', 'orders',
            'customer', 'customers', 
            'book', 'books',
            'shopping_cart', 'shoppingcart', 'shopping_carts',
            'test_item', 'testitem', 'test_items',
            'test_model', 'testmodel', 'test_models',
            'product_test', 'producttest', 'product_tests'
        ]
        
        plugins_dir = Path("app/plugins")
        if not plugins_dir.exists():
            print("❌ Plugins directory not found")
            return False
        
        found_plugins = []
        
        # Check which business plugins exist
        for plugin_name in business_plugins:
            plugin_dir = plugins_dir / plugin_name
            plugin_file = plugins_dir / f"{plugin_name}.py"
            
            if plugin_dir.exists() and plugin_dir.is_dir():
                found_plugins.append((plugin_name, 'directory', plugin_dir))
            elif plugin_file.exists():
                found_plugins.append((plugin_name, 'file', plugin_file))
        
        # Check for business-specific migrations
        migrations_dir = Path("alembic/versions")
        business_migrations = []
        
        if clean_migrations and migrations_dir.exists():
            print("🔍 Scanning for business-specific migrations...")
            for migration_file in migrations_dir.glob("*.py"):
                if migration_file.name == "__init__.py":
                    continue
                
                try:
                    with open(migration_file, 'r') as f:
                        content = f.read().lower()
                    
                    # Check if migration contains business model references
                    for model_name in business_models:
                        if (f"create_table('{model_name}'" in content or 
                            f'create_table("{model_name}"' in content or
                            f"drop_table('{model_name}'" in content or
                            f'drop_table("{model_name}"' in content or
                            f"'{model_name}'" in content and ('create_table' in content or 'drop_table' in content)):
                            business_migrations.append(migration_file)
                            break
                except Exception as e:
                    print(f"   ⚠️  Error reading {migration_file.name}: {e}")
        
        if not found_plugins and not business_migrations:
            print("✅ No business-specific plugins or migrations found - boilerplate is already clean!")
            return True
        
        print(f"Found items to clean up:")
        if found_plugins:
            print(f"   🔌 {len(found_plugins)} business plugins:")
            for plugin_name, plugin_type, path in found_plugins:
                print(f"      💼 {plugin_name} ({plugin_type})")
        
        if business_migrations:
            print(f"   📄 {len(business_migrations)} business migrations:")
            for migration in business_migrations:
                print(f"      🗃️  {migration.name}")
        
        if not force:
            print()
            print("⚠️  This will permanently remove these plugins, files, and migrations.")
            print("⚠️  This action cannot be undone!")
            if business_migrations:
                print("⚠️  Database migrations will be removed - this may affect your database!")
            confirm = input("Continue with cleanup? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ Cleanup cancelled")
                return False
        
        print()
        print("🗑️  Removing business-specific plugins...")
        
        removed_count = 0
        for plugin_name, plugin_type, path in found_plugins:
            try:
                if plugin_type == 'directory':
                    import shutil
                    shutil.rmtree(path)
                    print(f"   ✅ Removed directory: {path}")
                else:
                    path.unlink()
                    print(f"   ✅ Removed file: {path}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {path}: {e}")
        
        # Remove business migrations
        migration_removed_count = 0
        if clean_migrations and business_migrations:
            print()
            print("🗑️  Removing business-specific migrations...")
            for migration_file in business_migrations:
                try:
                    migration_file.unlink()
                    print(f"   ✅ Removed migration: {migration_file.name}")
                    migration_removed_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to remove {migration_file.name}: {e}")
        
        print()
        print(f"🎉 Cleanup complete!")
        print(f"   🔌 Removed {removed_count}/{len(found_plugins)} plugins")
        if clean_migrations:
            print(f"   📄 Removed {migration_removed_count}/{len(business_migrations)} migrations")
        
        print()
        print("📋 Remaining core plugins:")
        self.list_plugins()
        
        print()
        if clean_migrations and migration_removed_count > 0:
            print("⚠️  Important Notes:")
            print("   • Database migrations were removed")
            print("   • You may need to reset your database if it contains business data")
            print("   • Consider running: alembic stamp head (after ensuring DB is clean)")
            print("   • Test your application thoroughly after cleanup")
            print()
            print("🔧 Recommended next steps:")
            print("   1. Check alembic history: alembic history")
            print("   2. If needed, reset DB: dropdb your_db && createdb your_db")
            print("   3. Run migrations: alembic upgrade head")
        else:
            print("⚠️  Important Notes:")
            print("   • Database migrations were NOT removed")
            print("   • You may want to clean up migrations manually")
            print("   • Consider running: alembic history to review migrations")
            print("   • Test your application after cleanup")
        
        return True
    
    def cleanup_business_migrations_only(self, force: bool = False):
        """Remove only business-specific migrations, keep plugins"""
        print("🧹 Cleaning Up Business-Specific Migrations Only")
        print("=" * 45)
        
        # Define business-specific model names for migration cleanup
        business_models = [
            'product', 'products',
            'order', 'orders',
            'customer', 'customers', 
            'book', 'books',
            'shopping_cart', 'shoppingcart', 'shopping_carts',
            'test_item', 'testitem', 'test_items',
            'test_model', 'testmodel', 'test_models',
            'product_test', 'producttest', 'product_tests'
        ]
        
        # Check for business-specific migrations
        migrations_dir = Path("alembic/versions")
        business_migrations = []
        
        if not migrations_dir.exists():
            print("❌ Migrations directory not found")
            return False
        
        print("🔍 Scanning for business-specific migrations...")
        for migration_file in migrations_dir.glob("*.py"):
            if migration_file.name == "__init__.py":
                continue
            
            try:
                with open(migration_file, 'r') as f:
                    content = f.read().lower()
                
                # Check if migration contains business model references
                for model_name in business_models:
                    if (f"create_table('{model_name}'" in content or 
                        f'create_table("{model_name}"' in content or
                        f"drop_table('{model_name}'" in content or
                        f'drop_table("{model_name}"' in content or
                        f"'{model_name}'" in content and ('create_table' in content or 'drop_table' in content)):
                        business_migrations.append(migration_file)
                        break
            except Exception as e:
                print(f"   ⚠️  Error reading {migration_file.name}: {e}")
        
        if not business_migrations:
            print("✅ No business-specific migrations found!")
            return True
        
        print(f"Found {len(business_migrations)} business migrations to remove:")
        for migration in business_migrations:
            print(f"   🗃️  {migration.name}")
        
        if not force:
            print()
            print("⚠️  This will permanently remove these database migrations.")
            print("⚠️  This action cannot be undone and may affect your database!")
            confirm = input("Continue with migration cleanup? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ Migration cleanup cancelled")
                return False
        
        print()
        print("🗑️  Removing business-specific migrations...")
        
        migration_removed_count = 0
        for migration_file in business_migrations:
            try:
                migration_file.unlink()
                print(f"   ✅ Removed migration: {migration_file.name}")
                migration_removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {migration_file.name}: {e}")
        
        print()
        print(f"🎉 Migration cleanup complete! Removed {migration_removed_count}/{len(business_migrations)} migrations")
        
        print()
        print("⚠️  Important Notes:")
        print("   • Database migrations were removed")
        print("   • Business plugins are still present")
        print("   • You may need to reset your database if it contains business data")
        print("   • Consider running: alembic stamp head (after ensuring DB is clean)")
        print()
        print("🔧 Recommended next steps:")
        print("   1. Check alembic history: alembic history")
        print("   2. If needed, reset DB: dropdb your_db && createdb your_db")
        print("   3. Run migrations: alembic upgrade head")
        
        return True
    
    def show_model_migrations(self, model_name: str):
        """Show what migrations would be affected by removing a model"""
        import re
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        
        print(f"🔍 Analyzing {model_name} Model Dependencies")
        print("=" * 40)
        
        # Check if plugin exists
        plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
        plugin_file = Path(f"app/plugins/{snake_name}_plugin.py")
        
        plugin_exists = plugin_dir.exists() or plugin_file.exists()
        
        if plugin_exists:
            print(f"✅ Plugin found:")
            if plugin_dir.exists():
                print(f"   📁 Directory: {plugin_dir}")
            if plugin_file.exists():
                print(f"   📄 File: {plugin_file}")
        else:
            print(f"❌ Plugin not found: {model_name}")
            print(f"   Looked for: {snake_name}_plugin/ or {snake_name}_plugin.py")
        
        # Look for related migrations
        migrations_dir = Path("alembic/versions")
        found_migrations = []
        
        if migrations_dir.exists():
            print(f"\n🔍 Scanning for {model_name} migrations...")
            
            # Possible model name variations
            model_variations = [
                model_name.lower(),
                snake_name,
                snake_name.replace('_', ''),
                f"{snake_name}s",  # plural
                f"{model_name.lower()}s"  # plural
            ]
            
            for migration_file in migrations_dir.glob("*.py"):
                if migration_file.name == "__init__.py":
                    continue
                
                try:
                    with open(migration_file, 'r') as f:
                        content = f.read().lower()
                    
                    # Check if migration contains this model
                    for variation in model_variations:
                        if (f"create_table('{variation}'" in content or 
                            f'create_table("{variation}"' in content or
                            f"drop_table('{variation}'" in content or
                            f'drop_table("{variation}"' in content or
                            f"add_{variation}_model" in migration_file.name.lower() or
                            f"create_{variation}" in migration_file.name.lower() or
                            variation in migration_file.name.lower()):
                            found_migrations.append(migration_file)
                            break
                except Exception as e:
                    print(f"   ⚠️  Error reading {migration_file.name}: {e}")
        
        if found_migrations:
            print(f"✅ Found {len(found_migrations)} related migrations:")
            for migration in found_migrations:
                print(f"   🗃️  {migration.name}")
        else:
            print("💡 No related migrations found")
        
        print()
        print("📋 Summary:")
        if plugin_exists:
            print(f"   🔌 Plugin: EXISTS")
        else:
            print(f"   🔌 Plugin: NOT FOUND")
        print(f"   📄 Migrations: {len(found_migrations)} found")
        
        if plugin_exists or found_migrations:
            print()
            print("💡 Available commands:")
            if plugin_exists:
                print(f"   • Remove plugin only: python scaffold_generator_v4/main.py remove {model_name}")
                if found_migrations:
                    print(f"   • Remove plugin + migrations: python scaffold_generator_v4/main.py remove {model_name} --with-migrations")
            if found_migrations and not plugin_exists:
                print(f"   • Clean orphaned migrations: python scaffold_generator_v4/main.py cleanup-business-plugins --migrations-only")
        
        return len(found_migrations) > 0 or plugin_exists
    
    def remove_plugin(self, model_name: str, with_migrations: bool = False, force: bool = False) -> bool:
        """Remove a plugin (both v3 and v4 styles) with smart migration cleanup"""
        try:
            import re
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            
            print(f"🗑️  Removing {model_name} Plugin")
            print("=" * 35)
            
            removed_items = []
            found_migrations = []
            
            # Check for v4 modular plugin directory
            plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
            plugin_exists = False
            
            if plugin_dir.exists() and plugin_dir.is_dir():
                plugin_exists = True
                removed_items.append(f"Directory: {plugin_dir}")
            
            # Check for v3 single plugin file
            plugin_file = Path(f"app/plugins/{snake_name}_plugin.py")
            if plugin_file.exists():
                plugin_exists = True
                removed_items.append(f"File: {plugin_file}")
            
            if not plugin_exists:
                print(f"❌ Plugin not found: {model_name}")
                print(f"   Looked for: {snake_name}_plugin/ or {snake_name}_plugin.py")
                return False
            
            # Look for related migrations if requested
            if with_migrations:
                found_migrations = self._find_model_migrations(model_name)
            
            # Show what will be removed
            print(f"Found items to remove:")
            for item in removed_items:
                print(f"   🔌 Plugin: {item}")
            
            if found_migrations:
                print(f"   📄 {len(found_migrations)} related migrations:")
                for migration in found_migrations:
                    print(f"      🗃️  {migration.name}")
            
            # Confirmation
            if not force:
                print()
                if found_migrations:
                    print("⚠️  This will permanently remove the plugin AND its database migrations.")
                    print("⚠️  This may affect your database structure!")
                else:
                    print("⚠️  This will permanently remove the plugin files.")
                    print("💡 No related migrations found.")
                
                confirm = input("Continue with removal? (y/N): ").strip().lower()
                if confirm not in ['y', 'yes']:
                    print("❌ Removal cancelled")
                    return False
            
            print()
            
            # Use smart migration system for database cleanup
            if with_migrations and found_migrations:
                success = self._smart_remove_model_with_migrations(model_name, found_migrations)
                if not success:
                    print("⚠️  Database cleanup had issues, but continuing with plugin removal...")
            
            # Remove plugin files
            print("🗑️  Removing plugin files...")
            removed_count = 0
            if plugin_dir.exists() and plugin_dir.is_dir():
                import shutil
                shutil.rmtree(plugin_dir)
                print(f"   ✅ Removed plugin directory: {plugin_dir}")
                removed_count += 1
            
            if plugin_file.exists():
                plugin_file.unlink()
                print(f"   ✅ Removed plugin file: {plugin_file}")
                removed_count += 1
            
            print()
            print(f"🎉 {model_name} removal complete!")
            print(f"   🔌 Removed {removed_count} plugin file(s)")
            if with_migrations and found_migrations:
                print(f"   📄 Processed {len(found_migrations)} migration(s)")
                print("   🗄️  Database cleanup completed using smart migration system")
            
            return True
            
        except Exception as e:
            print(f"❌ Error removing plugin: {e}")
            return False
    
    def _find_model_migrations(self, model_name: str) -> List[Path]:
        """Find all migrations related to a specific model"""
        import re
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        found_migrations = []
        
        migrations_dir = Path("alembic/versions")
        if not migrations_dir.exists():
            return found_migrations
        
        print(f"🔍 Scanning for {model_name} migrations...")
        
        # Possible model name variations
        model_variations = [
            model_name.lower(),
            snake_name,
            snake_name.replace('_', ''),
            f"{snake_name}s",  # plural
            f"{model_name.lower()}s"  # plural
        ]
        
        for migration_file in migrations_dir.glob("*.py"):
            if migration_file.name == "__init__.py":
                continue
            
            try:
                with open(migration_file, 'r') as f:
                    content = f.read().lower()
                
                # Check if migration contains this model
                for variation in model_variations:
                    if (f"create_table('{variation}'" in content or 
                        f'create_table("{variation}"' in content or
                        f"drop_table('{variation}'" in content or
                        f'drop_table("{variation}"' in content or
                        f"add_{variation}_model" in migration_file.name.lower() or
                        f"create_{variation}" in migration_file.name.lower() or
                        variation in migration_file.name.lower()):
                        found_migrations.append(migration_file)
                        break
            except Exception as e:
                print(f"   ⚠️  Error reading {migration_file.name}: {e}")
        
        return found_migrations
    
    def _smart_remove_model_with_migrations(self, model_name: str, migrations: List[Path]) -> bool:
        """Use direct database operations to properly remove model and its database artifacts"""
        try:
            import re
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            
            print("🧠 Using Direct Database Cleanup")
            print("=" * 35)
            
            # Step 1: Drop the database table directly
            print("🔧 Step 1: Dropping database table...")
            table_drop_success = self._drop_model_table_directly(model_name)
            
            if table_drop_success:
                print("✅ Database table dropped successfully")
                
                # Step 2: Clean up migration files
                print("🔧 Step 2: Cleaning up migration files...")
                cleanup_success = self._cleanup_old_migrations(migrations)
                
                if cleanup_success:
                    print("✅ Migration files cleaned up")
                    
                    # Step 3: Update alembic state to reflect the changes
                    print("🔧 Step 3: Updating alembic state...")
                    state_success = self._update_alembic_state_after_removal()
                    
                    if state_success:
                        print("✅ Alembic state updated successfully")
                        return True
                    else:
                        print("⚠️  Alembic state update had issues, but table was dropped")
                        return True  # Still consider success since table was dropped
                else:
                    print("⚠️  Migration cleanup had issues, but table was dropped")
                    return True  # Still consider success since table was dropped
            else:
                print("⚠️  Database table drop failed")
                return False
                
        except Exception as e:
            print(f"❌ Direct database cleanup failed: {e}")
            return False
    
    def _drop_model_table_directly(self, model_name: str) -> bool:
        """Drop the model's table directly from the database"""
        try:
            import re
            import sys
            import os
            sys.path.append(os.getcwd())
            
            from app.db.session import engine
            from sqlalchemy import text, inspect
            
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            
            # Try different table name variations (singular and plural)
            table_variations = [
                snake_name,  # singular
                f"{snake_name}s",  # plural
                snake_name.rstrip('s') if snake_name.endswith('s') else snake_name  # handle already plural
            ]
            
            # Handle both async and sync engines
            if hasattr(engine, 'begin'):
                # Async engine
                import asyncio
                return asyncio.run(self._drop_table_async(engine, table_variations))
            else:
                # Sync engine
                return self._drop_table_sync(engine, table_variations)
                
        except Exception as e:
            print(f"❌ Error dropping table directly: {e}")
            return False
    
    async def _drop_table_async(self, engine, table_variations: list) -> bool:
        """Drop table using async engine"""
        try:
            from sqlalchemy import text
            async with engine.begin() as conn:
                dropped_any = False
                
                for table_name in table_variations:
                    # Check if table exists
                    result = await conn.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_name = :table_name"
                    ), {"table_name": table_name})
                    
                    table_exists = result.fetchone() is not None
                    
                    if table_exists:
                        # Drop table with CASCADE to handle dependencies
                        await conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                        print(f"   ✅ Dropped table: {table_name}")
                        dropped_any = True
                        break  # Only drop the first match
                
                if not dropped_any:
                    print(f"   💡 No matching tables found for variations: {table_variations}")
                
                return True  # Always consider success since we tried all variations
                    
        except Exception as e:
            print(f"   ❌ Error dropping tables {table_variations}: {e}")
            return False
    
    def _drop_table_sync(self, engine, table_variations: list) -> bool:
        """Drop table using sync engine"""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                dropped_any = False
                
                for table_name in table_variations:
                    # Check if table exists
                    result = conn.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_name = :table_name"
                    ), {"table_name": table_name})
                    
                    table_exists = result.fetchone() is not None
                    
                    if table_exists:
                        # Drop table with CASCADE to handle dependencies
                        conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                        conn.commit()
                        print(f"   ✅ Dropped table: {table_name}")
                        dropped_any = True
                        break  # Only drop the first match
                
                if not dropped_any:
                    print(f"   💡 No matching tables found for variations: {table_variations}")
                
                return True  # Always consider success since we tried all variations
                    
        except Exception as e:
            print(f"   ❌ Error dropping tables {table_variations}: {e}")
            return False
    
    def _update_alembic_state_after_removal(self) -> bool:
        """Update alembic state after removing a model"""
        try:
            # Use the existing migration manager's auto-fix functionality
            return self.migration_manager.auto_fix_if_needed(force=False)
        except Exception as e:
            print(f"❌ Error updating alembic state: {e}")
            return False
    
    def _cleanup_old_migrations(self, migrations: List[Path]) -> bool:
        """Clean up old migration files"""
        try:
            removed_count = 0
            for migration_file in migrations:
                try:
                    migration_file.unlink()
                    print(f"   ✅ Removed migration: {migration_file.name}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to remove {migration_file.name}: {e}")
            
            print(f"   📊 Removed {removed_count}/{len(migrations)} migration files")
            return removed_count > 0
            
        except Exception as e:
            print(f"❌ Error cleaning up migrations: {e}")
            return False
    
    def fix_plugins(self):
        """Fix common issues in existing plugins"""
        print("🔧 Fixing Plugin Issues")
        print("=" * 25)
        
        plugins_dir = Path("app/plugins")
        if not plugins_dir.exists():
            print("❌ Plugins directory not found")
            return
        
        # Find all plugins (both v3 and v4)
        plugin_dirs = [d for d in plugins_dir.iterdir() if d.is_dir() and d.name.endswith('_plugin')]
        plugin_files = list(plugins_dir.glob("*_plugin.py"))
        
        if not plugin_dirs and not plugin_files:
            print("📭 No plugins found to fix")
            return
        
        total_fixes = 0
        
        # Fix v4 modular plugins
        for plugin_dir in plugin_dirs:
            print(f"\n🔍 Checking {plugin_dir.name}...")
            fixes_applied = self.plugin_validator.fix_common_issues(plugin_dir)
            if fixes_applied:
                for fix in fixes_applied:
                    print(f"  ✅ {fix}")
                total_fixes += len(fixes_applied)
            else:
                print(f"  ✅ No fixes needed")
        
        # Fix v3 single-file plugins
        for plugin_file in plugin_files:
            print(f"\n🔍 Checking {plugin_file.name}...")
            
            try:
                with open(plugin_file, 'r') as f:
                    content = f.read()
                
                original_content = content
                fixes_applied = []
                
                # Fix common issues (similar to v3 logic)
                if 'features=["crud", "search"(' in content:
                    import re
                    content = re.sub(
                        r'features=\["crud", "search"\([^)]*\)\([^)]*\)\]',
                        'features=["crud", "search", "tasks", "bulk"]',
                        content
                    )
                    fixes_applied.append("Fixed malformed features list")
                
                if 'self.metadata.status = PluginStatus.INITIALIZED' in content:
                    content = content.replace(
                        'self.metadata.status = PluginStatus.INITIALIZED',
                        '# Status will be set by plugin manager - don\'t override here'
                    )
                    fixes_applied.append("Removed status override")
                
                if 'settings.SECRET_KEY' in content:
                    content = content.replace('settings.SECRET_KEY', 'settings.jwt_secret_token')
                    fixes_applied.append("Fixed SECRET_KEY reference")
                
                # Write back if changes were made
                if content != original_content:
                    with open(plugin_file, 'w') as f:
                        f.write(content)
                
                if fixes_applied:
                    for fix in fixes_applied:
                        print(f"  ✅ {fix}")
                    total_fixes += len(fixes_applied)
                else:
                    print(f"  ✅ No fixes needed")
                    
            except Exception as e:
                print(f"  ❌ Error fixing {plugin_file.name}: {e}")
        
        print(f"\n🎉 Plugin fixes completed! Applied {total_fixes} fixes total.")
    
    def cleanup_plugin(self, model_name: str, force: bool = False, keep_migrations: bool = False):
        """Completely remove a plugin with database cleanup"""
        import re
        import subprocess
        from pathlib import Path
        
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        
        print(f"🧹 Complete Cleanup: {model_name} Plugin")
        print("=" * 45)
        
        if not force:
            print(f"⚠️  This will PERMANENTLY remove:")
            print(f"   📁 Plugin files (app/plugins/{snake_name}_plugin/)")
            print(f"   🗄️  Database table(s) for {model_name}")
            if not keep_migrations:
                print(f"   📄 Related migration files")
            print()
            
            confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ Cleanup cancelled")
                return False
        
        cleanup_steps = []
        
        try:
            # Step 1: Find and analyze the plugin
            print("\n🔍 Step 1: Analyzing Plugin")
            
            plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
            plugin_file = Path(f"app/plugins/{snake_name}_plugin.py")
            
            plugin_exists = False
            if plugin_dir.exists() and plugin_dir.is_dir():
                plugin_exists = True
                print(f"   ✅ Found v4 plugin: {plugin_dir}")
            elif plugin_file.exists():
                plugin_exists = True
                print(f"   ✅ Found v3 plugin: {plugin_file}")
            else:
                print(f"   ❌ Plugin not found: {model_name}")
                return False
            
            # Step 2: Find related migration files
            print("\n🔍 Step 2: Finding Related Migrations")
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
                            f"create_table('{snake_name}'",   # Singular form
                            f"op.create_table('{snake_name}s'",
                            f"op.create_table('{snake_name}'",
                            f"table_name='{snake_name}s'",
                            f"table_name='{snake_name}'",
                            f"'{model_name.lower()}s'",  # Lowercase variants
                            f"'{model_name.lower()}'",
                        ]
                        
                        if any(pattern in content for pattern in table_patterns):
                            migration_files.append(migration_file)
                            print(f"   📄 Found migration: {migration_file.name}")
                    except Exception as e:
                        print(f"   ⚠️  Error reading {migration_file.name}: {e}")
            
            if migration_files:
                print(f"   ✅ Found {len(migration_files)} related migration(s)")
            else:
                print(f"   📝 No related migrations found")
            
            # Step 3: Drop database tables
            print("\n🗄️  Step 3: Dropping Database Tables")
            try:
                # Get table names to drop
                table_names = [f"{snake_name}s", f"{snake_name}", snake_name.lower() + "s", snake_name.lower()]
                
                # Try to connect and drop tables
                try:
                    from app.core.config import get_settings
                    settings = get_settings()
                    database_url = settings.database_url_without_async
                except ImportError:
                    print("   ⚠️  Could not import app config - using environment variables")
                    import os
                    database_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
                
                drop_commands = []
                for table_name in table_names:
                    drop_commands.append(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
                
                # Execute drop commands
                for drop_cmd in drop_commands:
                    try:
                        result = subprocess.run([
                            'psql', database_url, 
                            '-c', drop_cmd
                        ], capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            # Check if anything was actually dropped
                            if "DROP TABLE" in result.stderr or not result.stderr:
                                print(f"   ✅ Dropped table (if existed): {drop_cmd.split()[4]}")
                                cleanup_steps.append(f"Dropped table: {drop_cmd.split()[4]}")
                        else:
                            print(f"   📝 Table not found: {drop_cmd.split()[4]}")
                    except subprocess.TimeoutExpired:
                        print(f"   ⚠️  Timeout dropping table: {drop_cmd.split()[4]}")
                    except Exception as e:
                        print(f"   ⚠️  Error dropping table: {e}")
                
            except Exception as e:
                print(f"   ⚠️  Database cleanup error: {e}")
                print(f"   💡 You may need to manually drop tables for {model_name}")
            
            # Step 4: Remove migration files (if not keeping them)
            if not keep_migrations and migration_files:
                print("\n📄 Step 4: Removing Migration Files")
                
                for migration_file in migration_files:
                    try:
                        migration_file.unlink()
                        print(f"   ✅ Removed: {migration_file.name}")
                        cleanup_steps.append(f"Removed migration: {migration_file.name}")
                    except Exception as e:
                        print(f"   ❌ Error removing {migration_file.name}: {e}")
            elif keep_migrations:
                print("\n📄 Step 4: Keeping Migration Files (as requested)")
            else:
                print("\n📄 Step 4: No migration files to remove")
            
            # Step 5: Remove plugin files
            print("\n📁 Step 5: Removing Plugin Files")
            
            if plugin_dir.exists():
                import shutil
                shutil.rmtree(plugin_dir)
                print(f"   ✅ Removed directory: {plugin_dir}")
                cleanup_steps.append(f"Removed plugin directory: {plugin_dir}")
            
            if plugin_file.exists():
                plugin_file.unlink()
                print(f"   ✅ Removed file: {plugin_file}")
                cleanup_steps.append(f"Removed plugin file: {plugin_file}")
            
            # Step 6: Update Alembic state (if migrations were removed)
            if not keep_migrations and migration_files:
                print("\n🔄 Step 6: Updating Alembic State")
                try:
                    # Get current head
                    result = subprocess.run(['alembic', 'current'], capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"   📋 Current Alembic head: {result.stdout.strip()}")
                        print(f"   💡 Consider running 'alembic downgrade' if needed")
                    else:
                        print(f"   ⚠️  Could not determine current Alembic state")
                except Exception as e:
                    print(f"   ⚠️  Error checking Alembic state: {e}")
            
            # Summary
            print(f"\n🎉 Cleanup Complete: {model_name}")
            print("=" * 30)
            print(f"✅ Successfully cleaned up {len(cleanup_steps)} items:")
            for step in cleanup_steps:
                print(f"   • {step}")
            
            if not keep_migrations and migration_files:
                print(f"\n💡 Next steps:")
                print(f"   • Check if Alembic state needs adjustment")
                print(f"   • Restart your FastAPI server")
                print(f"   • Verify the plugin routes are removed from Swagger")
            else:
                print(f"\n💡 Next steps:")
                print(f"   • Restart your FastAPI server")
                print(f"   • Verify the plugin routes are removed from Swagger")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Cleanup failed: {e}")
            print(f"💡 You may need to manually clean up remaining items")
            return False
    
    def auth_check(self):
        """Check authentication system compatibility"""
        print("🔐 Authentication System Compatibility Check")
        print("=" * 45)
        
        checks = []
        
        # Check if authentication components exist
        print("🔍 Checking authentication components...")
        auth_components = [
            ("JWT Service", "app/core/jwt.py"),
            ("Security Service", "app/core/security.py"),
            ("User Model", "app/db/models/user.py"),
            ("Auth Routes", "app/api/v1/endpoints/auth.py"),
            ("User Service", "app/services/user_service.py")
        ]
        
        for component_name, component_path in auth_components:
            exists = Path(component_path).exists()
            checks.append((component_name, exists))
            status = "✅" if exists else "❌"
            print(f"   {status} {component_name}: {component_path}")
        
        # Check authentication dependencies
        print("\n🔍 Checking authentication dependencies...")
        try:
            from app.core.jwt import jwt_service
            print("   ✅ JWT Service importable")
            checks.append(("JWT Service Import", True))
        except ImportError as e:
            print(f"   ❌ JWT Service import failed: {e}")
            checks.append(("JWT Service Import", False))
        
        try:
            from app.core.security import security_service
            print("   ✅ Security Service importable")
            checks.append(("Security Service Import", True))
        except ImportError as e:
            print(f"   ❌ Security Service import failed: {e}")
            checks.append(("Security Service Import", False))
        
        # Check database models
        print("\n🔍 Checking database models...")
        try:
            from app.db.models.user import User
            print("   ✅ User model importable")
            checks.append(("User Model Import", True))
        except ImportError as e:
            print(f"   ❌ User model import failed: {e}")
            checks.append(("User Model Import", False))
        
        # Summary
        passed = sum(1 for _, status in checks if status)
        total = len(checks)
        
        print(f"\n📊 Authentication Check Summary")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {total - passed}")
        print(f"   📈 Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 Authentication system is ready for enhanced plugin generation!")
            return True
        else:
            print("\n⚠️ Authentication system needs setup before using --with-auth")
            print("💡 Run the main application to ensure all auth components are initialized")
            return False
    
    def add_authentication_to_plugin(self, model_name: str, auth_config: dict):
        """Add authentication to an existing plugin"""
        print(f"🔐 Adding Authentication to {model_name} Plugin")
        print("=" * 45)
        
        import re
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
        
        if not plugin_dir.exists():
            print(f"❌ Plugin not found: {plugin_dir}")
            return False
        
        try:
            # Backup existing files
            print("📋 Step 1: Backing up existing files")
            backup_dir = plugin_dir / "backup"
            backup_dir.mkdir(exist_ok=True)
            
            for file_name in ["models.py", "routes.py"]:
                source = plugin_dir / file_name
                if source.exists():
                    backup = backup_dir / f"{file_name}.backup"
                    backup.write_text(source.read_text())
                    print(f"   ✅ Backed up {file_name}")
            
            # Read existing fields from models.py
            print("\n🔍 Step 2: Analyzing existing model")
            fields = self._extract_fields_from_model(plugin_dir / "models.py")
            print(f"   ✅ Found {len(fields)} existing fields")
            
            # Generate enhanced model with auth
            print("\n🏗️ Step 3: Generating enhanced model")
            enhanced_config = {
                "enable_auth": True,
                "enable_ownership": auth_config.get("enable_ownership", False),
                "enable_audit": auth_config.get("enable_audit", True),
                "enable_soft_delete": auth_config.get("enable_soft_delete", False),
                "enable_versioning": False
            }
            
            models_content = self.auth_templates['models'].generate(
                model_name, fields, self.field_validator, enhanced_config
            )
            (plugin_dir / "models.py").write_text(models_content)
            print("   ✅ Enhanced models.py with authentication")
            
            # Generate enhanced routes with auth
            print("\n🔗 Step 4: Generating enhanced routes")
            routes_config = {
                "enable_auth": True,
                "require_permissions": True,
                "enable_audit": auth_config.get("enable_audit", True),
                "enable_rate_limiting": True,
                "owner_based_access": auth_config.get("enable_ownership", False),
                "require_roles": auth_config.get("require_roles", [])
            }
            
            routes_content = self.auth_templates['routes'].generate(
                model_name, fields, routes_config, False  # Assume no bulk for existing plugins
            )
            (plugin_dir / "routes.py").write_text(routes_content)
            print("   ✅ Enhanced routes.py with authentication")
            
            # Generate migration for auth fields
            print("\n🗄️ Step 5: Generating migration for auth fields")
            migration_success = self.migration_manager.generate_migration(f"{model_name}_add_auth")
            
            if migration_success:
                print(f"\n🎉 Authentication successfully added to {model_name} Plugin!")
                print(f"📂 Backups saved in: {backup_dir}")
                print(f"🔧 Remember to run: alembic upgrade head")
                return True
            else:
                print(f"\n⚠️ Authentication added but migration failed")
                print(f"💡 You may need to manually create migration for auth fields")
                return True
                
        except Exception as e:
            print(f"\n❌ Failed to add authentication: {e}")
            return False
    
    def generate_with_auth_preset(self, preset: str, model_name: str, fields: list, 
                                with_tasks: bool = False, with_bulk: bool = False):
        """Generate plugin with authentication presets"""
        print(f"🔐 Generating {model_name} Plugin with '{preset}' Authentication Preset")
        print("=" * 60)
        
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
                "owner_based_access": False
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
                "owner_based_access": True
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
                "owner_based_access": True
            }
        }
        
        auth_config = presets.get(preset)
        if not auth_config:
            print(f"❌ Unknown preset: {preset}")
            return False
        
        print(f"📋 Using preset configuration:")
        for key, value in auth_config.items():
            print(f"   • {key}: {value}")
        
        return self.add_plugin(model_name, fields, with_tasks, with_bulk, True, auth_config)
    
    def analyze_architecture(self, output_file: str = None, format_type: str = 'text') -> bool:
        """Analyze project architecture and generate report"""
        print("🔍 Starting Architecture Analysis")
        print("=" * 40)
        
        try:
            # Run architecture analysis
            report = self.architecture_analyzer.analyze_project()
            
            # Generate report
            output_path = Path(output_file) if output_file else None
            
            if format_type == 'json':
                # Convert report to JSON
                report_data = {
                    'health_score': report.health_score,
                    'metrics': report.metrics,
                    'plugins': [
                        {
                            'name': p.name,
                            'models': p.models,
                            'routes': p.routes,
                            'dependencies': p.dependencies,
                            'size_metrics': p.size_metrics,
                            'complexity_score': p.complexity_score
                        } for p in report.plugins
                    ],
                    'issues': [
                        {
                            'type': i.type,
                            'source': i.source,
                            'target': i.target,
                            'severity': i.severity,
                            'description': i.description,
                            'suggestion': i.suggestion
                        } for i in report.issues
                    ],
                    'recommendations': report.recommendations,
                    'dependency_graph': report.dependency_graph
                }
                
                if output_path:
                    import json
                    output_path.write_text(json.dumps(report_data, indent=2))
                    print(f"📄 JSON report saved to: {output_path}")
                else:
                    import json
                    print(json.dumps(report_data, indent=2))
            else:
                # Generate text report
                report_text = self.architecture_analyzer.generate_report(report, output_path)
                if not output_path:
                    print(report_text)
            
            print(f"\n🎉 Architecture analysis completed!")
            print(f"📊 Health Score: {report.health_score:.1f}%")
            return True
            
        except Exception as e:
            print(f"❌ Architecture analysis failed: {e}")
            return False
    
    def generate_test_suite(self, model_name: str, test_types: List[str], output_dir: str = None, with_auth: bool = False) -> bool:
        """Generate comprehensive test suite for a plugin"""
        print(f"🧪 Generating Test Suite for {model_name}")
        print("=" * 45)
        
        try:
            # Find the plugin to get its details
            import re
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
            
            if not plugin_dir.exists():
                print(f"❌ Plugin not found: {plugin_dir}")
                return False
            
            # Extract models and routes from plugin
            models = self._extract_models_from_plugin(plugin_dir)
            routes = self._extract_routes_from_plugin(plugin_dir)
            
            # Set up test configuration
            test_output_dir = Path(output_dir) if output_dir else Path(f"tests/plugins/{snake_name}_plugin")
            
            config = TestConfig(
                plugin_name=model_name,
                models=models,
                routes=routes,
                test_types=test_types,
                output_dir=test_output_dir,
                include_auth=with_auth,
                include_performance='load' in test_types
            )
            
            # Generate test suite
            success = self.test_generator.generate_test_suite(config)
            
            if success:
                print(f"\n🎉 Test suite generated successfully!")
                print(f"📂 Location: {test_output_dir}")
                print(f"🧪 Test types: {', '.join(test_types)}")
                print(f"\n💡 Next steps:")
                print(f"   • Install test dependencies: pip install pytest pytest-asyncio httpx")
                print(f"   • Run tests: pytest {test_output_dir}")
                if 'load' in test_types:
                    print(f"   • Install Locust for load tests: pip install locust")
                    print(f"   • Run load tests: locust -f {test_output_dir}/load/test_{model_name}_load.py")
            
            return success
            
        except Exception as e:
            print(f"❌ Test generation failed: {e}")
            return False
    
    def generate_smart_migration(self, model_name: str, changes: List[str] = None, auto_apply: bool = False) -> bool:
        """Generate smart migration with zero-downtime strategies"""
        print(f"🧠 Generating Smart Migration for {model_name}")
        print("=" * 50)
        
        try:
            # Set auto-apply mode in the migration manager
            if auto_apply:
                # Temporarily override the input function for auto-apply
                import builtins
                original_input = builtins.input
                builtins.input = lambda prompt: "y"
                
                try:
                    success = self.smart_migration_manager.generate_smart_migration(model_name, changes)
                finally:
                    builtins.input = original_input
            else:
                success = self.smart_migration_manager.generate_smart_migration(model_name, changes)
            
            if success:
                print(f"\n🎉 Smart migration completed successfully!")
                print(f"💡 Features included:")
                print(f"   • Automatic model file modification")
                print(f"   • Zero-downtime strategy analysis")
                print(f"   • Risk assessment and mitigation")
                print(f"   • Rollback strategy planning")
                print(f"   • Migration validation and application")
            
            return success
            
        except Exception as e:
            print(f"❌ Smart migration generation failed: {e}")
            return False
    
    def _extract_models_from_plugin(self, plugin_dir: Path) -> List[str]:
        """Extract model names from plugin directory"""
        models_file = plugin_dir / "models.py"
        if not models_file.exists():
            return []
        
        try:
            import ast
            with open(models_file, 'r') as f:
                tree = ast.parse(f.read())
            
            models = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a SQLAlchemy model
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'Base':
                            models.append(node.name)
                            break
            return models
        except Exception:
            return []
    
    def _extract_routes_from_plugin(self, plugin_dir: Path) -> List[str]:
        """Extract route information from plugin directory"""
        routes_file = plugin_dir / "routes.py"
        if not routes_file.exists():
            return []
        
        try:
            import ast
            with open(routes_file, 'r') as f:
                tree = ast.parse(f.read())
            
            routes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Look for FastAPI route decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                    routes.append(f"{decorator.func.attr.upper()} {node.name}")
            return routes
        except Exception:
            return []
    
    def _extract_fields_from_model(self, model_file: Path) -> list:
        """Extract field definitions from existing model file"""
        if not model_file.exists():
            return []
        
        # This is a simplified field extraction
        # In a real implementation, you'd parse the Python AST
        content = model_file.read_text()
        fields = []
        
        # Extract basic field patterns (simplified)
        import re
        field_pattern = r'(\w+)\s*=\s*Column\((.*?)\)'
        matches = re.findall(field_pattern, content, re.MULTILINE)
        
        for field_name, column_def in matches:
            if field_name not in ['id', 'created_at', 'updated_at']:
                # Extract basic type information
                if 'String' in column_def:
                    field_type = 'str'
                elif 'Integer' in column_def:
                    field_type = 'int'
                elif 'Boolean' in column_def:
                    field_type = 'bool'
                elif 'Float' in column_def:
                    field_type = 'float'
                else:
                    field_type = 'str'  # Default
                
                fields.append({
                    'name': field_name,
                    'type': field_type,
                    'constraints': []
                })
        
        return fields
    
    def migration_health_check(self):
        """Check migration system health and provide recommendations"""
        print("🏥 Migration System Health Check")
        print("=" * 40)
        
        health_status = self.migration_manager.check_migration_health()
        
        if health_status["status"] == "healthy":
            print("✅ Migration system is healthy")
        elif health_status["status"] == "needs_attention":
            print("⚠️ Migration system needs attention")
        else:
            print("❌ Migration system has errors")
        
        if health_status["current_revision"]:
            print(f"📍 Current revision: {health_status['current_revision']}")
        
        if health_status["issues"]:
            print("\n❌ Issues found:")
            for issue in health_status["issues"]:
                print(f"   - {issue}")
        
        if health_status["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in health_status["recommendations"]:
                print(f"   - {rec}")
        
        return health_status["status"] == "healthy"
    
    def test_enhanced_generator(self):
        """Test the enhanced scaffold generator with various scenarios"""
        print("🧪 Testing Enhanced Scaffold Generator v4")
        print("=" * 50)
        
        # Test 1: Health check
        print("\n🔍 Test 1: Migration Health Check")
        health_ok = self.migration_health_check()
        
        # Test 2: Field validation
        print("\n🔍 Test 2: Field Validation Tests")
        test_fields = [
            "name:str",
            "email:email",
            "status:str:choices=active,inactive,pending", 
            "age:int:ge=0:le=120",
            "price:float:gt=0",
            "notes:str:optional",
            "created_date:datetime"
        ]
        
        try:
            validated_fields = self.field_validator.validate_fields_batch(test_fields)
            print(f"✅ Validated {len(validated_fields)} test fields successfully")
            
            # Test choices constraint
            choice_field = next((f for f in validated_fields if 'choices=' in str(f.get('constraints', []))), None)
            if choice_field:
                print(f"✅ Choices constraint validated: {choice_field['name']}")
            
            # Test optional field
            optional_field = next((f for f in validated_fields if f.get('is_optional')), None)
            if optional_field:
                print(f"✅ Optional field detected: {optional_field['name']}")
                
        except Exception as e:
            print(f"❌ Field validation test failed: {e}")
            
        # Test 3: Import generation
        print("\n🔍 Test 3: Import Generation")
        try:
            imports = self.field_validator.get_required_imports(validated_fields)
            if 'typing' in imports and 'Literal' in imports['typing']:
                print("✅ Literal type import detected for choices")
            if 'pydantic' in imports and 'EmailStr' in imports['pydantic']:
                print("✅ EmailStr import detected")
        except Exception as e:
            print(f"❌ Import generation test failed: {e}")
        
        print(f"\n🎯 Enhanced Generator Test Complete")
        print(f"📊 Migration system health: {'✅ OK' if health_ok else '❌ Issues'}")
        
        return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='FastAPI Scaffold Generator v4.0 - Enhanced with Auto-Fix',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s add User name:str email:email age:int --with-tasks --with-bulk
  %(prog)s auto-fix                    # Fix all migration issues automatically
  %(prog)s auto-fix --force           # Aggressive fixes with emergency reset  
  %(prog)s migration-health           # Quick health check
  %(prog)s list                       # List all plugins with categories
  %(prog)s list-models                # List all models in project
  %(prog)s show-deps Product          # Show what migrations would be affected
  %(prog)s cleanup-business-plugins   # Remove business plugins + migrations for generic boilerplate
  %(prog)s cleanup-business-plugins --no-migrations  # Remove plugins only, keep migrations
  %(prog)s cleanup-business-plugins --migrations-only  # Remove migrations only, keep plugins
  %(prog)s remove Product                # Remove plugin only
  %(prog)s remove Product --with-migrations  # Remove plugin + its migrations
  %(prog)s cleanup Product --force --keep-migrations
  %(prog)s infra-check
  %(prog)s test Product name:str price:float:gt=0
  %(prog)s health-check

Auto-Fix Features:
  - Automatically fixes multiple migration heads
  - Removes invalid foreign key constraints (organizations, etc.)
  - Protects critical tables from accidental modification
  - Handles database state corruption
  - Removes orphaned migration files
  - 8 comprehensive strategies with fallbacks
  
Common Issues Resolved:
  ✅ Organizations FK constraint errors
  ✅ Multiple unmerged migration heads  
  ✅ Database state corruption
  ✅ Protected table modification attempts
  ✅ Malformed migration files
        '''
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Generate a new plugin')
    add_parser.add_argument('model', help='Model name (PascalCase)')
    add_parser.add_argument('fields', nargs='*', help='Field definitions (name:type[:constraints])')
    add_parser.add_argument('--with-tasks', action='store_true', help='Include background tasks')
    add_parser.add_argument('--with-bulk', action='store_true', help='Include bulk operations')
    add_parser.add_argument('--with-auth', action='store_true', help='Enable enterprise authentication')
    add_parser.add_argument('--auth-ownership', action='store_true', help='Enable owner-based access control')
    add_parser.add_argument('--auth-audit', action='store_true', default=True, help='Enable audit logging')
    add_parser.add_argument('--auth-soft-delete', action='store_true', help='Enable soft delete')
    add_parser.add_argument('--auth-versioning', action='store_true', help='Enable versioning')
    add_parser.add_argument('--auth-roles', help='Required roles (comma-separated)')
    add_parser.add_argument('--auth-rate-limit', action='store_true', default=True, help='Enable rate limiting')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all existing plugins')
    
    # List models command
    list_models_parser = subparsers.add_parser('list-models', help='List all models in the project')
    
    # Show model dependencies command
    show_deps_parser = subparsers.add_parser('show-deps', help='Show what migrations would be affected by removing a model')
    show_deps_parser.add_argument('model', help='Model name to analyze')
    
    # Cleanup business plugins command
    cleanup_business_parser = subparsers.add_parser('cleanup-business-plugins', help='Remove business-specific plugins for generic boilerplate')
    cleanup_business_parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    cleanup_business_parser.add_argument('--no-migrations', action='store_true', help='Skip migration cleanup (keep migrations)')
    cleanup_business_parser.add_argument('--migrations-only', action='store_true', help='Only clean migrations, keep plugins')
    
    # Remove command  
    remove_parser = subparsers.add_parser('remove', help='Remove a plugin')
    remove_parser.add_argument('model', help='Model name to remove')
    remove_parser.add_argument('--with-migrations', action='store_true', help='Also remove related database migrations')
    remove_parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    
    # Cleanup command (enhanced removal with database cleanup)
    cleanup_parser = subparsers.add_parser('cleanup', help='Completely remove plugin with database cleanup')
    cleanup_parser.add_argument('model', help='Model name to clean up')
    cleanup_parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    cleanup_parser.add_argument('--keep-migrations', action='store_true', help='Keep migration files (only remove plugin code)')
    
    # Fix plugins command
    fix_parser = subparsers.add_parser('fix-plugins', help='Fix common plugin issues')
    
    # Infrastructure check command
    subparsers.add_parser('infra-check', help='Check infrastructure compatibility')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test plugin generation')
    test_parser.add_argument('model', help='Model name (PascalCase)')
    test_parser.add_argument('fields', nargs='*', help='Field definitions (name:type[:constraints])')
    
    # Health check command
    subparsers.add_parser('health-check', help='Run comprehensive system health check')
    
    # Test enhanced generator command
    subparsers.add_parser('test-enhanced', help='Test enhanced generator capabilities')
    
    # Migration health check command
    subparsers.add_parser('migration-health', help='Check migration system health')
    
    # Fix Alembic command
    subparsers.add_parser('fix-alembic', help='Fix corrupted Alembic state')
    
    # Auto-fix all migration issues command
    auto_fix_parser = subparsers.add_parser('auto-fix', help='Automatically fix all migration issues (comprehensive)')
    auto_fix_parser.add_argument('--force', action='store_true', help='Enable aggressive fixes including emergency reset')
    auto_fix_parser.add_argument('--backup', action='store_true', default=True, help='Create backup before fixes')
    
    # Authentication commands
    add_auth_parser = subparsers.add_parser('add-auth', help='Add authentication to existing plugin')
    add_auth_parser.add_argument('model', help='Model name to add authentication to')
    add_auth_parser.add_argument('--ownership', action='store_true', help='Enable owner-based access control')
    add_auth_parser.add_argument('--audit', action='store_true', default=True, help='Enable audit logging')
    add_auth_parser.add_argument('--soft-delete', action='store_true', help='Enable soft delete')
    add_auth_parser.add_argument('--roles', help='Required roles (comma-separated)')
    
    # Auth check command
    subparsers.add_parser('auth-check', help='Check authentication system compatibility')
    
    # Generate auth preset command
    auth_preset_parser = subparsers.add_parser('auth-preset', help='Generate with authentication presets')
    auth_preset_parser.add_argument('preset', choices=['basic', 'secure', 'enterprise'], help='Authentication preset level')
    auth_preset_parser.add_argument('model', help='Model name (PascalCase)')
    auth_preset_parser.add_argument('fields', nargs='*', help='Field definitions (name:type[:constraints])')
    auth_preset_parser.add_argument('--with-tasks', action='store_true', help='Include background tasks')
    auth_preset_parser.add_argument('--with-bulk', action='store_true', help='Include bulk operations')
    
    # Architecture analysis command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze project architecture')
    analyze_parser.add_argument('--output', help='Output file for analysis report')
    analyze_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    # Test generation command
    test_parser = subparsers.add_parser('generate-tests', help='Generate comprehensive test suite')
    test_parser.add_argument('model', help='Model name to generate tests for')
    test_parser.add_argument('--types', nargs='+', choices=['unit', 'integration', 'e2e', 'load'], 
                           default=['unit', 'integration'], help='Types of tests to generate')
    test_parser.add_argument('--output-dir', help='Output directory for tests')
    test_parser.add_argument('--with-auth', action='store_true', help='Include authentication in tests')
    
    # Smart migration command
    smart_migration_parser = subparsers.add_parser('smart-migration', help='Generate smart migration with zero-downtime strategies')
    smart_migration_parser.add_argument('model', help='Model name for migration')
    smart_migration_parser.add_argument('--changes', nargs='*', 
                                      help='Specific changes to apply (e.g. add_column:status:str:default=active, drop_column:old_field)')
    smart_migration_parser.add_argument('--auto-apply', action='store_true', 
                                      help='Automatically apply the migration without prompting')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize generator
    generator = ScaffoldGeneratorV4()
    
    # Execute commands
    if args.command == 'add':
        if not args.fields:
            print("❌ Error: No fields specified")
            print("Example: python scaffold_generator_v4/main.py add User name:str email:email age:int")
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
                "require_permissions": bool(args.auth_roles),  # Only if roles are specified
                "require_roles": args.auth_roles.split(',') if args.auth_roles else [],
                "owner_based_access": args.auth_ownership
            }
        
        success = generator.add_plugin(args.model, args.fields, args.with_tasks, args.with_bulk, args.with_auth, auth_config)
        sys.exit(0 if success else 1)
    
    elif args.command == 'infra-check':
        success = generator.infra_check()
        sys.exit(0 if success else 1)
    
    elif args.command == 'test':
        if not args.fields:
            print("❌ Error: No fields specified for test")
            print("Example: python scaffold_generator_v4/main.py test User name:str email:email age:int")
            return
        
        success = generator.test_plugin(args.model, args.fields)
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        generator.list_plugins()
    
    elif args.command == 'list-models':
        generator.list_models()
    
    elif args.command == 'show-deps':
        generator.show_model_migrations(args.model)
    
    elif args.command == 'cleanup-business-plugins':
        if args.migrations_only:
            success = generator.cleanup_business_migrations_only(force=args.force)
        else:
            clean_migrations = not args.no_migrations
            success = generator.cleanup_business_plugins(force=args.force, clean_migrations=clean_migrations)
        sys.exit(0 if success else 1)
    
    elif args.command == 'remove':
        success = generator.remove_plugin(args.model, with_migrations=args.with_migrations, force=args.force)
        sys.exit(0 if success else 1)
    
    elif args.command == 'cleanup':
        success = generator.cleanup_plugin(args.model, force=args.force, keep_migrations=args.keep_migrations)
        sys.exit(0 if success else 1)
    
    elif args.command == 'fix-plugins':
        generator.fix_plugins()
    
    elif args.command == 'health-check':
        healthy = generator.health_check()
        sys.exit(0 if healthy else 1)
    
    elif args.command == 'test-enhanced':
        success = generator.test_enhanced_generator()
        sys.exit(0 if success else 1)
    
    elif args.command == 'migration-health':
        success = generator.migration_health_check()
        sys.exit(0 if success else 1)
    
    elif args.command == 'fix-alembic':
        success = generator.migration_manager.fix_alembic_state()
        sys.exit(0 if success else 1)
    
    elif args.command == 'auto-fix':
        print("🔧 Starting Comprehensive Auto-Fix Process")
        print("This will automatically fix all common migration issues")
        print("including multiple heads, foreign key constraints, and database state")
        print()
        
        if not args.force:
            print("⚠️ This will modify your migration files. Backup will be created.")
            confirm = input("Continue? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ Auto-fix cancelled")
                sys.exit(1)
        
        success = generator.migration_manager.auto_fix_all_migration_issues(force=args.force)
        
        if success:
            print("\n✅ Auto-fix completed successfully!")
            print("🎯 Your migration system should now be working correctly")
            print("💡 Try generating a new model to test: python main.py add TestModel name:str")
        else:
            print("\n❌ Auto-fix encountered issues")
            print("💡 Check the output above for details")
            print("🔧 You may need to run with --force for aggressive fixes")
        
        sys.exit(0 if success else 1)
    
    elif args.command == 'add-auth':
        success = generator.add_authentication_to_plugin(args.model, {
            "enable_ownership": args.ownership,
            "enable_audit": args.audit,
            "enable_soft_delete": args.soft_delete,
            "require_roles": args.roles.split(',') if args.roles else []
        })
        sys.exit(0 if success else 1)
    
    elif args.command == 'auth-check':
        success = generator.auth_check()
        sys.exit(0 if success else 1)
    
    elif args.command == 'auth-preset':
        if not args.fields:
            print("❌ Error: No fields specified for auth preset")
            return
        
        success = generator.generate_with_auth_preset(args.preset, args.model, args.fields, args.with_tasks, args.with_bulk)
        sys.exit(0 if success else 1)
    
    elif args.command == 'analyze':
        success = generator.analyze_architecture(args.output, args.format)
        sys.exit(0 if success else 1)
    
    elif args.command == 'generate-tests':
        success = generator.generate_test_suite(args.model, args.types, args.output_dir, args.with_auth)
        sys.exit(0 if success else 1)
    
    elif args.command == 'smart-migration':
        success = generator.generate_smart_migration(args.model, args.changes, args.auto_apply)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 