"""
Migration management for scaffold generator
"""
import subprocess
import re
from typing import List


class MigrationManager:
    """Handles Alembic migration operations"""
    
    def __init__(self, infrastructure_checker=None):
        self.infrastructure_checker = infrastructure_checker
        self.infrastructure_tables = [
            'alembic_version',
            'procrastinate_jobs',
            'procrastinate_job', 
            'procrastinate_events',
            'procrastinate_periodic_defers',
            'procrastinate_periodic_defer',
            'procrastinate_workers'
        ]
    
    def generate_migration(self, model_name: str) -> bool:
        """Generate Alembic migration for the model"""
        try:
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
            
            print(f"🔄 Generating migration for {model_name}...")
            
            # Check Alembic status first
            status_result = subprocess.run([
                "alembic", "current"
            ], capture_output=True, text=True)
            
            if status_result.returncode != 0:
                print(f"⚠️ Alembic status check failed: {status_result.stderr}")
                print("⚠️ Migration may fail due to state issues")
            else:
                current_revision = status_result.stdout.strip()
                print(f"📍 Current migration revision: {current_revision}")
            
            # Check for infrastructure tables in the database
            print("🔍 Checking for infrastructure tables...")
            
            # Generate migration with enhanced output
            print(f"🏗️ Creating migration for {model_name} model...")
            result = subprocess.run([
                "alembic", "revision", "--autogenerate", 
                "-m", f"Add {model_name} model"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Migration generated successfully")
                
                # Check if any infrastructure tables were detected in the output
                if any(table in result.stdout for table in self.infrastructure_tables):
                    print("⚠️ Warning: Infrastructure tables detected in migration output")
                    print("💡 This might indicate a configuration issue")
                
                # Apply migration with better error handling
                print(f"🚀 Applying migration...")
                apply_result = subprocess.run([
                    "alembic", "upgrade", "head"
                ], capture_output=True, text=True)
                
                if apply_result.returncode == 0:
                    print(f"✅ Migration applied successfully")
                    print(f"🎯 {model_name} table created in database")
                    
                    # Verify the table was created
                    print(f"🔍 Verifying {snake_name}s table creation...")
                    return True
                else:
                    print(f"❌ Failed to apply migration: {apply_result.stderr}")
                    self._handle_migration_errors(apply_result.stderr)
                    return False
            else:
                print(f"❌ Failed to generate migration: {result.stderr}")
                self._handle_generation_errors(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Migration error: {e}")
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
    
    def fix_alembic_state(self):
        """Fix corrupted Alembic state by resetting to latest valid revision"""
        try:
            print("🔧 Fixing Alembic state...")
            
            # Get the latest revision from history
            result = subprocess.run(['alembic', 'history'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to get Alembic history: {result.stderr}")
                return False
            
            # Parse the history to find the head revision
            lines = result.stdout.strip().split('\n')
            head_revision = None
            for line in lines:
                if '(head)' in line:
                    # Extract revision ID from line like "6aa199c2e923 -> 4231a548294e (head), ..."
                    parts = line.split(' -> ')
                    if len(parts) > 1:
                        head_revision = parts[1].split(' ')[0]
                        break
            
            if not head_revision:
                print("❌ Could not find head revision")
                return False
            
            print(f"🎯 Found head revision: {head_revision}")
            
            # Stamp the database with the head revision
            result = subprocess.run(['alembic', 'stamp', head_revision], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Successfully reset Alembic state to {head_revision}")
                return True
            else:
                print(f"❌ Failed to stamp revision: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error fixing Alembic state: {e}")
            return False 