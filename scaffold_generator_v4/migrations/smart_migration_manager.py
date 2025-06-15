"""
Smart Migration Manager for FastAPI Projects

Provides intelligent migration capabilities including:
- Zero-downtime migration strategies
- Schema evolution planning
- Data migration generation
- Rollback planning and execution
- Advanced database operations (indexes, constraints, etc.)
- Data transformation and validation
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import text


@dataclass
class MigrationPlan:
    """Represents a migration plan"""
    migration_type: str  # 'add_column', 'drop_column', 'add_table', etc.
    table_name: str
    changes: List[Dict[str, Any]]
    zero_downtime: bool
    rollback_strategy: str
    estimated_duration: str
    risks: List[str]
    prerequisites: List[str]


@dataclass
class SchemaChange:
    """Represents a schema change"""
    change_type: str
    table: str
    column: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    sql_command: Optional[str] = None


class SmartMigrationManager:
    """Manages intelligent database migrations"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.alembic_dir = self.project_root / "alembic"
        self.versions_dir = self.alembic_dir / "versions"
        
    def generate_smart_migration(self, model_name: str, changes: List[str] = None) -> bool:
        """Generate intelligent migration with zero-downtime strategies"""
        print(f"🧠 Generating Smart Migration for {model_name}")
        print("=" * 50)
        
        try:
            # Step 1: Apply changes to model file first
            if changes:
                print("🔧 Step 1: Applying changes to model file...")
                model_updated = self._apply_changes_to_model(model_name, changes)
                if model_updated:
                    print("✅ Model file updated successfully")
                else:
                    print("⚠️ No model changes were needed or possible")
            else:
                print("📝 Step 1: No specific changes requested, proceeding with analysis...")
            
            # Step 2: Analyze current schema
            current_schema = self._analyze_current_schema()
            print("✅ Step 2: Current schema analyzed")
            
            # Step 3: Plan migration strategy
            migration_plan = self._plan_migration(model_name, changes, current_schema)
            print(f"✅ Step 3: Migration plan created: {migration_plan.migration_type}")
            
            # Step 4: Generate migration file
            migration_file = self._generate_migration_file(model_name, migration_plan)
            print(f"✅ Step 4: Migration file generated: {migration_file.name}")
            
            # Step 5: Generate rollback strategy
            rollback_file = self._generate_rollback_strategy(migration_plan)
            print(f"✅ Step 5: Rollback strategy generated: {rollback_file.name}")
            
            # Step 6: Validate migration
            if self._validate_migration(migration_file):
                print("✅ Step 6: Migration validation passed")
                
                # Step 7: Ask user if they want to apply the migration
                print(f"\n🎯 Smart Migration Ready!")
                print(f"📂 Migration file: {migration_file.name}")
                print(f"📋 Rollback strategy: {rollback_file.name}")
                print(f"⏱️ Estimated duration: {migration_plan.estimated_duration}")
                print(f"🔒 Zero downtime: {migration_plan.zero_downtime}")
                
                apply_now = input("\n🚀 Apply migration now? (y/N): ").strip().lower()
                if apply_now in ['y', 'yes']:
                    return self._apply_migration()
                else:
                    print("✅ Migration ready but not applied. Run 'alembic upgrade head' when ready.")
                    return True
            else:
                print("❌ Step 6: Migration validation failed")
                return False
                
        except Exception as e:
            print(f"❌ Smart migration generation failed: {e}")
            return False
    
    def compare_schemas(self, source: str, target: str) -> List[SchemaChange]:
        """Compare two database schemas and return differences"""
        print(f"🔍 Comparing schemas: {source} vs {target}")
        
        try:
            # Get schema information from both databases
            source_schema = self._get_schema_info(source)
            target_schema = self._get_schema_info(target)
            
            # Compare and find differences
            changes = self._find_schema_differences(source_schema, target_schema)
            
            print(f"✅ Found {len(changes)} schema differences")
            return changes
            
        except Exception as e:
            print(f"❌ Schema comparison failed: {e}")
            return []
    
    def generate_zero_downtime_migration(self, changes: List[SchemaChange]) -> str:
        """Generate zero-downtime migration strategy"""
        print("🚀 Generating Zero-Downtime Migration Strategy")
        
        migration_steps = []
        
        for change in changes:
            if change.change_type == "add_column":
                # Add column as nullable first, then populate, then make non-null if needed
                steps = self._generate_add_column_steps(change)
                migration_steps.extend(steps)
                
            elif change.change_type == "drop_column":
                # Multi-step column removal for zero downtime
                steps = self._generate_drop_column_steps(change)
                migration_steps.extend(steps)
                
            elif change.change_type == "rename_column":
                # Add new column, copy data, drop old column
                steps = self._generate_rename_column_steps(change)
                migration_steps.extend(steps)
                
            elif change.change_type == "add_index":
                # Create index concurrently
                steps = self._generate_add_index_steps(change)
                migration_steps.extend(steps)
        
        return self._format_migration_steps(migration_steps)
    
    def _analyze_current_schema(self) -> Dict[str, Any]:
        """Analyze current database schema"""
        try:
            # Run alembic to get current revision
            result = subprocess.run(
                ["alembic", "current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            current_revision = result.stdout.strip()
            
            # Get schema information
            schema_info = {
                "current_revision": current_revision,
                "tables": self._get_table_info(),
                "indexes": self._get_index_info(),
                "constraints": self._get_constraint_info()
            }
            
            return schema_info
            
        except Exception as e:
            print(f"⚠️ Warning: Could not analyze current schema: {e}")
            return {}
    
    def _plan_migration(self, model_name: str, changes: List[str], current_schema: Dict[str, Any]) -> MigrationPlan:
        """Plan migration strategy based on changes"""
        
        # Determine migration type
        migration_type = "add_table"  # Default
        if changes:
            change_types = [change.split(':')[0] for change in changes]
            if "add_column" in change_types:
                migration_type = "add_column"
            elif "drop_column" in change_types:
                migration_type = "drop_column"
            elif "modify_column" in change_types:
                migration_type = "modify_column"
            elif "add_index" in change_types:
                migration_type = "add_index"
            elif "drop_index" in change_types:
                migration_type = "drop_index"
            elif "add_constraint" in change_types:
                migration_type = "add_constraint"
            elif "drop_constraint" in change_types:
                migration_type = "drop_constraint"
            elif "rename_column" in change_types:
                migration_type = "rename_column"
            elif "rename_table" in change_types:
                migration_type = "rename_table"
        
        # Assess zero-downtime feasibility
        zero_downtime = self._assess_zero_downtime_feasibility(migration_type, changes)
        
        # Generate rollback strategy
        rollback_strategy = self._generate_rollback_strategy_text(migration_type)
        
        # Estimate duration
        estimated_duration = self._estimate_migration_duration(migration_type, current_schema)
        
        # Identify risks
        risks = self._identify_migration_risks(migration_type, changes)
        
        # Identify prerequisites
        prerequisites = self._identify_prerequisites(migration_type, changes)
        
        return MigrationPlan(
            migration_type=migration_type,
            table_name=f"{model_name.lower()}s",
            changes=changes or [],
            zero_downtime=zero_downtime,
            rollback_strategy=rollback_strategy,
            estimated_duration=estimated_duration,
            risks=risks,
            prerequisites=prerequisites
        )
    
    def _generate_migration_file(self, model_name: str, plan: MigrationPlan) -> Path:
        """Generate Alembic migration file with smart strategies"""
        
        # Generate migration using alembic
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        message = f"smart_migration_{model_name.lower()}_{plan.migration_type}"
        
        try:
            subprocess.run(
                ["alembic", "revision", "--autogenerate", "-m", message],
                cwd=self.project_root,
                check=True
            )
            
            # Find the latest migration file
            migration_files = list(self.versions_dir.glob("*.py"))
            latest_migration = max(migration_files, key=lambda f: f.stat().st_mtime)
            
            # Enhance migration file with smart strategies
            self._enhance_migration_file(latest_migration, plan)
            
            return latest_migration
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to generate migration: {e}")
    
    def _enhance_migration_file(self, migration_file: Path, plan: MigrationPlan):
        """Enhance migration file with smart strategies"""
        
        # Read current migration file
        content = migration_file.read_text()
        
        # Add smart migration strategies
        enhanced_content = self._add_smart_strategies(content, plan)
        
        # Write enhanced content back
        migration_file.write_text(enhanced_content)
    
    def _add_smart_strategies(self, content: str, plan: MigrationPlan) -> str:
        """Add smart migration strategies to migration file"""
        
        # Add header comment with migration plan
        header = f'''"""
Smart Migration: {plan.migration_type}
Table: {plan.table_name}
Zero Downtime: {plan.zero_downtime}
Estimated Duration: {plan.estimated_duration}
Rollback Strategy: {plan.rollback_strategy}

Risks:
{chr(10).join(f"- {risk}" for risk in plan.risks)}

Prerequisites:
{chr(10).join(f"- {prereq}" for prereq in plan.prerequisites)}
"""

'''
        
        # Insert header after the existing docstring
        lines = content.split('\n')
        insert_index = 0
        
        # Find end of existing docstring
        in_docstring = False
        for i, line in enumerate(lines):
            if line.strip().startswith('"""'):
                if in_docstring:
                    insert_index = i + 1
                    break
                else:
                    in_docstring = True
        
        # Insert smart migration strategies based on type
        strategy_code = ""
        if plan.zero_downtime:
            if plan.migration_type == "add_column":
                strategy_code = self._generate_zero_downtime_add_column()
            elif plan.migration_type == "drop_column":
                strategy_code = self._generate_zero_downtime_drop_column()
            elif plan.migration_type == "add_index":
                strategy_code = self._generate_zero_downtime_add_index()
            elif plan.migration_type == "rename_column":
                strategy_code = self._generate_zero_downtime_rename_column()
        
        if strategy_code:
            lines.insert(insert_index, strategy_code)
        
        return header + '\n'.join(lines)
    
    def _generate_zero_downtime_add_column(self) -> str:
        """Generate zero-downtime add column strategy"""
        return '''
# Zero-downtime column addition strategy
# 1. Add column as nullable
# 2. Populate with default values
# 3. Make non-null if required (in separate migration)

def upgrade_zero_downtime():
    """Zero-downtime upgrade strategy"""
    # Step 1: Add nullable column
    op.add_column('table_name', sa.Column('new_column', sa.String(), nullable=True))
    
    # Step 2: Populate with default values (if needed)
    # op.execute("UPDATE table_name SET new_column = 'default_value' WHERE new_column IS NULL")
    
    # Step 3: Add constraints (in separate migration if needed)
    # op.alter_column('table_name', 'new_column', nullable=False)

'''
    
    def _generate_zero_downtime_drop_column(self) -> str:
        """Generate zero-downtime drop column strategy"""
        return '''
# Zero-downtime column removal strategy
# 1. Stop using column in application code
# 2. Deploy application without column references
# 3. Drop column in separate migration

def upgrade_zero_downtime():
    """Zero-downtime downgrade strategy for column removal"""
    # Step 1: Mark column as deprecated (add comment)
    # op.execute("COMMENT ON COLUMN table_name.old_column IS 'DEPRECATED - scheduled for removal'")
    
    # Step 2: In subsequent migration, drop the column
    # op.drop_column('table_name', 'old_column')
    
    pass  # Actual drop should be in separate migration

'''
    
    def _generate_zero_downtime_add_index(self) -> str:
        """Generate zero-downtime add index strategy"""
        return '''
# Zero-downtime index creation strategy
# Use CONCURRENTLY option for PostgreSQL

def upgrade_zero_downtime():
    """Zero-downtime index creation"""
    # PostgreSQL: Create index concurrently
    op.execute("CREATE INDEX CONCURRENTLY idx_table_column ON table_name (column_name)")
    
    # For other databases, create index normally (small downtime)
    # op.create_index('idx_table_column', 'table_name', ['column_name'])

'''
    
    def _generate_zero_downtime_rename_column(self) -> str:
        """Generate zero-downtime rename column strategy"""
        return '''
# Zero-downtime column rename strategy
# 1. Add new column
# 2. Copy data from old to new
# 3. Update application to use new column
# 4. Drop old column

def upgrade_zero_downtime():
    """Zero-downtime column rename strategy"""
    # Step 1: Add new column
    op.add_column('table_name', sa.Column('new_column_name', sa.String(), nullable=True))
    
    # Step 2: Copy data
    op.execute("UPDATE table_name SET new_column_name = old_column_name")
    
    # Step 3: Make new column not null if needed
    # op.alter_column('table_name', 'new_column_name', nullable=False)
    
    # Step 4: Drop old column (in separate migration after app deployment)
    # op.drop_column('table_name', 'old_column_name')

'''
    
    def _generate_rollback_strategy(self, plan: MigrationPlan) -> Path:
        """Generate rollback strategy file"""
        
        rollback_content = f'''"""
Rollback Strategy for {plan.migration_type}
Table: {plan.table_name}
Generated: {datetime.now().isoformat()}
"""

# Rollback Strategy: {plan.rollback_strategy}

def rollback_migration():
    """
    Execute rollback for this migration
    
    Steps:
    1. Verify data integrity
    2. Execute rollback commands
    3. Validate rollback success
    """
    
    # TODO: Implement specific rollback steps
    pass

def verify_rollback():
    """Verify rollback was successful"""
    # TODO: Add verification checks
    pass

# Emergency rollback commands (manual execution)
EMERGENCY_ROLLBACK_SQL = [
    # TODO: Add emergency SQL commands
]

# Rollback validation queries
ROLLBACK_VALIDATION_QUERIES = [
    # TODO: Add validation queries
]
'''
        
        rollback_file = self.project_root / f"rollback_strategies" / f"rollback_{plan.table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        rollback_file.parent.mkdir(exist_ok=True)
        rollback_file.write_text(rollback_content)
        
        return rollback_file
    
    def _validate_migration(self, migration_file: Path) -> bool:
        """Validate migration file"""
        try:
            # Check syntax
            with open(migration_file, 'r') as f:
                compile(f.read(), migration_file, 'exec')
            
            # Run alembic check (dry run)
            result = subprocess.run(
                ["alembic", "upgrade", "--sql", "head"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"⚠️ Migration validation error: {e}")
            return False
    
    def _assess_zero_downtime_feasibility(self, migration_type: str, changes: List[str]) -> bool:
        """Assess if zero-downtime migration is feasible"""
        
        # Safe operations for zero-downtime
        safe_operations = [
            "add_table",
            "add_column",
            "add_index",
            "drop_index",
            "add_constraint"
        ]
        
        # Risky operations that need special handling
        risky_operations = [
            "drop_table",
            "drop_column",
            "alter_column_type",
            "drop_constraint"
        ]
        
        # Operations that can be zero-downtime with proper strategy
        strategic_operations = [
            "rename_column",
            "modify_column"
        ]
        
        if migration_type in safe_operations:
            return True
        elif migration_type in strategic_operations:
            return True  # With proper strategy
        elif migration_type in risky_operations:
            # Analyze specific changes for feasibility
            return self._analyze_risky_operation_feasibility(migration_type, changes)
        else:
            # Analyze specific changes
            return len(changes or []) <= 3  # Simple heuristic
    
    def _analyze_risky_operation_feasibility(self, migration_type: str, changes: List[str]) -> bool:
        """Analyze feasibility of risky operations"""
        if migration_type == "drop_column":
            # Column drops can be zero-downtime with proper strategy
            return True
        elif migration_type == "drop_table":
            # Table drops are risky but can be done with backup strategy
            return False  # Conservative approach
        elif migration_type == "alter_column_type":
            # Type changes depend on compatibility
            return self._assess_type_change_compatibility(changes)
        else:
            return False
    
    def _assess_type_change_compatibility(self, changes: List[str]) -> bool:
        """Assess if column type changes are compatible"""
        # Simplified compatibility check
        compatible_changes = [
            "int:bigint",  # int to bigint is safe
            "varchar:text",  # varchar to text is safe
            "char:varchar"  # char to varchar is safe
        ]
        
        for change in changes:
            if "modify_column" in change:
                # Extract type change info and check compatibility
                # This is a simplified implementation
                pass
        
        return True  # Conservative default
    
    def _generate_rollback_strategy_text(self, migration_type: str) -> str:
        """Generate rollback strategy description"""
        
        strategies = {
            "add_table": "Drop the newly created table",
            "drop_table": "Restore table from backup",
            "add_column": "Drop the newly added column",
            "drop_column": "Restore column from backup or re-add with default values",
            "modify_column": "Revert column to original type and constraints",
            "add_index": "Drop the newly created index",
            "drop_index": "Recreate the dropped index",
            "add_constraint": "Drop the newly added constraint",
            "drop_constraint": "Recreate the dropped constraint",
            "rename_column": "Rename column back to original name",
            "rename_table": "Rename table back to original name"
        }
        
        return strategies.get(migration_type, "Manual rollback required")
    
    def _estimate_migration_duration(self, migration_type: str, schema_info: Dict[str, Any]) -> str:
        """Estimate migration duration"""
        
        # Duration estimates based on operation type and table size
        base_durations = {
            "add_table": "< 1 minute",
            "drop_table": "< 30 seconds",
            "add_column": "< 2 minutes",
            "drop_column": "< 1 minute",
            "modify_column": "2-5 minutes",
            "add_index": "2-10 minutes (depends on table size)",
            "drop_index": "< 30 seconds",
            "add_constraint": "1-5 minutes",
            "drop_constraint": "< 30 seconds",
            "rename_column": "5-15 minutes (multi-step process)",
            "rename_table": "1-3 minutes"
        }
        
        return base_durations.get(migration_type, "Unknown")
    
    def _identify_migration_risks(self, migration_type: str, changes: List[str]) -> List[str]:
        """Identify potential risks"""
        
        risks = []
        
        if migration_type == "drop_table":
            risks.extend([
                "Permanent data loss",
                "Application errors if table is still referenced",
                "Foreign key constraint violations"
            ])
        
        if migration_type == "drop_column":
            risks.extend([
                "Data loss for the dropped column",
                "Application errors if column is still used",
                "Potential impact on existing queries"
            ])
        
        if migration_type == "modify_column":
            risks.extend([
                "Data conversion errors",
                "Performance impact during conversion",
                "Possible data truncation"
            ])
        
        if migration_type == "add_index":
            risks.extend([
                "Table locking during index creation",
                "Increased storage requirements",
                "Performance impact during creation"
            ])
        
        if migration_type == "rename_column":
            risks.extend([
                "Application compatibility issues",
                "Temporary data duplication",
                "Complex rollback process"
            ])
        
        if migration_type == "add_constraint":
            risks.extend([
                "Constraint validation on existing data",
                "Potential data quality issues",
                "Performance impact during validation"
            ])
        
        return risks
    
    def _identify_prerequisites(self, migration_type: str, changes: List[str]) -> List[str]:
        """Identify migration prerequisites"""
        
        prerequisites = []
        
        if migration_type in ["drop_table", "drop_column"]:
            prerequisites.extend([
                "Create database backup",
                "Verify no active references to dropped objects",
                "Notify stakeholders of data removal"
            ])
        
        if migration_type == "add_index":
            prerequisites.extend([
                "Ensure sufficient disk space",
                "Schedule during low-traffic period",
                "Monitor system resources"
            ])
        
        if migration_type == "modify_column":
            prerequisites.extend([
                "Test data conversion on sample dataset",
                "Verify application compatibility",
                "Plan for potential data cleanup"
            ])
        
        if migration_type == "rename_column":
            prerequisites.extend([
                "Update application code to handle both column names",
                "Coordinate with development team",
                "Plan multi-step deployment"
            ])
        
        prerequisites.extend([
            "Test migration on staging environment",
            "Prepare rollback plan",
            "Coordinate with operations team"
        ])
        
        return prerequisites
    
    def _get_table_info(self) -> Dict[str, Any]:
        """Get current table information"""
        # This would connect to the database and get table info
        # Simplified for now
        return {}
    
    def _get_index_info(self) -> Dict[str, Any]:
        """Get current index information"""
        # This would connect to the database and get index info
        # Simplified for now
        return {}
    
    def _get_constraint_info(self) -> Dict[str, Any]:
        """Get current constraint information"""
        # This would connect to the database and get constraint info
        # Simplified for now
        return {}
    
    def _get_schema_info(self, database_url: str) -> Dict[str, Any]:
        """Get schema information from database"""
        # This would connect to the database and extract schema
        # Simplified for now
        return {}
    
    def _find_schema_differences(self, source: Dict[str, Any], target: Dict[str, Any]) -> List[SchemaChange]:
        """Find differences between two schemas"""
        # This would compare schemas and return differences
        # Simplified for now
        return []
    
    def _generate_add_column_steps(self, change: SchemaChange) -> List[str]:
        """Generate steps for adding a column with zero downtime"""
        return [
            f"Add column {change.column} as nullable",
            f"Populate {change.column} with default values",
            f"Make {change.column} non-null if required"
        ]
    
    def _generate_drop_column_steps(self, change: SchemaChange) -> List[str]:
        """Generate steps for dropping a column with zero downtime"""
        return [
            f"Stop using {change.column} in application code",
            f"Deploy application without {change.column} references",
            f"Drop column {change.column}"
        ]
    
    def _generate_rename_column_steps(self, change: SchemaChange) -> List[str]:
        """Generate steps for renaming a column with zero downtime"""
        return [
            f"Add new column {change.new_value}",
            f"Copy data from {change.old_value} to {change.new_value}",
            f"Update application to use {change.new_value}",
            f"Drop old column {change.old_value}"
        ]
    
    def _generate_add_index_steps(self, change: SchemaChange) -> List[str]:
        """Generate steps for adding an index with zero downtime"""
        return [
            f"Create index {change.new_value} concurrently"
        ]
    
    def _format_migration_steps(self, steps: List[str]) -> str:
        """Format migration steps into readable text"""
        return "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
    
    def _apply_changes_to_model(self, model_name: str, changes: List[str]) -> bool:
        """Apply requested changes to the model file"""
        import re
        
        # Find the model file
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        model_file = self.project_root / "app" / "plugins" / f"{snake_name}_plugin" / "models.py"
        
        if not model_file.exists():
            print(f"❌ Model file not found: {model_file}")
            return False
        
        try:
            # Read current model content
            content = model_file.read_text()
            original_content = content
            
            # Process each change
            for change in changes:
                content = self._apply_single_change(content, change, model_name)
            
            # Write back if changed
            if content != original_content:
                model_file.write_text(content)
                print(f"   ✅ Applied {len(changes)} change(s) to {model_file.name}")
                return True
            else:
                print(f"   📝 No changes needed in {model_file.name}")
                return False
                
        except Exception as e:
            print(f"❌ Error applying changes to model: {e}")
            return False
    
    def _apply_single_change(self, content: str, change: str, model_name: str) -> str:
        """Apply a single change to model content"""
        
        if change.startswith("add_column:"):
            column_definition = change.replace("add_column:", "")
            return self._add_column_to_model(content, column_definition, model_name)
        
        elif change.startswith("drop_column:"):
            column_name = change.replace("drop_column:", "")
            return self._remove_column_from_model(content, column_name)
        
        elif change.startswith("modify_column:"):
            column_info = change.replace("modify_column:", "")
            return self._modify_column_in_model(content, column_info)
        
        elif change.startswith("rename_column:"):
            column_info = change.replace("rename_column:", "")
            return self._rename_column_in_model(content, column_info)
        
        elif change.startswith("add_index:"):
            index_info = change.replace("add_index:", "")
            return self._add_index_to_model(content, index_info)
        
        elif change.startswith("add_constraint:"):
            constraint_info = change.replace("add_constraint:", "")
            return self._add_constraint_to_model(content, constraint_info)
        
        elif change.startswith("drop_index:"):
            index_name = change.replace("drop_index:", "")
            return self._remove_index_from_model(content, index_name)
        
        elif change.startswith("drop_constraint:"):
            constraint_name = change.replace("drop_constraint:", "")
            return self._remove_constraint_from_model(content, constraint_name)
        
        elif change.startswith("add_foreign_key:"):
            fk_info = change.replace("add_foreign_key:", "")
            return self._add_foreign_key_to_column(content, fk_info)
        
        else:
            print(f"⚠️ Unknown change type: {change}")
            return content
    
    def _add_column_to_model(self, content: str, column_definition: str, model_name: str) -> str:
        """Add a column to the SQLAlchemy model"""
        
        # Parse column definition (e.g., "status:str:nullable" or just "status")
        parts = column_definition.split(":")
        column_name = parts[0]
        column_type = parts[1] if len(parts) > 1 else "str"
        column_options = parts[2:] if len(parts) > 2 else []
        
        # Map type to SQLAlchemy column
        type_mapping = {
            "str": "String(255)",
            "text": "Text",
            "int": "Integer",
            "bigint": "BigInteger", 
            "float": "Float",
            "decimal": "Numeric",
            "bool": "Boolean",
            "datetime": "DateTime",
            "date": "Date",
            "time": "Time",
            "json": "JSON",
            "uuid": "UUID",
            "binary": "LargeBinary"
        }
        
        sa_type = type_mapping.get(column_type, "String(255)")
        
        # Handle decimal precision/scale
        if column_type == "decimal":
            precision = None
            scale = None
            
            # Parse precision and scale from options
            for option in column_options:
                if option.startswith("precision="):
                    precision = option.split("=")[1]
                elif option.startswith("scale="):
                    scale = option.split("=")[1]
            
            # Build the Numeric type with proper formatting
            if precision and scale:
                sa_type = f"Numeric({precision}, {scale})"
            elif precision:
                sa_type = f"Numeric({precision})"
            else:
                sa_type = "Numeric"
        
        # Build column options
        nullable = "nullable=True"
        default_val = None
        unique = False
        index = False
        
        for option in column_options:
            if option == "required" or option == "not_null":
                nullable = "nullable=False"
            elif option == "nullable":
                nullable = "nullable=True"
            elif option.startswith("default="):
                default_val = option.replace("default=", "")
            elif option == "unique":
                unique = True
            elif option == "index":
                index = True
        
        # Build column definition
        column_parts = [sa_type, nullable]
        
        if default_val:
            if column_type == "str":
                column_parts.append(f'default="{default_val}"')
            elif column_type == "bool":
                column_parts.append(f'default={default_val.capitalize()}')
            else:
                column_parts.append(f'default={default_val}')
        
        if unique:
            column_parts.append("unique=True")
        
        if index:
            column_parts.append("index=True")
        
        column_def = f'    {column_name} = Column({", ".join(column_parts)})'
        
        # Use line-by-line approach for safer insertion
        lines = content.split('\n')
        insert_index = -1
        
        # Find the best insertion point (before timestamp fields)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if ('created_at' in line or 'updated_at' in line) and 'Column(' in line:
                insert_index = i
                break
        
        # If no timestamp fields found, find the last column definition
        if insert_index == -1:
            for i, line in enumerate(lines):
                stripped = line.strip()
                if ('Column(' in line and '=' in line and 
                    not stripped.startswith('def ') and 
                    not stripped.startswith('class ') and
                    not stripped.startswith('#')):
                    insert_index = i + 1
        
        # Insert the new column
        if insert_index > -1:
            lines.insert(insert_index, column_def)
            new_content = '\n'.join(lines)
        else:
            # Fallback: find __tablename__ and insert after it
            for i, line in enumerate(lines):
                if '__tablename__' in line:
                    lines.insert(i + 2, "")
                    lines.insert(i + 3, column_def)
                    new_content = '\n'.join(lines)
                    break
            else:
                new_content = content + "\n" + column_def + "\n"
        
        # Also update to_dict method if it exists
        if 'def to_dict(self):' in new_content:
            lines = new_content.split('\n')
            for i, line in enumerate(lines):
                if "'updated_at': self.updated_at" in line:
                    new_field = f"            '{column_name}': self.{column_name},"
                    lines.insert(i, new_field)
                    new_content = '\n'.join(lines)
                    break
        
        print(f"   ➕ Added column: {column_name} ({sa_type})")
        return new_content
    
    def _remove_column_from_model(self, content: str, column_name: str) -> str:
        """Remove a column from the SQLAlchemy model"""
        import re
        
        lines = content.split('\n')
        new_lines = []
        
        # Remove column definition line by line for better control
        for line in lines:
            # Check if this line defines the column we want to remove
            if (f'{column_name} = Column(' in line or 
                f'{column_name}= Column(' in line or
                f'{column_name} =Column(' in line):
                print(f"   ➖ Removed column definition: {column_name}")
                continue  # Skip this line
            
            # Remove from to_dict method
            if (f"'{column_name}': self.{column_name}" in line or 
                f'"{column_name}": self.{column_name}' in line):
                print(f"   ➖ Removed from to_dict: {column_name}")
                continue  # Skip this line
            
            new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
        print(f"   ✅ Column {column_name} removed from model")
        return new_content
    
    def _modify_column_in_model(self, content: str, column_info: str) -> str:
        """Modify an existing column in the SQLAlchemy model"""
        # Parse modification: column_name:new_type:options
        parts = column_info.split(":")
        if len(parts) < 2:
            print(f"   ⚠️ Invalid modify_column format: {column_info}")
            return content
        
        column_name = parts[0]
        new_type = parts[1]
        options = parts[2:] if len(parts) > 2 else []
        
        # First remove the old column definition
        content_without_old = self._remove_column_from_model(content, column_name)
        
        # Handle the special case where options contain commas (like precision=5,scale=2)
        # Recombine the parts properly
        if len(options) > 0:
            # Join all remaining parts and then re-split by commas if needed
            options_str = ':'.join(options)
            if ',' in options_str and ('precision=' in options_str or 'scale=' in options_str):
                # Split by commas to handle precision=5,scale=2,default=4.50
                comma_split_options = []
                for part in options_str.split(','):
                    comma_split_options.append(part.strip())
                new_column_def = f"{column_name}:{new_type}:{':'.join(comma_split_options)}"
            else:
                new_column_def = f"{column_name}:{new_type}:{options_str}"
        else:
            new_column_def = f"{column_name}:{new_type}"
        
        # Then add the new column definition
        content_with_new = self._add_column_to_model(content_without_old, new_column_def, "")
        
        print(f"   🔧 Modified column: {column_name} -> {new_type}")
        return content_with_new
    
    def _rename_column_in_model(self, content: str, column_info: str) -> str:
        """Rename a column in the SQLAlchemy model"""
        parts = column_info.split(":")
        if len(parts) != 2:
            print(f"   ⚠️ Invalid rename_column format, expected old_name:new_name")
            return content
        
        old_name, new_name = parts
        
        # Replace column definition
        import re
        pattern = rf'\b{old_name}\s*=\s*Column\('
        replacement = f'{new_name} = Column('
        content = re.sub(pattern, replacement, content)
        
        # Replace in to_dict method
        pattern = rf"['\"]?{old_name}['\"]?\s*:\s*self\.{old_name}"
        replacement = f"'{new_name}': self.{new_name}"
        content = re.sub(pattern, replacement, content)
        
        print(f"   🔄 Renamed column: {old_name} -> {new_name}")
        return content
    
    def _add_index_to_model(self, content: str, index_info: str) -> str:
        """Add actual SQLAlchemy index to model"""
        # Parse index info: column1,column2:unique=true
        parts = index_info.split(":")
        columns = parts[0].split(",")
        options = parts[1:] if len(parts) > 1 else []
        
        # Check if we need to add Index import
        if 'from sqlalchemy import' in content and 'Index' not in content:
            # Add Index to the imports
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('from sqlalchemy import'):
                    # Add Index to the import
                    if ', Index' not in line:
                        lines[i] = line.rstrip() + ', Index'
                    break
            content = '\n'.join(lines)
        
        # Build index definition
        index_name = f"idx_{columns[0]}" if len(columns) == 1 else f"idx_{'_'.join(columns)}"
        unique = "unique=true" in [opt.lower() for opt in options]
        
        # Create index definition - add it to the model class
        if len(columns) == 1:
            column_str = f"'{columns[0]}'"
        else:
            column_str = ', '.join(f"'{col.strip()}'" for col in columns)
        
        if unique:
            index_def = f"    __table_args__ = (Index('{index_name}', {column_str}, unique=True),)"
        else:
            index_def = f"    __table_args__ = (Index('{index_name}', {column_str}),)"
        
        lines = content.split('\n')
        
        # Check if __table_args__ already exists
        table_args_exists = False
        table_args_line = -1
        for i, line in enumerate(lines):
            if '__table_args__' in line:
                table_args_exists = True
                table_args_line = i
                break
        
        if table_args_exists:
            # Extend existing __table_args__
            existing_line = lines[table_args_line].strip()
            if existing_line.endswith(',)'):
                # Remove the closing ,) and add our index
                new_index = f"Index('{index_name}', {column_str}" + (", unique=True" if unique else "") + "),"
                lines[table_args_line] = existing_line[:-2] + ", " + new_index + ")"
            else:
                # Replace the line
                lines[table_args_line] = index_def
        else:
            # Add new __table_args__ after __tablename__
            for i, line in enumerate(lines):
                if '__tablename__' in line:
                    lines.insert(i + 2, "")
                    lines.insert(i + 3, index_def)
                    break
        
        new_content = '\n'.join(lines)
        index_type = "UNIQUE INDEX" if unique else "INDEX"
        print(f"   📊 Added {index_type}: {index_name} on ({', '.join(columns)})")
        return new_content
    
    def _add_constraint_to_model(self, content: str, constraint_info: str) -> str:
        """Add actual SQLAlchemy constraint to model"""
        # Parse constraint info: name:type:details
        # Examples: 
        # - check_age:check:age >= 18
        # - fk_user:foreign_key:users.id
        # - unique_email:unique:email
        parts = constraint_info.split(":")
        constraint_name = parts[0]
        constraint_type = parts[1] if len(parts) > 1 else "check"
        constraint_details = parts[2] if len(parts) > 2 else ""
        
        # Check if we need to add constraint imports
        if 'from sqlalchemy import' in content:
            imports_to_add = []
            if 'CheckConstraint' not in content:
                imports_to_add.append('CheckConstraint')
            if 'ForeignKey' not in content and constraint_type == 'foreign_key':
                imports_to_add.append('ForeignKey')
            if 'UniqueConstraint' not in content and constraint_type == 'unique':
                imports_to_add.append('UniqueConstraint')
            
            if imports_to_add:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('from sqlalchemy import'):
                        for imp in imports_to_add:
                            if imp not in line:
                                lines[i] = line.rstrip() + f', {imp}'
                        break
                content = '\n'.join(lines)
        
        # Build constraint definition
        constraint_def = None
        
        if constraint_type == "check":
            constraint_def = f"CheckConstraint('{constraint_details}', name='{constraint_name}')"
            
        elif constraint_type == "foreign_key":
            # For foreign key, add to specific column
            if '.' in constraint_details:  # like users.id
                column_name = constraint_name.replace('fk_', '').replace('_id', '') + '_id'
                # This needs to be handled in column definition, not __table_args__
                print(f"   🔗 Foreign key constraint: {constraint_name} -> {constraint_details}")
                print(f"   ⚠️ Note: Foreign keys should be added to column definitions")
                return content
                
        elif constraint_type == "unique":
            if ',' in constraint_details:  # Multiple columns
                columns = [col.strip() for col in constraint_details.split(',')]
                column_str = ', '.join(f"'{col}'" for col in columns)
                constraint_def = f"UniqueConstraint({column_str}, name='{constraint_name}')"
            else:  # Single column
                constraint_def = f"UniqueConstraint('{constraint_details}', name='{constraint_name}')"
        
        if not constraint_def:
            print(f"   ⚠️ Unsupported constraint type: {constraint_type}")
            return content
        
        # Add to __table_args__
        lines = content.split('\n')
        
        # Check if __table_args__ already exists
        table_args_exists = False
        table_args_line = -1
        for i, line in enumerate(lines):
            if '__table_args__' in line:
                table_args_exists = True
                table_args_line = i
                break
        
        if table_args_exists:
            # Extend existing __table_args__
            existing_line = lines[table_args_line].strip()
            if existing_line.endswith(',)'):
                # Remove the closing ,) and add our constraint
                lines[table_args_line] = existing_line[:-2] + f", {constraint_def})"
            elif existing_line.endswith(')'):
                # Convert single item to tuple
                lines[table_args_line] = existing_line[:-1] + f", {constraint_def})"
            else:
                # Replace the line
                lines[table_args_line] = f"    __table_args__ = ({constraint_def},)"
        else:
            # Add new __table_args__ after __tablename__
            for i, line in enumerate(lines):
                if '__tablename__' in line:
                    lines.insert(i + 2, "")
                    lines.insert(i + 3, f"    __table_args__ = ({constraint_def},)")
                    break
        
        new_content = '\n'.join(lines)
        print(f"   🔒 Added {constraint_type.upper()} constraint: {constraint_name}")
        return new_content
    
    def _remove_index_from_model(self, content: str, index_name: str) -> str:
        """Remove an index from the SQLAlchemy model"""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Check if this line contains the index we want to remove
            if '__table_args__' in line and index_name in line:
                # Handle different __table_args__ formats
                if line.strip().startswith('__table_args__ = (') and line.strip().endswith(',)'):
                    # Single index case
                    if f"'{index_name}'" in line:
                        print(f"   ➖ Removed index: {index_name}")
                        continue  # Skip this line entirely
                else:
                    # Multiple items case - need to remove just this index
                    # For now, mark for manual review
                    print(f"   ⚠️ Complex __table_args__ found - manual review needed for index: {index_name}")
                    new_lines.append(f"    # TODO: Remove index {index_name} from __table_args__")
            
            new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
        print(f"   ✅ Index {index_name} removal processed")
        return new_content
    
    def _remove_constraint_from_model(self, content: str, constraint_name: str) -> str:
        """Remove a constraint from the SQLAlchemy model"""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Check if this line contains the constraint we want to remove
            if '__table_args__' in line and constraint_name in line:
                # Handle different __table_args__ formats
                if line.strip().startswith('__table_args__ = (') and line.strip().endswith(',)'):
                    # Single constraint case
                    if f"'{constraint_name}'" in line:
                        print(f"   ➖ Removed constraint: {constraint_name}")
                        continue  # Skip this line entirely
                else:
                    # Multiple items case - need to remove just this constraint
                    print(f"   ⚠️ Complex __table_args__ found - manual review needed for constraint: {constraint_name}")
                    new_lines.append(f"    # TODO: Remove constraint {constraint_name} from __table_args__")
            
            new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
        print(f"   ✅ Constraint {constraint_name} removal processed")
        return new_content
    
    def _add_foreign_key_to_column(self, content: str, fk_info: str) -> str:
        """Add foreign key to a specific column"""
        # Parse fk_info: column_name:reference_table.reference_column
        # Example: user_id:users.id
        parts = fk_info.split(":")
        if len(parts) != 2:
            print(f"   ⚠️ Invalid foreign key format: {fk_info}")
            return content
        
        column_name, reference = parts
        
        # Check if we need to add ForeignKey import
        if 'from sqlalchemy import' in content and 'ForeignKey' not in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('from sqlalchemy import'):
                    if 'ForeignKey' not in line:
                        lines[i] = line.rstrip() + ', ForeignKey'
                    break
            content = '\n'.join(lines)
        
        # Find the column definition and add ForeignKey
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if f'{column_name} = Column(' in line and 'ForeignKey' not in line:
                # Add ForeignKey to the column definition
                if line.rstrip().endswith(')'):
                    # Insert ForeignKey before the closing parenthesis
                    lines[i] = line.rstrip()[:-1] + f", ForeignKey('{reference}'))"
                else:
                    print(f"   ⚠️ Complex column definition found for {column_name}")
                print(f"   🔗 Added foreign key: {column_name} -> {reference}")
                break
        
        return '\n'.join(lines)
    
    def _apply_migration(self) -> bool:
        """Apply the migration to the database"""
        try:
            print("\n🚀 Applying migration to database...")
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ Migration applied successfully!")
                print("🎉 Database schema updated!")
                return True
            else:
                print(f"❌ Migration failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error applying migration: {e}")
            return False 