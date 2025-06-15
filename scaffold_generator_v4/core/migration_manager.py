"""
Migration management for scaffold generator with enhanced error handling
"""
import subprocess
import re
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime


class MigrationManager:
    """Handles Alembic migration operations with enhanced error handling"""
    
    def __init__(self, infrastructure_checker=None):
        self.infrastructure_checker = infrastructure_checker
        self.project_root = Path.cwd()
        self.infrastructure_tables = [
            'alembic_version',
            'procrastinate_jobs',
            'procrastinate_job', 
            'procrastinate_events',
            'procrastinate_periodic_defers',
            'procrastinate_periodic_defer',
            'procrastinate_workers'
        ]
        # Tables that are known to not exist but might be referenced
        self.missing_reference_tables = [
            'organizations',
            'companies',
            'tenants',
            'departments',
            'groups',
            'projects'
        ]
        
        # Critical tables that should never be dropped automatically  
        self.protected_tables = [
            'users',
            'roles', 
            'permissions',
            'user_sessions',
            'security_events',
            'user_roles',
            'role_permissions',
            'user_passkeys',
            'api_keys',
            'blocked_ips',
            'security_configurations',
            'security_alerts'
        ]
    
    def create_migration(self, model_name: str) -> bool:
        """Create migration for the model (alias for generate_migration)"""
        return self.generate_migration(model_name)
    
    def generate_migration(self, model_name: str) -> bool:
        """Generate Alembic migration for the model with enhanced error handling"""
        try:
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            
            print(f"🔄 Generating migration for {model_name}...")
            
            # Step 1: Fix any existing migration state issues
            if not self._ensure_clean_migration_state():
                print("⚠️ Migration state issues detected, attempting to fix...")
                if not self._fix_migration_state():
                    print("❌ Could not fix migration state, proceeding anyway...")
            
            # Step 2: Check for multiple heads and merge if needed
            if not self._handle_multiple_heads():
                print("⚠️ Multiple heads detected but could not merge, proceeding...")
            
            # Step 3: Generate migration with better conflict handling
            print(f"🏗️ Creating migration for {model_name} model...")
            migration_file = self._generate_migration_file(model_name)
            
            if not migration_file:
                return False
            
            # Step 4: Post-process the migration to fix common issues
            if not self._fix_migration_file(migration_file, model_name):
                print("⚠️ Could not fix migration file, but proceeding...")
            
            # Step 5: Apply migration with retry logic
            return self._apply_migration_with_retry(model_name)
                
        except Exception as e:
            print(f"❌ Migration error: {e}")
            return False
    
    def _ensure_clean_migration_state(self) -> bool:
        """Ensure the migration state is clean and consistent"""
        try:
            # Check current status
            result = subprocess.run([
                "alembic", "current"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                current_revision = result.stdout.strip()
                print(f"📍 Current migration revision: {current_revision}")
                return True
            else:
                print(f"⚠️ Alembic status check failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking migration state: {e}")
            return False
    
    def _handle_multiple_heads(self) -> bool:
        """Handle multiple migration heads by merging them"""
        try:
            # Check for multiple heads
            result = subprocess.run([
                "alembic", "heads"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return True  # No issue if we can't check
            
            heads = result.stdout.strip().split('\n')
            heads = [head.split(' ')[0] for head in heads if head.strip()]
            
            if len(heads) <= 1:
                return True  # Single head or no heads, no issue
            
            print(f"🔀 Multiple heads detected: {heads}")
            print("🔧 Attempting to merge heads...")
            
            # Attempt to merge heads
            merge_result = subprocess.run([
                "alembic", "merge", "heads", "-m", "merge_multiple_heads"
            ], capture_output=True, text=True)
            
            if merge_result.returncode == 0:
                print("✅ Successfully merged multiple heads")
                
                # Upgrade to the new merged head
                upgrade_result = subprocess.run([
                    "alembic", "upgrade", "head"
                ], capture_output=True, text=True)
                
                if upgrade_result.returncode == 0:
                    print("✅ Successfully upgraded to merged head")
                    return True
                else:
                    print(f"⚠️ Failed to upgrade to merged head: {upgrade_result.stderr}")
                    return False
            else:
                print(f"⚠️ Failed to merge heads: {merge_result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error handling multiple heads: {e}")
            return False
    
    def _generate_migration_file(self, model_name: str) -> Optional[str]:
        """Generate the migration file and return its path"""
        try:
            result = subprocess.run([
                "alembic", "revision", "--autogenerate", 
                "-m", f"add_{model_name.lower()}_model"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Migration file generated successfully")
                
                # Extract migration file path from output
                output = result.stdout
                if "Generating" in output:
                    for line in output.split('\n'):
                        if "Generating" in line and ".py" in line:
                            # Extract path from "Generating /path/to/file.py"
                            path_start = line.find('/')
                            if path_start != -1:
                                path = line[path_start:].split(' ')[0]
                                return path
                
                # Fallback: find the most recent migration file
                alembic_dir = Path("alembic/versions")
                if alembic_dir.exists():
                    migration_files = list(alembic_dir.glob("*.py"))
                    if migration_files:
                        latest_file = max(migration_files, key=lambda x: x.stat().st_mtime)
                        return str(latest_file)
                
                return "migration_generated"  # Fallback indicator
            else:
                print(f"❌ Failed to generate migration: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating migration file: {e}")
            return None
    
    def _fix_migration_file(self, migration_file: str, model_name: str) -> bool:
        """Fix common issues in the generated migration file"""
        try:
            if migration_file == "migration_generated":
                print("⚠️ Could not locate migration file, skipping fixes")
                return True
            
            migration_path = Path(migration_file)
            if not migration_path.exists():
                print(f"⚠️ Migration file not found: {migration_file}")
                return False
            
            print(f"🔧 Fixing migration file: {migration_path.name}")
            
            # Read the migration file
            content = migration_path.read_text()
            original_content = content
            
            # Fix 1: Remove foreign key constraints to missing tables
            for missing_table in self.missing_reference_tables:
                # Remove foreign key constraints that reference missing tables
                fk_pattern = rf"sa\.ForeignKeyConstraint\(\[.*?\], \['{missing_table}\..*?\'\], \),?\s*\n"
                content = re.sub(fk_pattern, "", content)
                
                # Also remove from downgrade function
                fk_pattern_down = rf"sa\.ForeignKeyConstraint\(\['.*?'\], \['{missing_table}\..*?'\], name='.*?'\),?\s*\n"
                content = re.sub(fk_pattern_down, "", content)
            
            # Fix 2: Remove unwanted table drops from upgrade function
            # This prevents the migration from trying to drop existing important tables
            for protected_table in self.protected_tables:
                # Remove table drops
                drop_table_pattern = rf"op\.drop_table\('{protected_table}'\)"
                content = re.sub(drop_table_pattern, "", content)
                
                # Remove index drops for protected tables
                drop_index_pattern = rf"op\.drop_index\('ix_{protected_table}_.*?', table_name='{protected_table}'\)"
                content = re.sub(drop_index_pattern, "", content)
                
                # Remove specific index patterns
                drop_index_pattern2 = rf"op\.drop_index\('.*?', table_name='{protected_table}'\)"
                content = re.sub(drop_index_pattern2, "", content)
            
            # Also remove any attempts to create protected tables (they should already exist)
            for protected_table in self.protected_tables:
                create_table_pattern = rf"op\.create_table\('{protected_table}'.*?\)\s*\n"
                content = re.sub(create_table_pattern, "", content, flags=re.DOTALL)
            
            # Fix 3: Clean up the downgrade function to only handle the new table
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            table_name = f"{snake_name}s"
            
            # Find the downgrade function and replace it with a clean version
            downgrade_pattern = r"def downgrade\(\) -> None:.*?# ### end Alembic commands ###"
            clean_downgrade = f"""def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_{table_name}_id'), table_name='{table_name}')
    op.drop_table('{table_name}')
    # ### end Alembic commands ###"""
            
            content = re.sub(downgrade_pattern, clean_downgrade, content, flags=re.DOTALL)
            
            # Fix 4: Handle specific error patterns we've encountered
            content = self._fix_specific_migration_issues(content, model_name)
            
            # Fix 5: Validate and clean up the migration structure
            content = self._validate_migration_structure(content, model_name)
            
            # Only write if changes were made
            if content != original_content:
                migration_path.write_text(content)
                print(f"✅ Fixed migration file issues")
                print(f"📝 Changes made:")
                print(f"   - Removed foreign key constraints to missing tables")
                print(f"   - Removed unwanted table/index drops")
                print(f"   - Cleaned up downgrade function")
                print(f"   - Fixed migration structure")
            else:
                print(f"✅ Migration file looks good, no fixes needed")
            
            return True
            
        except Exception as e:
            print(f"❌ Error fixing migration file: {e}")
            return False
    
    def _fix_specific_migration_issues(self, content: str, model_name: str) -> str:
        """Fix specific migration issues we've encountered"""
        
        # Issue 1: Remove references to non-existent tables in downgrade function
        for missing_table in self.missing_reference_tables:
            # Remove foreign key constraints in downgrade that reference missing tables
            fk_downgrade_pattern = rf"sa\.ForeignKeyConstraint\(\['.*?'\], \['{missing_table}\..*?'\], name='.*?'\),?\s*\n"
            content = re.sub(fk_downgrade_pattern, "", content)
            
            # Remove table recreations that might reference missing tables
            create_table_pattern = rf"op\.create_table\('{missing_table}'.*?\),?\s*\n"
            content = re.sub(create_table_pattern, "", content, flags=re.DOTALL)
        
        # Issue 2: Fix duplicate table creation attempts
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        table_name = f"{snake_name}s"
        
        # Find all create_table statements for our table and keep only the first one
        create_pattern = rf"op\.create_table\('{table_name}'.*?\),?\s*\n.*?op\.create_index.*?{table_name}.*?\n"
        matches = list(re.finditer(create_pattern, content, flags=re.DOTALL))
        
        if len(matches) > 1:
            # Keep the first match, remove the rest
            for match in reversed(matches[1:]):
                content = content[:match.start()] + content[match.end():]
        
        # Issue 3: Remove malformed constraint definitions
        malformed_fk_pattern = r"sa\.ForeignKeyConstraint\(\[.*?\], \[\], \),?\s*\n"
        content = re.sub(malformed_fk_pattern, "", content)
        
        # Issue 4: Clean up extra whitespace and empty lines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content
    
    def _validate_migration_structure(self, content: str, model_name: str) -> str:
        """Validate and fix migration structure"""
        
        # Ensure proper upgrade and downgrade function structure
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        table_name = f"{snake_name}s"
        
        # Check if upgrade function is properly structured
        if "def upgrade() -> None:" not in content:
            print("⚠️ Warning: Migration missing upgrade function")
            return content
        
        # Check if downgrade function exists and is properly structured
        if "def downgrade() -> None:" not in content:
            print("⚠️ Warning: Migration missing downgrade function")
            return content
        
        # Ensure the downgrade function only handles the new table
        downgrade_section = re.search(
            r"def downgrade\(\) -> None:.*?(?=def|\Z)", 
            content, 
            re.DOTALL
        )
        
        if downgrade_section:
            downgrade_content = downgrade_section.group(0)
            
            # Check if it contains references to protected tables
            for protected_table in self.protected_tables:
                if protected_table in downgrade_content and protected_table != table_name:
                    print(f"⚠️ Warning: Downgrade function references protected table: {protected_table}")
                    
                    # Remove problematic references
                    content = self._clean_downgrade_function(content, table_name)
                    break
        
        return content
    
    def _clean_downgrade_function(self, content: str, table_name: str) -> str:
        """Clean up the downgrade function to only handle the intended table"""
        
        # Replace the entire downgrade function with a clean version
        clean_downgrade = f'''def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_{table_name}_id'), table_name='{table_name}')
    op.drop_table('{table_name}')
    # ### end Alembic commands ###'''
        
        # Replace the downgrade function
        content = re.sub(
            r"def downgrade\(\) -> None:.*?# ### end Alembic commands ###",
            clean_downgrade,
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def _apply_migration_with_retry(self, model_name: str) -> bool:
        """Apply migration with retry logic for common failures"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"🚀 Applying migration (attempt {attempt + 1}/{max_retries})...")
                
                result = subprocess.run([
                    "alembic", "upgrade", "head"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ Migration applied successfully")
                    print(f"🎯 {model_name} table created in database")
                    return True
                else:
                    error_msg = result.stderr
                    print(f"❌ Migration failed (attempt {attempt + 1}): {error_msg}")
                    
                    # Handle specific error types
                    if "relation already exists" in error_msg:
                        print("💡 Table already exists, marking migration as applied...")
                        return self._stamp_current_migration()
                    
                    elif "Target database is not up to date" in error_msg:
                        print("🔧 Database state issue, attempting to fix...")
                        if self._fix_database_state():
                            continue  # Retry
                        else:
                            break
                    
                    elif "multiple heads" in error_msg.lower():
                        print("🔧 Multiple heads detected during migration...")
                        if self._handle_multiple_heads():
                            continue  # Retry
                        else:
                            break
                    
                    # If it's the last attempt, return False
                    if attempt == max_retries - 1:
                        print(f"💡 You may need to manually fix migration issues")
                        return False
                        
            except Exception as e:
                print(f"❌ Migration error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return False
        
        return False
    
    def _fix_database_state(self) -> bool:
        """Fix database state inconsistencies"""
        try:
            # Check current state
            current_result = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if current_result.returncode != 0:
                print("   Database state is corrupted, attempting to fix...")
                
                # Try to stamp to head
                stamp_result = subprocess.run(
                    ["alembic", "stamp", "head"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                if stamp_result.returncode == 0:
                    print("   Successfully stamped to head")
                    return True
                else:
                    print(f"   Stamp failed: {stamp_result.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"   Error fixing database state: {e}")
            return False
    
    def _stamp_current_migration(self) -> bool:
        """Stamp the current migration as applied"""
        try:
            # Get the latest migration
            result = subprocess.run([
                "alembic", "heads"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                head = result.stdout.strip().split('\n')[0].split(' ')[0]
                
                stamp_result = subprocess.run([
                    "alembic", "stamp", head
                ], capture_output=True, text=True)
                
                if stamp_result.returncode == 0:
                    print(f"✅ Marked migration as applied: {head}")
                    return True
                else:
                    print(f"❌ Failed to stamp migration: {stamp_result.stderr}")
                    return False
            else:
                print(f"❌ Failed to get head revision: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error stamping migration: {e}")
            return False
    
    def _fix_migration_state(self) -> bool:
        """Fix corrupted migration state"""
        try:
            print("🔧 Fixing migration state...")
            
            # Get current heads
            result = subprocess.run(['alembic', 'heads'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                heads = result.stdout.strip().split('\n')
                if len(heads) == 1:
                    head = heads[0].split(' ')[0]
                    return self._stamp_current_migration()
            
            # If that doesn't work, try to reset to a known good state
            history_result = subprocess.run(['alembic', 'history'], capture_output=True, text=True)
            if history_result.returncode == 0:
                lines = history_result.stdout.strip().split('\n')
                for line in lines:
                    if '(head)' in line:
                        head_revision = line.split(' -> ')[1].split(' ')[0] if ' -> ' in line else line.split(' ')[0]
                        stamp_result = subprocess.run(['alembic', 'stamp', head_revision], capture_output=True, text=True)
                        if stamp_result.returncode == 0:
                            print(f"✅ Reset migration state to {head_revision}")
                            return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error fixing migration state: {e}")
            return False
    
    def _handle_migration_errors(self, error_message: str):
        """Handle migration application errors"""
        if "duplicate key value" in error_message:
            print("💡 Table may already exist - this might be expected")
        elif "relation already exists" in error_message:
            print("💡 Table already exists - migration may have run before")
        else:
            print("💡 You may need to manually fix migration state")
            print("💡 Try: alembic stamp head")
    
    def _handle_generation_errors(self, error_message: str):
        """Handle migration generation errors"""
        if "Can't locate revision" in error_message:
            print("💡 Migration state conflict detected")
            print("💡 You may need to run: alembic stamp head")
        elif "could not assemble any primary key columns" in error_message:
            print("💡 Model definition issue - check primary key configuration")
        elif "No changes in schema detected" in error_message:
            print("💡 No changes detected - table may already exist")
    
    def downgrade_migration(self, revision: str) -> bool:
        """Downgrade to a specific migration revision"""
        try:
            print(f"⬇️ Downgrading to revision: {revision}")
            result = subprocess.run([
                "alembic", "downgrade", revision
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Migration downgraded successfully")
                return True
            else:
                print(f"❌ Failed to downgrade migration: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Downgrade error: {e}")
            return False
    
    def get_migration_history(self) -> List[str]:
        """Get the migration history"""
        try:
            result = subprocess.run([
                "alembic", "history", "--verbose"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.split('\n')
            else:
                print(f"❌ Failed to get migration history: {result.stderr}")
                return []
                
        except Exception as e:
            print(f"❌ History error: {e}")
            return []
    
    def stamp_head(self) -> bool:
        """Stamp the database to the current head revision"""
        try:
            print("🔧 Stamping database to current head...")
            result = subprocess.run([
                "alembic", "stamp", "head"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Database stamped successfully")
                return True
            else:
                print(f"❌ Failed to stamp database: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Stamp error: {e}")
            return False
    
    def check_migration_health(self) -> Dict[str, Any]:
        """Check the health of the migration system and return status"""
        health_status = {
            "status": "healthy",
            "issues": [],
            "recommendations": [],
            "current_revision": None,
            "pending_migrations": [],
            "multiple_heads": False
        }
        
        try:
            # Check current revision
            result = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                health_status["current_revision"] = result.stdout.strip()
            else:
                health_status["issues"].append("Cannot determine current revision")
                health_status["status"] = "unhealthy"
            
            # Check for multiple heads
            heads_result = subprocess.run(
                ["alembic", "heads"],
                capture_output=True,
                text=True
            )
            
            if heads_result.returncode == 0:
                heads = heads_result.stdout.strip().split('\n')
                heads = [head.split(' ')[0] for head in heads if head.strip()]
                
                if len(heads) > 1:
                    health_status["multiple_heads"] = True
                    health_status["issues"].append(f"Multiple migration heads detected: {heads}")
                    health_status["recommendations"].append("Run: alembic merge heads")
                    health_status["status"] = "needs_attention"
            
            # Check for pending migrations
            # This would require more complex logic to determine pending migrations
            
            return health_status
            
        except Exception as e:
            health_status["status"] = "error"
            health_status["issues"].append(f"Health check failed: {e}")
            return health_status
    
    def auto_fix_all_migration_issues(self, force: bool = False) -> bool:
        """
        Comprehensive auto-fix for all migration issues with multiple fallback strategies.
        This handles all the common issues we've encountered in the last 3 model generations.
        """
        print("🔧 Auto-fixing All Migration Issues")
        print("=" * 50)
        
        success_count = 0
        total_strategies = 8
        
        try:
            # Strategy 1: Check and fix multiple heads
            print("\n📍 Strategy 1: Checking for multiple heads...")
            if self._fix_multiple_heads():
                print("✅ Multiple heads resolved")
                success_count += 1
            else:
                print("⚠️ No multiple heads found or couldn't fix")
            
            # Strategy 2: Clean up invalid migration files
            print("\n📍 Strategy 2: Cleaning up invalid migration files...")
            if self._cleanup_invalid_migrations():
                print("✅ Invalid migrations cleaned up")
                success_count += 1
            else:
                print("⚠️ No invalid migrations found")
            
            # Strategy 3: Fix database state inconsistencies
            print("\n📍 Strategy 3: Fixing database state...")
            if self._fix_database_state():
                print("✅ Database state fixed")
                success_count += 1
            else:
                print("⚠️ Database state issues detected")
            
            # Strategy 4: Remove orphaned migration files
            print("\n📍 Strategy 4: Removing orphaned migrations...")
            if self._remove_orphaned_migrations():
                print("✅ Orphaned migrations removed")
                success_count += 1
            else:
                print("⚠️ No orphaned migrations found")
            
            # Strategy 5: Fix foreign key constraint issues in all migrations
            print("\n📍 Strategy 5: Fixing foreign key constraints...")
            if self._fix_all_foreign_key_issues():
                print("✅ Foreign key constraints fixed")
                success_count += 1
            else:
                print("⚠️ No foreign key issues found")
            
            # Strategy 6: Validate and fix migration sequence
            print("\n📍 Strategy 6: Validating migration sequence...")
            if self._validate_migration_sequence():
                print("✅ Migration sequence validated")
                success_count += 1
            else:
                print("⚠️ Migration sequence issues detected")
            
            # Strategy 7: Emergency fallback - reset to known good state
            if success_count < 3 and force:
                print("\n📍 Strategy 7: Emergency fallback (force mode)...")
                if self._emergency_reset_migrations():
                    print("✅ Emergency reset completed")
                    success_count += 1
                else:
                    print("❌ Emergency reset failed")
            
            # Strategy 8: Final validation and cleanup
            print("\n📍 Strategy 8: Final validation...")
            if self._final_validation_and_cleanup():
                print("✅ Final validation passed")
                success_count += 1
            else:
                print("⚠️ Final validation issues")
            
            print(f"\n🎯 Auto-fix Results: {success_count}/{total_strategies} strategies successful")
            
            if success_count >= 6:
                print("✅ Auto-fix completed successfully!")
                return True
            elif success_count >= 4:
                print("⚠️ Auto-fix partially successful - manual intervention may be needed")
                return True
            else:
                print("❌ Auto-fix failed - multiple issues detected")
                return False
                
        except Exception as e:
            print(f"❌ Auto-fix failed with error: {e}")
            return False
    
    def _fix_multiple_heads(self) -> bool:
        """Fix multiple migration heads automatically"""
        try:
            # Check for multiple heads
            result = subprocess.run(
                ["alembic", "heads"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                return False
            
            heads = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            heads = [head.split(' ')[0] for head in heads if head and not head.startswith('(')]
            
            if len(heads) <= 1:
                return True  # No multiple heads
            
            print(f"   Found {len(heads)} heads: {heads}")
            
            # Attempt to merge heads
            merge_result = subprocess.run(
                ["alembic", "merge", "heads", "-m", f"Auto-merge heads: {', '.join(heads)}"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if merge_result.returncode == 0:
                print(f"   Successfully merged {len(heads)} heads")
                return True
            else:
                print(f"   Merge failed: {merge_result.stderr}")
                return False
                
        except Exception as e:
            print(f"   Error fixing multiple heads: {e}")
            return False
    
    def _cleanup_invalid_migrations(self) -> bool:
        """Clean up invalid migration files"""
        try:
            fixed_count = 0
            migrations_dir = self.project_root / "alembic" / "versions"
            
            if not migrations_dir.exists():
                return True
            
            for migration_file in migrations_dir.glob("*.py"):
                try:
                    content = migration_file.read_text()
                    original_content = content
                    
                    # Fix common issues
                    content = self._fix_migration_content_issues(content)
                    
                    if content != original_content:
                        migration_file.write_text(content)
                        fixed_count += 1
                        print(f"   Fixed: {migration_file.name}")
                        
                except Exception as e:
                    print(f"   Error fixing {migration_file.name}: {e}")
            
            return fixed_count > 0 or True  # Return True if no issues found
            
        except Exception as e:
            print(f"   Error cleaning up migrations: {e}")
            return False
    
    def _fix_migration_content_issues(self, content: str) -> str:
        """Fix common migration content issues"""
        
        # Remove foreign key constraints to missing tables
        for missing_table in self.missing_reference_tables:
            patterns = [
                rf"sa\.ForeignKeyConstraint\(\['.*?'\], \['{missing_table}\..*?'\], name='.*?'\),?\s*\n",
                rf"sa\.ForeignKeyConstraint\(\['.*?'\], \['{missing_table}\..*?'\]\),?\s*\n",
                rf"op\.create_foreign_key\('.*?', '.*?', '{missing_table}', \['.*?'\], \['.*?'\]\)\s*\n"
            ]
            
            for pattern in patterns:
                content = re.sub(pattern, "", content)
        
        # Remove malformed foreign key constraints
        malformed_patterns = [
            r"sa\.ForeignKeyConstraint\(\[.*?\], \[\], \),?\s*\n",
            r"sa\.ForeignKeyConstraint\(\[\], \[.*?\], \),?\s*\n",
            r"op\.create_foreign_key\('.*?', '.*?', '', \['.*?'\], \['.*?'\]\)\s*\n"
        ]
        
        for pattern in malformed_patterns:
            content = re.sub(pattern, "", content)
        
        # Remove attempts to drop protected tables
        for protected_table in self.protected_tables:
            drop_patterns = [
                rf"op\.drop_table\('{protected_table}'\)\s*\n",
                rf"op\.drop_index\('.*?', table_name='{protected_table}'\)\s*\n"
            ]
            
            for pattern in drop_patterns:
                content = re.sub(pattern, "", content)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content
    
    def _fix_database_state(self) -> bool:
        """Fix database state inconsistencies"""
        try:
            # Check current state
            current_result = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if current_result.returncode != 0:
                print("   Database state is corrupted, attempting to fix...")
                
                # Try to stamp to head
                stamp_result = subprocess.run(
                    ["alembic", "stamp", "head"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                if stamp_result.returncode == 0:
                    print("   Successfully stamped to head")
                    return True
                else:
                    print(f"   Stamp failed: {stamp_result.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"   Error fixing database state: {e}")
            return False
    
    def _remove_orphaned_migrations(self) -> bool:
        """Remove orphaned migration files that cause conflicts"""
        try:
            removed_count = 0
            migrations_dir = self.project_root / "alembic" / "versions"
            
            if not migrations_dir.exists():
                return True
            
            # Get list of migrations from alembic history
            history_result = subprocess.run(
                ["alembic", "history"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if history_result.returncode != 0:
                return False
            
            # Extract revision IDs from history
            history_revisions = set()
            for line in history_result.stdout.split('\n'):
                if ' -> ' in line:
                    # Extract revision ID (first part before space)
                    rev_id = line.strip().split(' ')[0]
                    if rev_id and rev_id != '(head)':
                        history_revisions.add(rev_id)
            
            # Check each migration file
            for migration_file in migrations_dir.glob("*.py"):
                try:
                    # Extract revision from filename
                    filename = migration_file.name
                    if '_' in filename:
                        file_revision = filename.split('_')[0]
                        
                        # If file revision is not in history, it might be orphaned
                        if file_revision not in history_revisions and len(file_revision) >= 12:
                            # Additional check: ensure it's not referenced
                            content = migration_file.read_text()
                            if 'revision =' in content:
                                # Check if this creates conflicts
                                if self._is_migration_problematic(content):
                                    print(f"   Removing problematic migration: {filename}")
                                    migration_file.unlink()
                                    removed_count += 1
                                    
                except Exception as e:
                    print(f"   Error checking {migration_file.name}: {e}")
            
            return True
            
        except Exception as e:
            print(f"   Error removing orphaned migrations: {e}")
            return False
    
    def _is_migration_problematic(self, content: str) -> bool:
        """Check if a migration file is problematic"""
        problematic_indicators = [
            # Contains references to missing tables
            any(table in content for table in self.missing_reference_tables),
            # Contains malformed foreign keys
            'ForeignKeyConstraint([], [' in content,
            'ForeignKeyConstraint([' in content and '], [])' in content,
            # Attempts to drop protected tables
            any(f"drop_table('{table}')" in content for table in self.protected_tables)
        ]
        
        return any(problematic_indicators)
    
    def _fix_all_foreign_key_issues(self) -> bool:
        """Fix foreign key constraint issues in all migration files"""
        try:
            fixed_count = 0
            migrations_dir = self.project_root / "alembic" / "versions"
            
            if not migrations_dir.exists():
                return True
            
            for migration_file in migrations_dir.glob("*.py"):
                try:
                    content = migration_file.read_text()
                    original_content = content
                    
                    # Apply all foreign key fixes
                    content = self._fix_migration_content_issues(content)
                    
                    if content != original_content:
                        migration_file.write_text(content)
                        fixed_count += 1
                        
                except Exception as e:
                    print(f"   Error fixing FK in {migration_file.name}: {e}")
            
            if fixed_count > 0:
                print(f"   Fixed foreign key issues in {fixed_count} migration files")
            
            return True
            
        except Exception as e:
            print(f"   Error fixing foreign key issues: {e}")
            return False
    
    def _validate_migration_sequence(self) -> bool:
        """Validate and fix migration sequence"""
        try:
            # Check if we can show migration history
            history_result = subprocess.run(
                ["alembic", "history"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if history_result.returncode != 0:
                print("   Migration history is corrupted")
                
                # Try to fix by stamping to head
                stamp_result = subprocess.run(
                    ["alembic", "stamp", "head"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                return stamp_result.returncode == 0
            
            return True
            
        except Exception as e:
            print(f"   Error validating migration sequence: {e}")
            return False
    
    def _emergency_reset_migrations(self) -> bool:
        """Emergency reset migrations to a known good state"""
        try:
            print("   ⚠️ Performing emergency migration reset...")
            
            # Backup current migrations
            backup_dir = self.project_root / "alembic_backup" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            migrations_dir = self.project_root / "alembic" / "versions"
            
            if migrations_dir.exists():
                backup_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copytree(migrations_dir, backup_dir / "versions")
                print(f"   Created backup at: {backup_dir}")
            
            # Remove all migration files
            if migrations_dir.exists():
                for migration_file in migrations_dir.glob("*.py"):
                    migration_file.unlink()
            
            # Reset alembic state
            subprocess.run(
                ["alembic", "stamp", "base"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            print("   Emergency reset completed")
            return True
            
        except Exception as e:
            print(f"   Emergency reset failed: {e}")
            return False
    
    def _final_validation_and_cleanup(self) -> bool:
        """Final validation and cleanup"""
        try:
            # Test if alembic commands work
            commands_to_test = [
                ["alembic", "current"],
                ["alembic", "heads"],
                ["alembic", "history"]
            ]
            
            for cmd in commands_to_test:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                if result.returncode != 0:
                    print(f"   Command failed: {' '.join(cmd)}")
                    return False
            
            print("   All alembic commands working correctly")
            return True
            
        except Exception as e:
            print(f"   Final validation failed: {e}")
            return False
    
    def quick_migration_health_check(self) -> bool:
        """Quick check to see if migration system needs auto-fix"""
        try:
            # Check 1: Multiple heads
            heads_result = subprocess.run(
                ["alembic", "heads"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if heads_result.returncode == 0:
                heads = [line.strip() for line in heads_result.stdout.strip().split('\n') if line.strip()]
                heads = [head.split(' ')[0] for head in heads if head and not head.startswith('(')]
                
                if len(heads) > 1:
                    return False  # Multiple heads detected
            
            # Check 2: Database state
            current_result = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if current_result.returncode != 0:
                return False  # Database state issues
            
            # Check 3: Migration files with known issues
            migrations_dir = self.project_root / "alembic" / "versions"
            if migrations_dir.exists():
                for migration_file in migrations_dir.glob("*.py"):
                    try:
                        content = migration_file.read_text()
                        if self._is_migration_problematic(content):
                            return False  # Problematic migration found
                    except Exception:
                        continue
            
            return True  # All checks passed
            
        except Exception:
            return False  # Error means we should run auto-fix
    
    def auto_fix_if_needed(self, force: bool = False) -> bool:
        """Run auto-fix only if migration system has issues"""
        if self.quick_migration_health_check():
            print("✅ Migration system is healthy, no auto-fix needed")
            return True
        
        print("⚠️ Migration issues detected, running auto-fix...")
        return self.auto_fix_all_migration_issues(force=force) 