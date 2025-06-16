# Database Utilities

This directory contains utility scripts for managing database operations, particularly useful for debugging, verification, and maintenance tasks related to the FastAPI PostgreSQL project.

## 🛠️ Available Utilities

### 1. `fix_alembic_version.py` - Alembic State Management

A comprehensive utility for fixing corrupted alembic version states that can occur during development.

#### **When to Use:**
- After manually deleting migration files
- When `alembic current` shows "Can't locate revision" errors
- When database and migration files get out of sync
- After removing models with migrations

#### **Usage Examples:**

```bash
# Check current alembic version
python fix_alembic_version.py --current

# List all available revisions
python fix_alembic_version.py --list

# Fix to a specific revision
python fix_alembic_version.py --revision ec62d2a648e7

# Interactive fix (prompts for confirmation)
python fix_alembic_version.py
```

#### **Features:**
- ✅ Interactive confirmation for safety
- ✅ Current version checking
- ✅ Available revisions listing
- ✅ Command-line argument support
- ✅ Error handling and validation
- ✅ Backup recommendations in comments

#### **Safety Notes:**
- Always backup your database before running
- Verify the target revision exists in `alembic history`
- This directly modifies the `alembic_version` table

---

### 2. `check_table.py` - Database Table Verification

A powerful utility for checking table existence, listing tables, and getting detailed table information.

#### **When to Use:**
- Verifying model removal operations
- Checking database state after migrations
- Debugging table existence issues
- Validating database cleanup operations

#### **Usage Examples:**

```bash
# Default check (test_removal5s table)
python check_table.py

# Check specific table
python check_table.py --table users

# Check multiple tables
python check_table.py --table users --table products --table orders

# List all tables in database
python check_table.py --list-all

# Check tables matching pattern (supports wildcards)
python check_table.py --pattern "test_*"
python check_table.py --pattern "*_plugin"
python check_table.py --pattern "user*"

# Get detailed table information
python check_table.py --info users
```

#### **Features:**
- ✅ Single table existence checking
- ✅ Multiple table batch checking
- ✅ Pattern matching with wildcards
- ✅ Complete database table listing
- ✅ Detailed table information (columns, types, constraints, row counts)
- ✅ Error handling and validation
- ✅ Colored output for better readability

#### **Output Examples:**

```bash
# Table existence check
$ python check_table.py --table users --table nonexistent
🔍 Checking specific tables:
  users: ✅ EXISTS
  nonexistent: ❌ NOT FOUND

# Pattern matching
$ python check_table.py --pattern "test_*"
🔍 Checking tables matching pattern: test_*
  test_cleanups: ✅ EXISTS
  test_items: ✅ EXISTS

# Detailed info
$ python check_table.py --info users
📊 Detailed info for table: users
  ✅ Table exists
  📊 Row count: 5
  📋 Columns (8):
    • id: integer NOT NULL DEFAULT nextval('users_id_seq'::regclass)
    • username: character varying NOT NULL
    • email: character varying NOT NULL
    • created_at: timestamp without time zone NOT NULL
    • updated_at: timestamp without time zone NOT NULL
```

---

## 🔧 Integration with Scaffold Generator

These utilities are designed to work seamlessly with the enhanced scaffold generator v4:

### **Model Removal Workflow:**

1. **Before Removal** - Check what exists:
   ```bash
   python scaffold_generator_v4/main.py show-deps ModelName
   python check_table.py --pattern "model_name*"
   ```

2. **Perform Removal** - Use enhanced remove command:
   ```bash
   python scaffold_generator_v4/main.py remove ModelName --with-migrations --force
   ```

3. **Verify Removal** - Confirm cleanup:
   ```bash
   python check_table.py --table model_names
   python fix_alembic_version.py --current
   ```

4. **Fix State if Needed** - Handle any issues:
   ```bash
   python fix_alembic_version.py --list
   python fix_alembic_version.py --revision <correct_head>
   ```

### **Migration Debugging Workflow:**

1. **Check Current State:**
   ```bash
   python fix_alembic_version.py --current
   python fix_alembic_version.py --list
   alembic current
   ```

2. **Fix Corrupted State:**
   ```bash
   python scaffold_generator_v4/main.py fix-alembic
   # OR manually:
   python fix_alembic_version.py --revision <target_revision>
   ```

3. **Verify Fix:**
   ```bash
   alembic current
   python check_table.py --list-all
   ```

---

## 🚀 Advanced Usage

### **Batch Operations:**

```bash
# Check all test tables
python check_table.py --pattern "test_*"

# Check all plugin-related tables
python check_table.py --pattern "*_plugin*"

# Get info on multiple tables
for table in users products orders; do
    python check_table.py --info $table
done
```

### **Scripting Integration:**

```python
# In your Python scripts
import asyncio
from check_table import check_table_exists, list_all_tables

async def verify_cleanup():
    tables = await list_all_tables()
    test_tables = [t for t in tables if t.startswith('test_')]
    print(f"Found {len(test_tables)} test tables")
    
    for table in test_tables:
        exists = await check_table_exists(table)
        print(f"{table}: {'EXISTS' if exists else 'REMOVED'}")

asyncio.run(verify_cleanup())
```

### **CI/CD Integration:**

```yaml
# In your GitHub Actions or CI pipeline
- name: Verify Database State
  run: |
    python check_table.py --list-all
    python fix_alembic_version.py --current
    
- name: Check Test Tables Cleanup
  run: |
    python check_table.py --pattern "test_*" || echo "No test tables found (expected)"
```

---

## 🔍 Troubleshooting

### **Common Issues:**

1. **"Can't locate revision" Error:**
   ```bash
   python fix_alembic_version.py --list
   python fix_alembic_version.py --revision <valid_revision>
   ```

2. **Table Not Found After Removal:**
   ```bash
   python check_table.py --table <table_name>
   python check_table.py --pattern "<table_pattern>*"
   ```

3. **Migration State Corruption:**
   ```bash
   python scaffold_generator_v4/main.py fix-alembic
   python fix_alembic_version.py --current
   ```

### **Best Practices:**

- ✅ Always check current state before making changes
- ✅ Use pattern matching to find related tables
- ✅ Verify operations with detailed info checks
- ✅ Keep backups before major operations
- ✅ Use the utilities in combination for comprehensive verification

---

## 📝 Development Notes

### **File Structure:**
```
├── fix_alembic_version.py      # Alembic state management
├── check_table.py              # Table verification utility
└── DATABASE_UTILITIES_README.md # This documentation
```

### **Dependencies:**
- `asyncio` - For async database operations
- `sqlalchemy` - For database queries
- `argparse` - For command-line interface
- `fnmatch` - For pattern matching
- Project's `app.db.session` - Database connection

### **Future Enhancements:**
- [ ] Add table backup/restore functionality
- [ ] Include foreign key relationship checking
- [ ] Add database schema comparison tools
- [ ] Include migration rollback utilities
- [ ] Add performance monitoring for large tables

---

## 🤝 Contributing

When adding new utilities:

1. Follow the established pattern of comprehensive documentation
2. Include command-line argument support
3. Add proper error handling
4. Provide usage examples
5. Update this README with new functionality

---

*These utilities are part of the enhanced FastAPI PostgreSQL scaffold generator v4 system and are designed to work together for comprehensive database management and debugging.* 