# Scaffold v4 Commands Guide

## 🎯 VERIFIED WORKING COMMANDS

**These commands have been tested and confirmed working:**

### ✅ Main Command - Add New Model/Plugin

**From Project Root Directory:**

```bash
python scaffold_generator_v4/main.py add <ModelName> <field1:type> <field2:type> [options]
```

### 🔥 Working Examples

#### **Basic Model Creation:**

```bash
# Simple Customer model
python scaffold_generator_v4/main.py add Customer name:str email:str phone:str
```

#### **Advanced Model with All Features:**

```bash
# Product model with constraints, tasks, and bulk operations
python scaffold_generator_v4/main.py add Product name:str price:float:gt=0 category:str:choices=electronics,clothing,books description:str:optional stock:int:ge=0 is_active:bool --with-tasks --with-bulk
```

#### **Field Type Variations:**

```bash
# All field constraint types
python scaffold_generator_v4/main.py add Order customer_name:str customer_email:email total_amount:float:gt=0 status:str:choices=pending,processing,shipped,delivered,cancelled order_date:datetime shipping_address:str notes:str:optional discount:float:ge=0 is_priority:bool
```

### 📋 Available Field Constraints

| Constraint      | Example                              | Description                |
| --------------- | ------------------------------------ | -------------------------- |
| `gt=N`          | `price:float:gt=0`                   | Greater than N             |
| `ge=N`          | `stock:int:ge=0`                     | Greater than or equal to N |
| `lt=N`          | `limit:int:lt=100`                   | Less than N                |
| `le=N`          | `score:int:le=100`                   | Less than or equal to N    |
| `choices=a,b,c` | `status:str:choices=active,inactive` | Limited choice options     |
| `optional`      | `description:str:optional`           | Nullable field             |
| `email`         | `contact:email`                      | Email validation           |
| `date`          | `birth_date:date`                    | Date field                 |
| `datetime`      | `created_at:datetime`                | Datetime field             |

### 🚀 Command Options

| Option         | Description                                         | Example        |
| -------------- | --------------------------------------------------- | -------------- |
| `--with-tasks` | Add background task support                         | `--with-tasks` |
| `--with-bulk`  | Add bulk operations (create/update/delete multiple) | `--with-bulk`  |
| `--with-auth`  | Enable enterprise authentication                    | `--with-auth`  |

### 📋 Other Commands

```bash
# List all plugins
python scaffold_generator_v4/main.py list

# Check system health
python scaffold_generator_v4/main.py infra-check

# Test model (dry run)
python scaffold_generator_v4/main.py test ModelName field1:type field2:type

# Fix migration issues
python scaffold_generator_v4/main.py auto-fix
```

### 🎯 Success Results

✅ **Auto-Fix System**: 7/8 strategies working (87.5% success rate)  
✅ **Migration Generation**: Successfully creates and applies migrations  
✅ **Plugin Creation**: All files generated correctly (models, routes, schemas, services, tasks)  
✅ **Database Integration**: Tables created with proper constraints  
✅ **FastAPI Integration**: Routes automatically registered with timeout support

### 📝 Quick Reference

**Most Common Command:**

```bash
python scaffold_generator_v4/main.py add Product name:str price:float:gt=0 category:str:choices=electronics,clothing,books description:str:optional stock:int:ge=0 is_active:bool --with-tasks --with-bulk
```

**Generated API Endpoints (example for Product):**

- `POST /products/` - Create product
- `GET /products/` - List products (with pagination)
- `GET /products/{id}` - Get specific product
- `PUT /products/{id}` - Update product
- `DELETE /products/{id}` - Delete product
- `GET /products/search/` - Search products

---

## Overview

Scaffold v4 is an enhanced FastAPI plugin generator with comprehensive auto-fix capabilities, advanced field support, and enterprise features. This guide covers all available commands with detailed usage instructions.

## Table of Contents

1. [Basic Commands](#basic-commands)
2. [Migration Commands](#migration-commands)
3. [Health & Maintenance Commands](#health--maintenance-commands)
4. [Authentication Commands](#authentication-commands)
5. [Advanced Commands](#advanced-commands)
6. [Testing Commands](#testing-commands)
7. [Field Types & Constraints](#field-types--constraints)
8. [Best Practices](#best-practices)

---

## Basic Commands

### `add` - Generate New Plugin

Creates a new plugin with the specified model and fields.

**Syntax:**

```bash
python main.py add <ModelName> <field1:type> <field2:type> [options]
```

**Basic Examples:**

```bash
# Simple model
python main.py add User name:str email:email age:int

# Model with constraints
python main.py add Product name:str price:float:gt=0 status:str:choices=active,inactive,discontinued

# Complex model with all features
python main.py add Order customer_name:str customer_email:email total_amount:float:gt=0 status:str:choices=pending,processing,shipped,delivered,cancelled order_date:datetime shipping_address:str notes:str:optional --with-tasks --with-bulk
```

**Options:**

- `--with-tasks` - Include background task support
- `--with-bulk` - Include bulk operations (create/update/delete multiple)
- `--with-auth` - Enable enterprise authentication
- `--auth-ownership` - Enable owner-based access control
- `--auth-audit` - Enable audit logging (default: true)
- `--auth-soft-delete` - Enable soft delete functionality
- `--auth-versioning` - Enable entity versioning
- `--auth-roles` - Required roles (comma-separated)
- `--auth-rate-limit` - Enable rate limiting (default: true)

**Authentication Examples:**

```bash
# Basic authentication
python main.py add Document title:str content:str --with-auth

# Full enterprise authentication
python main.py add Customer name:str email:email --with-auth --auth-ownership --auth-audit --auth-soft-delete --auth-roles=admin,manager

# With versioning and rate limiting
python main.py add Contract title:str amount:float --with-auth --auth-versioning --auth-rate-limit
```

**Generated Files:**

- `app/plugins/{model_name}_plugin/__init__.py`
- `app/plugins/{model_name}_plugin/models.py`
- `app/plugins/{model_name}_plugin/schemas.py`
- `app/plugins/{model_name}_plugin/routes.py`
- `app/plugins/{model_name}_plugin/services.py`
- `app/plugins/{model_name}_plugin/tasks.py` (if `--with-tasks`)

---

### `list` - List All Plugins

Shows all existing plugins in the system.

**Syntax:**

```bash
python main.py list
```

**Example Output:**

```
📋 Existing Plugins:
=====================================
✅ book_plugin (Book)
   📁 Location: app/plugins/book_plugin
   📝 Model: Book
   🔧 Features: crud, search, tasks

✅ order_plugin (Order)
   📁 Location: app/plugins/order_plugin
   📝 Model: Order
   🔧 Features: crud, search, tasks, bulk

✅ user_plugin (User)
   📁 Location: app/plugins/user_plugin
   📝 Model: User
   🔧 Features: crud, search, auth, ownership
```

---

### `remove` - Remove Plugin

Removes a plugin's code files (keeps database).

**Syntax:**

```bash
python main.py remove <ModelName>
```

**Examples:**

```bash
# Remove plugin files only
python main.py remove Product

# Confirmation will be requested
```

**What it does:**

- Removes plugin directory and all files
- Keeps database tables and migrations
- Safe operation (no data loss)

---

### `cleanup` - Complete Plugin Removal

Removes plugin code and optionally cleans up database.

**Syntax:**

```bash
python main.py cleanup <ModelName> [options]
```

**Options:**

- `--force` - Skip confirmation prompts
- `--keep-migrations` - Keep migration files (only remove plugin code)

**Examples:**

```bash
# Complete cleanup with confirmation
python main.py cleanup Product

# Force cleanup without prompts
python main.py cleanup Product --force

# Remove code but keep migrations
python main.py cleanup Product --keep-migrations --force
```

**What it does:**

- Removes plugin directory and all files
- Optionally removes database table
- Optionally removes migration files
- Creates backup before destructive operations

---

## Migration Commands

### `auto-fix` - Comprehensive Migration Fix

Automatically fixes all common migration issues with 8 comprehensive strategies.

**Syntax:**

```bash
python main.py auto-fix [options]
```

**Options:**

- `--force` - Enable aggressive fixes including emergency reset
- `--backup` - Create backup before fixes (default: true)

**Examples:**

```bash
# Standard auto-fix (safe mode)
python main.py auto-fix

# Aggressive fixes with emergency reset
python main.py auto-fix --force

# Auto-fix with explicit backup
python main.py auto-fix --backup
```

**What it fixes:**

- ✅ Multiple migration heads
- ✅ Organizations FK constraint errors
- ✅ Database state corruption
- ✅ Protected table modification attempts
- ✅ Orphaned migration files
- ✅ Malformed constraint definitions
- ✅ Migration sequence issues
- ✅ Invalid foreign key constraints

**Example Output:**

```
🔧 Auto-fixing All Migration Issues
==================================================

📍 Strategy 1: Checking for multiple heads...
   Found 3 heads: [abc123, def456, ghi789]
   Successfully merged 3 heads
✅ Multiple heads resolved

📍 Strategy 2: Cleaning up invalid migration files...
   Fixed: 20231210_create_order.py
   Fixed: 20231211_add_product.py
✅ Invalid migrations cleaned up

📍 Strategy 3: Fixing database state...
✅ Database state fixed

... (continues for all 8 strategies)

🎯 Auto-fix Results: 7/8 strategies successful
✅ Auto-fix completed successfully!
```

---

### `migration-health` - Quick Migration Check

Performs a quick health check of the migration system.

**Syntax:**

```bash
python main.py migration-health
```

**Example Output:**

```
🏥 Migration System Health Check
========================================
✅ Migration system is healthy
📍 Current revision: abc123def456
```

---

### `fix-alembic` - Legacy Alembic Fix

Fixes corrupted Alembic state (legacy command, use `auto-fix` instead).

**Syntax:**

```bash
python main.py fix-alembic
```

---

## Health & Maintenance Commands

### `health-check` - Comprehensive System Check

Runs a complete system health check including infrastructure, plugins, and dependencies.

**Syntax:**

```bash
python main.py health-check
```

**Example Output:**

```
🏥 System Health Check
======================
✅ FastAPI framework detected
✅ SQLAlchemy ORM available
✅ Alembic migrations configured
✅ Database connection successful
✅ Plugin system operational
✅ Redis cache available
✅ All dependencies satisfied

Overall Status: ✅ HEALTHY
```

---

### `infra-check` - Infrastructure Compatibility

Checks infrastructure compatibility for plugin generation.

**Syntax:**

```bash
python main.py infra-check
```

**Example Output:**

```
🔍 Infrastructure Compatibility Check
=====================================
✅ FastAPI: 0.104.1 (Compatible)
✅ SQLAlchemy: 2.0.23 (Compatible)
✅ Alembic: 1.12.1 (Compatible)
✅ Pydantic: 2.5.0 (Compatible)
✅ Database: PostgreSQL 15.5 (Compatible)
✅ Python: 3.11.6 (Compatible)

Infrastructure Status: ✅ COMPATIBLE
```

---

### `test-enhanced` - Test Enhanced Features

Tests the enhanced generator capabilities including field validation and auto-fix.

**Syntax:**

```bash
python main.py test-enhanced
```

**Example Output:**

```
🧪 Testing Enhanced Scaffold Generator v4
==================================================

🔍 Test 1: Migration Health Check
✅ Migration system is healthy

🔍 Test 2: Field Validation Tests
✅ Validated 7 test fields successfully
✅ Choices constraint validated: status
✅ Optional field detected: notes

🔍 Test 3: Import Generation
✅ Literal type import detected for choices
✅ EmailStr import detected

🎯 Enhanced Generator Test Complete
📊 Migration system health: ✅ OK
```

---

### `fix-plugins` - Fix Plugin Issues

Fixes common plugin-related issues.

**Syntax:**

```bash
python main.py fix-plugins
```

---

## Authentication Commands

### `add-auth` - Add Authentication to Existing Plugin

Adds authentication features to an existing plugin.

**Syntax:**

```bash
python main.py add-auth <ModelName> [options]
```

**Options:**

- `--ownership` - Enable owner-based access control
- `--audit` - Enable audit logging (default: true)
- `--soft-delete` - Enable soft delete
- `--roles` - Required roles (comma-separated)

**Examples:**

```bash
# Basic authentication
python main.py add-auth Product

# Full authentication features
python main.py add-auth Product --ownership --audit --soft-delete --roles=admin,manager
```

---

### `auth-check` - Check Authentication System

Validates the authentication system compatibility.

**Syntax:**

```bash
python main.py auth-check
```

---

### `auth-preset` - Generate with Authentication Presets

Generates a new plugin with predefined authentication levels.

**Syntax:**

```bash
python main.py auth-preset <preset> <ModelName> <fields> [options]
```

**Presets:**

- `basic` - Basic authentication only
- `secure` - Enhanced security features
- `enterprise` - Full enterprise authentication

**Examples:**

```bash
# Basic preset
python main.py auth-preset basic Document title:str content:str

# Secure preset
python main.py auth-preset secure Customer name:str email:email

# Enterprise preset
python main.py auth-preset enterprise Contract title:str amount:float --with-tasks --with-bulk
```

---

## Advanced Commands

### `analyze` - Architecture Analysis

Analyzes project architecture and generates reports.

**Syntax:**

```bash
python main.py analyze [options]
```

**Options:**

- `--output` - Output file for analysis report
- `--format` - Output format: `text` or `json` (default: text)

**Examples:**

```bash
# Text analysis to console
python main.py analyze

# JSON report to file
python main.py analyze --output=analysis.json --format=json

# Text report to file
python main.py analyze --output=analysis.txt --format=text
```

---

### `generate-tests` - Generate Test Suite

Generates comprehensive test suites for models.

**Syntax:**

```bash
python main.py generate-tests <ModelName> [options]
```

**Options:**

- `--types` - Test types: `unit`, `integration`, `e2e`, `load` (default: unit, integration)
- `--output-dir` - Output directory for tests
- `--with-auth` - Include authentication in tests

**Examples:**

```bash
# Basic test generation
python main.py generate-tests Product

# All test types
python main.py generate-tests Product --types unit integration e2e load

# With authentication tests
python main.py generate-tests Product --types unit integration --with-auth

# Custom output directory
python main.py generate-tests Product --output-dir=custom_tests/
```

---

### `smart-migration` - Zero-Downtime Migrations

Generates smart migrations with zero-downtime strategies.

**Syntax:**

```bash
python main.py smart-migration <ModelName> [options]
```

**Options:**

- `--changes` - Specific changes to apply
- `--auto-apply` - Automatically apply without prompting

**Examples:**

```bash
# Smart migration for model
python main.py smart-migration Product

# Specific changes
python main.py smart-migration Product --changes add_column:status:str:default=active drop_column:old_field

# Auto-apply changes
python main.py smart-migration Product --auto-apply
```

---

## Testing Commands

### `test` - Test Plugin Generation

Tests plugin generation without creating actual files.

**Syntax:**

```bash
python main.py test <ModelName> <fields>
```

**Examples:**

```bash
# Test simple model
python main.py test Product name:str price:float

# Test complex model
python main.py test Order customer:str total:float:gt=0 status:str:choices=pending,complete
```

---

## Field Types & Constraints

### Basic Types

| Type       | Description            | Example               |
| ---------- | ---------------------- | --------------------- |
| `str`      | String field           | `name:str`            |
| `int`      | Integer field          | `age:int`             |
| `float`    | Float field            | `price:float`         |
| `bool`     | Boolean field          | `active:bool`         |
| `datetime` | DateTime field         | `created_at:datetime` |
| `date`     | Date field             | `birth_date:date`     |
| `email`    | Email field (EmailStr) | `email:email`         |

### Constraints

| Constraint      | Description                   | Example                                      |
| --------------- | ----------------------------- | -------------------------------------------- |
| `gt=N`          | Greater than N                | `price:float:gt=0`                           |
| `ge=N`          | Greater than or equal to N    | `age:int:ge=18`                              |
| `lt=N`          | Less than N                   | `discount:float:lt=1.0`                      |
| `le=N`          | Less than or equal to N       | `score:int:le=100`                           |
| `min_length=N`  | Minimum string length         | `name:str:min_length=2`                      |
| `max_length=N`  | Maximum string length         | `title:str:max_length=100`                   |
| `choices=a,b,c` | String choices (Literal type) | `status:str:choices=active,inactive,pending` |
| `optional`      | Nullable field                | `notes:str:optional`                         |

### Advanced Constraints

```bash
# Multiple constraints
python main.py add Product name:str:min_length=2:max_length=50 price:float:gt=0:le=10000

# Integer choices
python main.py add Rating score:int:choices=1,2,3,4,5 comment:str:optional

# Complex example
python main.py add User name:str:min_length=2:max_length=50 email:email age:int:ge=18:le=120 status:str:choices=active,inactive,pending bio:str:optional
```

---

## Best Practices

### 1. Model Generation Workflow

```bash
# Step 1: Check system health
python main.py migration-health

# Step 2: Auto-fix if needed
python main.py auto-fix

# Step 3: Generate model
python main.py add MyModel field1:type field2:type

# Step 4: Verify creation
python main.py list
```

### 2. Field Design Guidelines

**Good:**

```bash
# Clear, descriptive names with appropriate constraints
python main.py add Product name:str:min_length=1:max_length=100 price:float:gt=0 status:str:choices=active,inactive,discontinued description:str:optional
```

**Avoid:**

```bash
# Vague names, missing constraints
python main.py add Product n:str p:float s:str d:str
```

### 3. Authentication Strategy

**For Public APIs:**

```bash
python main.py add PublicData name:str value:str
```

**For Internal APIs:**

```bash
python main.py add InternalData name:str value:str --with-auth --auth-roles=staff
```

**For Enterprise:**

```bash
python main.py add EnterpriseData name:str value:str --with-auth --auth-ownership --auth-audit --auth-versioning --auth-soft-delete
```

### 4. Feature Selection

**Simple CRUD:**

```bash
python main.py add SimpleModel name:str
```

**With Background Tasks:**

```bash
python main.py add ProcessingModel data:str --with-tasks
```

**With Bulk Operations:**

```bash
python main.py add BulkModel items:str --with-bulk
```

**Full Featured:**

```bash
python main.py add FullModel name:str status:str:choices=active,inactive --with-tasks --with-bulk --with-auth
```

### 5. Maintenance Schedule

**Daily:**

```bash
python main.py migration-health
```

**Weekly:**

```bash
python main.py health-check
python main.py test-enhanced
```

**Before Major Changes:**

```bash
python main.py auto-fix
python main.py infra-check
```

### 6. Troubleshooting Workflow

**If model generation fails:**

```bash
# Step 1: Auto-fix
python main.py auto-fix

# Step 2: If still failing, force mode
python main.py auto-fix --force

# Step 3: Check infrastructure
python main.py infra-check

# Step 4: Try again
python main.py add MyModel field:type
```

### 7. Testing Strategy

**Before Production:**

```bash
# Generate test model
python main.py test TestModel name:str

# Run comprehensive tests
python main.py test-enhanced

# Generate actual test files
python main.py generate-tests MyModel --types unit integration
```

---

## Common Use Cases

### 1. E-commerce Product Catalog

```bash
python main.py add Product name:str:min_length=1:max_length=200 description:str:optional price:float:gt=0 category:str:choices=electronics,clothing,books,home sku:str:min_length=3:max_length=50 in_stock:bool --with-tasks --with-bulk
```

### 2. User Management System

```bash
python main.py add User username:str:min_length=3:max_length=50 email:email full_name:str:max_length=100 role:str:choices=admin,user,moderator is_active:bool:default=true last_login:datetime:optional --with-auth --auth-ownership --auth-audit
```

### 3. Order Management

```bash
python main.py add Order order_number:str:min_length=5:max_length=20 customer_email:email total_amount:float:gt=0 status:str:choices=pending,processing,shipped,delivered,cancelled order_date:datetime shipping_address:str notes:str:optional --with-tasks --with-bulk --with-auth
```

### 4. Content Management

```bash
python main.py add Article title:str:min_length=5:max_length=200 content:str slug:str:max_length=100 status:str:choices=draft,published,archived author:str published_at:datetime:optional tags:str:optional --with-auth --auth-ownership --auth-versioning
```

### 5. Inventory System

```bash
python main.py add InventoryItem name:str:max_length=100 sku:str:max_length=50 quantity:int:ge=0 unit_price:float:gt=0 category:str:choices=raw_material,finished_good,work_in_progress location:str:optional reorder_level:int:ge=0 --with-tasks --with-bulk
```

---

## Command Reference Quick Guide

| Command            | Purpose                   | Usage                                |
| ------------------ | ------------------------- | ------------------------------------ |
| `add`              | Create new plugin         | `add Model field:type`               |
| `list`             | Show all plugins          | `list`                               |
| `remove`           | Remove plugin code        | `remove Model`                       |
| `cleanup`          | Complete removal          | `cleanup Model --force`              |
| `auto-fix`         | Fix all migration issues  | `auto-fix [--force]`                 |
| `migration-health` | Quick migration check     | `migration-health`                   |
| `health-check`     | Full system check         | `health-check`                       |
| `infra-check`      | Infrastructure check      | `infra-check`                        |
| `test-enhanced`    | Test enhanced features    | `test-enhanced`                      |
| `add-auth`         | Add authentication        | `add-auth Model`                     |
| `auth-preset`      | Generate with auth preset | `auth-preset basic Model field:type` |
| `analyze`          | Architecture analysis     | `analyze [--output file]`            |
| `generate-tests`   | Generate test suite       | `generate-tests Model`               |
| `smart-migration`  | Zero-downtime migration   | `smart-migration Model`              |
| `test`             | Test plugin generation    | `test Model field:type`              |

---

This comprehensive guide covers all Scaffold v4 commands. For the most up-to-date help, run:

```bash
python main.py --help
python main.py <command> --help
```
