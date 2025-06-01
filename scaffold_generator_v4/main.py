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
"""

import argparse
import sys
from pathlib import Path

# Import modular components
from .core import FieldValidator, MigrationManager, InfrastructureChecker, PluginValidator
from .templates import (
    ModelsTemplate, SchemasTemplate, ServicesTemplate,
    RoutesTemplate, TasksTemplate, InitTemplate
)


class ScaffoldGeneratorV4:
    """Main scaffold generator orchestrator"""
    
    def __init__(self):
        # Initialize core components
        self.field_validator = FieldValidator()
        self.infrastructure_checker = InfrastructureChecker()
        self.migration_manager = MigrationManager(self.infrastructure_checker)
        self.plugin_validator = PluginValidator()
        
        # Initialize templates
        self.templates = {
            'models': ModelsTemplate(),
            'schemas': SchemasTemplate(),
            'services': ServicesTemplate(),
            'routes': RoutesTemplate(),
            'tasks': TasksTemplate(),
            'init': InitTemplate()
        }
    
    def add_plugin(self, model_name: str, fields: list, with_tasks: bool = False, with_bulk: bool = False):
        """Generate a new modular plugin"""
        print(f"🚀 Generating {model_name} Plugin with Modular Architecture")
        print("=" * 55)
        
        try:
            # 1. Validate infrastructure compatibility
            print("🔍 Step 1: Infrastructure Compatibility Check")
            if not self.infrastructure_checker.check_compatibility():
                print("❌ Infrastructure compatibility check failed")
                return False
            
            if not self.infrastructure_checker.validate_table_name_compatibility(model_name):
                return False
            
            # 2. Validate fields
            print("\n🔍 Step 2: Field Validation")
            validated_fields = self.field_validator.validate_fields_batch(fields)
            print(f"✅ Validated {len(validated_fields)} fields")
            
            # 3. Create plugin directory
            print(f"\n📁 Step 3: Creating Plugin Directory")
            plugin_dir = self._create_plugin_directory(model_name)
            print(f"✅ Created: {plugin_dir}")
            
            # 4. Generate modular files
            print(f"\n🏗️ Step 4: Generating Modular Files")
            self._generate_plugin_files(plugin_dir, model_name, validated_fields, with_tasks, with_bulk)
            
            # 5. Generate migration
            print(f"\n🗄️ Step 5: Database Migration")
            migration_success = self.migration_manager.generate_migration(model_name)
            
            if migration_success:
                print(f"\n🎉 {model_name} Plugin Generated Successfully!")
                print(f"📂 Location: {plugin_dir}")
                print(f"📋 Features: crud, search{', tasks' if with_tasks else ''}{', bulk' if with_bulk else ''}")
                print(f"🔗 Ready for integration with plugin system")
                return True
            else:
                print(f"\n⚠️ Plugin files created but migration failed")
                print(f"💡 You may need to manually fix migration issues")
                return False
                
        except Exception as e:
            print(f"\n❌ Plugin generation failed: {e}")
            return False
    
    def _create_plugin_directory(self, model_name: str) -> Path:
        """Create the plugin directory structure"""
        import re
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return plugin_dir
    
    def _generate_plugin_files(self, plugin_dir: Path, model_name: str, validated_fields: list, 
                             with_tasks: bool, with_bulk: bool):
        """Generate all modular plugin files"""
        
        # Generate models.py
        models_content = self.templates['models'].generate(model_name, validated_fields, self.field_validator)
        (plugin_dir / "models.py").write_text(models_content)
        print("  ✅ models.py")
        
        # Generate schemas.py
        schemas_content = self.templates['schemas'].generate(model_name, validated_fields, self.field_validator)
        (plugin_dir / "schemas.py").write_text(schemas_content)
        print("  ✅ schemas.py")
        
        # Generate services.py
        services_content = self.templates['services'].generate(model_name, validated_fields)
        (plugin_dir / "services.py").write_text(services_content)
        print("  ✅ services.py")
        
        # Generate routes.py
        routes_content = self.templates['routes'].generate(model_name, validated_fields, with_bulk)
        (plugin_dir / "routes.py").write_text(routes_content)
        print("  ✅ routes.py")
        
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
        """List all existing plugins"""
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
        
        # List v4 modular plugins
        for plugin_dir in plugin_dirs:
            plugin_name = plugin_dir.name.replace('_plugin', '').title()
            print(f"🔌 {plugin_name} (v4 - Modular)")
            print(f"   📁 Directory: {plugin_dir.name}")
            
            # Check files in directory
            files = list(plugin_dir.glob("*.py"))
            print(f"   📄 Files: {', '.join(f.name for f in files)}")
            
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
            
            print(f"🔌 {plugin_name} (v3 - Single File)")
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
    
    def remove_plugin(self, model_name: str) -> bool:
        """Remove a plugin (both v3 and v4 styles)"""
        try:
            import re
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            
            print(f"🗑️  Removing {model_name} Plugin")
            print("=" * 35)
            
            removed_items = []
            
            # Check for v4 modular plugin directory
            plugin_dir = Path(f"app/plugins/{snake_name}_plugin")
            if plugin_dir.exists() and plugin_dir.is_dir():
                # Remove directory and all files
                import shutil
                shutil.rmtree(plugin_dir)
                removed_items.append(f"Directory: {plugin_dir}")
                print(f"✅ Removed plugin directory: {plugin_dir}")
            
            # Check for v3 single plugin file
            plugin_file = Path(f"app/plugins/{snake_name}_plugin.py")
            if plugin_file.exists():
                plugin_file.unlink()
                removed_items.append(f"File: {plugin_file}")
                print(f"✅ Removed plugin file: {plugin_file}")
            
            if not removed_items:
                print(f"❌ Plugin not found: {model_name}")
                print(f"   Looked for: {snake_name}_plugin/ or {snake_name}_plugin.py")
                return False
            
            print(f"\n🎉 {model_name} plugin removed successfully!")
            print("⚠️  Note: Database migration not removed. Handle manually if needed.")
            
            return True
            
        except Exception as e:
            print(f"❌ Error removing plugin: {e}")
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
                from app.core.config import get_settings
                settings = get_settings()
                
                drop_commands = []
                for table_name in table_names:
                    drop_commands.append(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
                
                # Execute drop commands
                for drop_cmd in drop_commands:
                    try:
                        result = subprocess.run([
                            'psql', settings.database_url_without_async, 
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


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='FastAPI Scaffold Generator v4.0 - Modular Architecture',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s add User name:str email:email age:int --with-tasks --with-bulk
  %(prog)s list
  %(prog)s remove Product
  %(prog)s cleanup Product --force --keep-migrations
  %(prog)s infra-check
  %(prog)s test Product name:str price:float:gt=0
  %(prog)s health-check
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
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all existing plugins')
    
    # Remove command  
    remove_parser = subparsers.add_parser('remove', help='Remove a plugin')
    remove_parser.add_argument('model', help='Model name to remove')
    
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
        
        success = generator.add_plugin(args.model, args.fields, args.with_tasks, args.with_bulk)
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
    
    elif args.command == 'remove':
        success = generator.remove_plugin(args.model)
        sys.exit(0 if success else 1)
    
    elif args.command == 'cleanup':
        success = generator.cleanup_plugin(args.model, force=args.force, keep_migrations=args.keep_migrations)
        sys.exit(0 if success else 1)
    
    elif args.command == 'fix-plugins':
        generator.fix_plugins()
    
    elif args.command == 'health-check':
        healthy = generator.health_check()
        sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main() 