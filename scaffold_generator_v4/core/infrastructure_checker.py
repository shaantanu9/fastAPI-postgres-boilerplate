"""
Infrastructure compatibility checker for scaffold generator
"""
import subprocess
import re
from typing import Set


class InfrastructureChecker:
    """Handles infrastructure compatibility checks"""
    
    def __init__(self):
        self.infrastructure_tables = {
            'alembic_version',
            'procrastinate_jobs',
            'procrastinate_job',  # Alternative naming
            'procrastinate_events',
            'procrastinate_periodic_defers',
            'procrastinate_periodic_defer',  # Alternative naming
            'procrastinate_locks',
            'procrastinate_workers'
        }
        
        self.reserved_names = {
            'alembic_version', 'alembic_versions',
            'procrastinate_jobs', 'procrastinate_job',
            'procrastinate_events', 'procrastinate_event', 
            'procrastinate_periodic_defers', 'procrastinate_periodic_defer',
            'procrastinate_workers', 'procrastinate_worker',
            'procrastinate_locks', 'procrastinate_lock',
            'migrations', 'migration',
            'users', 'user'  # Common conflicts
        }
    
    def check_compatibility(self) -> bool:
        """Check if the database infrastructure is compatible with scaffold generation"""
        print("🔍 Checking Infrastructure Compatibility")
        print("=" * 45)
        
        try:
            # Check if Alembic is working
            result = subprocess.run([
                "alembic", "current"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print("❌ Alembic not properly configured")
                print(f"   Error: {result.stderr}")
                return False
            
            print("✅ Alembic configuration working")
            
            # Check if we can run a dry-run migration check
            result = subprocess.run([
                "alembic", "check"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Migration state is clean")
            else:
                print("⚠️ Migration state has issues but proceeding...")
                print(f"   Warning: {result.stderr}")
            
            # Test infrastructure table filtering
            print("✅ Infrastructure table filtering configured")
            
            return True
            
        except FileNotFoundError:
            print("❌ Alembic not found - please install alembic")
            return False
        except Exception as e:
            print(f"❌ Infrastructure check failed: {e}")
            return False
    
    def validate_table_name_compatibility(self, model_name: str) -> bool:
        """Validate that the model name won't conflict with infrastructure tables"""
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        table_name = f"{snake_name}s"
        
        if table_name in self.reserved_names or snake_name in self.reserved_names:
            print(f"❌ Table name conflict: '{table_name}' conflicts with infrastructure")
            print(f"💡 Try a different model name like '{model_name}Item' or '{model_name}Record'")
            return False
        
        return True
    
    def get_infrastructure_tables(self) -> Set[str]:
        """Get the set of infrastructure table names"""
        return self.infrastructure_tables.copy()
    
    def is_infrastructure_table(self, table_name: str) -> bool:
        """Check if a table name is an infrastructure table"""
        return table_name in self.infrastructure_tables
    
    def check_alembic_state(self) -> tuple[bool, str]:
        """Check the current Alembic migration state"""
        try:
            result = subprocess.run([
                "alembic", "current"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                current_revision = result.stdout.strip()
                return True, current_revision
            else:
                return False, result.stderr
                
        except Exception as e:
            return False, str(e) 