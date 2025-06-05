# FastAPI + PostgreSQL Async Boilerplate

A minimal, production-ready FastAPI boilerplate using async SQLAlchemy, PostgreSQL, and uv for fast dependency management. Designed for simplicity, portability, and quick project spin-up.

---

## Features

- Async SQLAlchemy ORM with PostgreSQL
- FastAPI app structure
- Environment variable support via `.env`
- Ready for Docker or local dev
- One-command setup and run using [uv](https://docs.astral.sh/uv/)
- **🧠 Smart Migration System** - Zero-downtime database migrations with automated model updates

---

## Quickstart

### 1. Install uv (if not already)

```bash
pip install uv
# or
brew install astral-sh/uv/uv
```

### 2. Clone this repo and enter the directory

```bash
git clone <your-repo-url>
cd <repo-dir>
```

### 3. Configure your database

Edit `.env` and set your `DATABASE_URL`:

```
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>
```

### 4. Ensure Python version is set

This project uses a `.python-version` file (e.g., `3.13`). uv will pick this up and use the correct Python version if available.

### 5. Install dependencies and create the lock file

```bash
uv sync
```

- This will create a `.venv` virtual environment (if not present) and a `uv.lock` file for reproducible installs.

### 6. Run the server using uv

```bash
uv run -- uvicorn main:app --reload
```

- Always use `uv run` to ensure you are using the correct virtual environment and dependencies managed by uv.

Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive API docs.

---

## Project Structure (per uv docs)

```
.
├── .venv/               # Virtual environment (auto-managed by uv)
├── .python-version      # Python version for the project
├── README.md            # This file
├── main.py              # FastAPI app entrypoint
├── pyproject.toml       # Project dependencies and metadata
├── uv.lock              # Lock file for reproducible installs
├── .env                 # Environment variables (DB URL, etc.)
├── scaffold_generator_v4/  # Advanced scaffold system
│   ├── main.py          # Main CLI interface
│   ├── migrations/      # Smart migration system
│   ├── core/           # Core validation and infrastructure
│   ├── templates/      # Code generation templates
│   ├── analyzers/      # Architecture analysis
│   └── testing/        # Test generation
└── app/                 # App code (models, schemas, crud, etc.)
    └── plugins/        # Generated plugin modules
```

- Do not manually activate the venv; always use `uv run`.
- Do not use `pip install` directly; use `uv sync` to manage dependencies.
- The `uv.lock` file ensures everyone gets the same dependency versions.

---

## 🧠 Smart Migration System

The FastAPI scaffold includes an enterprise-grade Smart Migration System that provides zero-downtime database schema evolution with automated model updates.

### Key Features

- **🔧 Automatic Model Updates**: Modifies SQLAlchemy models before generating migrations
- **⏱️ Zero-Downtime Strategies**: Plans migration execution to minimize service interruption
- **🛡️ Risk Assessment**: Identifies potential issues and suggests mitigation strategies
- **🔄 Rollback Planning**: Generates comprehensive rollback procedures
- **📊 Performance Analysis**: Estimates migration duration and resource impact
- **✅ Data Validation**: Ensures data integrity throughout the process

### Smart Migration Commands

#### Add Column to Existing Model

```bash
# Add a single column with type and default value
python -m scaffold_generator_v4.main smart-migration TestItem --changes add_column:priority:int:default=1

# Add column with multiple constraints
python -m scaffold_generator_v4.main smart-migration TestItem --changes add_column:status:str:default=pending:required

# Add multiple columns at once
python -m scaffold_generator_v4.main smart-migration TestItem --changes add_column:priority:int:default=1 add_column:category:str:nullable
```

#### Remove Column from Existing Model

```bash
# Remove a single column (with safety checks)
python -m scaffold_generator_v4.main smart-migration TestItem --changes drop_column:old_field

# Remove multiple columns
python -m scaffold_generator_v4.main smart-migration TestItem --changes drop_column:deprecated_field drop_column:unused_column
```

#### Modify Existing Columns

```bash
# Change column type
python -m scaffold_generator_v4.main smart-migration TestItem --changes modify_column:price:decimal:precision=10,scale=2

# Add constraints to existing column
python -m scaffold_generator_v4.main smart-migration TestItem --changes modify_column:email:str:unique=true

# Change column nullability
python -m scaffold_generator_v4.main smart-migration TestItem --changes modify_column:description:text:nullable=false
```

#### Advanced Migration Operations

```bash
# Add database index
python -m scaffold_generator_v4.main smart-migration TestItem --changes add_index:name,email:unique=true

# Add foreign key constraint
python -m scaffold_generator_v4.main smart-migration TestItem --changes add_constraint:fk_user_id:foreign_key:user.id

# Rename column (zero-downtime approach)
python -m scaffold_generator_v4.main smart-migration TestItem --changes rename_column:old_name:new_name
```

#### Auto-Apply Mode (CI/CD Integration)

```bash
# Automatically apply migration without prompts
python -m scaffold_generator_v4.main smart-migration TestItem --changes add_column:status:str:default=active --auto-apply
```

### Supported Column Types

| Type       | SQLAlchemy Mapping | Example Usage                         |
| ---------- | ------------------ | ------------------------------------- |
| `str`      | String(255)        | `name:str`                            |
| `text`     | Text               | `description:text`                    |
| `int`      | Integer            | `age:int`                             |
| `float`    | Float              | `price:float`                         |
| `bool`     | Boolean            | `is_active:bool`                      |
| `datetime` | DateTime           | `created_at:datetime`                 |
| `date`     | Date               | `birth_date:date`                     |
| `json`     | JSON               | `metadata:json`                       |
| `decimal`  | Decimal            | `amount:decimal:precision=10,scale=2` |

### Column Constraints

| Constraint      | Description           | Example                      |
| --------------- | --------------------- | ---------------------------- |
| `default=value` | Set default value     | `status:str:default=pending` |
| `nullable`      | Allow NULL values     | `description:text:nullable`  |
| `required`      | NOT NULL constraint   | `email:str:required`         |
| `unique`        | Unique constraint     | `username:str:unique`        |
| `index`         | Create database index | `email:str:index`            |

### Zero-Downtime Migration Process

The Smart Migration System follows industry best practices for zero-downtime migrations:

1. **📋 Analysis Phase**: Analyzes current schema and plans migration strategy
2. **🔧 Model Updates**: Automatically modifies SQLAlchemy model files
3. **📝 Migration Generation**: Creates Alembic migration with smart strategies
4. **🛡️ Risk Assessment**: Identifies potential issues and suggests solutions
5. **🔄 Rollback Planning**: Generates comprehensive rollback procedures
6. **✅ Validation**: Tests migration integrity before application
7. **🚀 Execution**: Applies migration with minimal downtime

### Smart Migration Architecture

The system employs several advanced patterns to ensure safe database evolution:

#### Expand-Contract Pattern

For breaking changes, the system uses a three-phase approach:

1. **Expand**: Add new schema elements alongside existing ones
2. **Migrate**: Update application code to use new schema
3. **Contract**: Remove old schema elements

#### Zero-Downtime Column Operations

**Adding Columns:**

```bash
# Phase 1: Add as nullable
python -m scaffold_generator_v4.main smart-migration Orders --changes add_column:total:decimal:nullable

# Phase 2: Populate with defaults (if needed)
# Application code updated to handle new column

# Phase 3: Make required (separate migration)
python -m scaffold_generator_v4.main smart-migration Orders --changes modify_column:total:decimal:required
```

**Removing Columns:**

```bash
# Phase 1: Stop using in application code
# Deploy application without column references

# Phase 2: Mark as deprecated
python -m scaffold_generator_v4.main smart-migration Orders --changes drop_column:old_field

# The system automatically implements safe removal strategy
```

**Column Type Changes:**

```bash
# Safe type expansion (e.g., varchar to text)
python -m scaffold_generator_v4.main smart-migration Products --changes modify_column:description:text

# Complex type changes use temporary column approach
python -m scaffold_generator_v4.main smart-migration Products --changes modify_column:price:decimal:precision=10,scale=2
```

### Advanced Migration Features

#### Index Management

```bash
# Create concurrent index (PostgreSQL)
python -m scaffold_generator_v4.main smart-migration Users --changes add_index:email:unique=true

# Composite indexes
python -m scaffold_generator_v4.main smart-migration Orders --changes add_index:user_id,status,created_at

# Remove unused indexes
python -m scaffold_generator_v4.main smart-migration Products --changes drop_index:old_category_idx
```

#### Constraint Operations

```bash
# Foreign key constraints
python -m scaffold_generator_v4.main smart-migration Orders --changes add_constraint:fk_user:foreign_key:users.id

# Check constraints
python -m scaffold_generator_v4.main smart-migration Products --changes add_constraint:positive_price:check:"price > 0"

# Remove constraints
python -m scaffold_generator_v4.main smart-migration Orders --changes drop_constraint:old_constraint_name
```

#### Relationship Management

```bash
# Rename columns with relationship preservation
python -m scaffold_generator_v4.main smart-migration Orders --changes rename_column:customer_id:user_id

# Update foreign key references
python -m scaffold_generator_v4.main smart-migration OrderItems --changes modify_column:order_id:int:fk=orders.id
```

### Risk Assessment & Safety

The Smart Migration System automatically evaluates migration risk:

#### 🟢 Low Risk Operations

- Adding nullable columns
- Creating indexes
- Adding constraints (with existing data validation)
- Renaming columns (with proper strategy)

#### 🟡 Medium Risk Operations

- Modifying column types (with data validation)
- Removing unused columns
- Changing constraints
- Large data migrations

#### 🔴 High Risk Operations

- Dropping tables
- Removing columns with data
- Type changes that may truncate data
- Operations affecting foreign key relationships

#### Safety Features

- **Pre-migration Validation**: Checks data compatibility
- **Rollback Planning**: Every migration includes rollback strategy
- **Performance Impact Analysis**: Estimates execution time and resource usage
- **Data Integrity Checks**: Validates schema consistency post-migration
- **Circuit Breakers**: Automatic rollback triggers for performance degradation

### Migration Monitoring & Observability

```bash
# Monitor migration progress
python -m scaffold_generator_v4.main smart-migration Users --changes add_column:score:int --monitor

# Performance benchmarking
python -m scaffold_generator_v4.main smart-migration Products --changes add_index:name --benchmark

# Dry run mode for testing
python -m scaffold_generator_v4.main smart-migration Orders --changes add_column:priority:int --dry-run
```

### Best Practices

1. **Always Test First**: Run migrations on staging before production
2. **Backup Strategy**: Ensure recent backups before major migrations
3. **Monitor Performance**: Watch key metrics during and after migration
4. **Coordinate Deployments**: Align database changes with application releases
5. **Use Feature Flags**: Control rollout of schema-dependent features
6. **Plan Rollbacks**: Have tested rollback procedures ready

### Example: Complete Feature Migration

Here's how to safely add a product rating system:

```bash
# Step 1: Add rating infrastructure
python -m scaffold_generator_v4.main smart-migration Products --changes \
  add_column:average_rating:decimal:precision=3,scale=2:default=0.0 \
  add_column:rating_count:int:default=0 \
  add_index:average_rating

# Step 2: Deploy application code that can handle the new columns

# Step 3: Create reviews table
python -m scaffold_generator_v4.main smart-migration Reviews --changes \
  create_table:reviews \
  add_column:product_id:int:fk=products.id \
  add_column:user_id:int:fk=users.id \
  add_column:rating:int:check="rating BETWEEN 1 AND 5" \
  add_index:product_id,user_id:unique=true

# Step 4: Enable rating features in application
# Use feature flags to gradually roll out rating functionality
```

For complete documentation on advanced features, see [SMART_MIGRATIONS_ADVANCED_FEATURES.md](./SMART_MIGRATIONS_ADVANCED_FEATURES.md).

### Migration Strategies by Operation

| Operation      | Strategy                                   | Downtime  | Risk Level |
| -------------- | ------------------------------------------ | --------- | ---------- |
| Add Column     | Add as nullable → Populate → Make required | Minimal   | Low        |
| Drop Column    | Stop using → Deploy → Drop column          | Minimal   | Medium     |
| Rename Column  | Add new → Copy data → Drop old             | Near-zero | Medium     |
| Add Index      | Create concurrently (PostgreSQL)           | None      | Low        |
| Add Constraint | Add as NOT VALID → Validate                | Minimal   | Medium     |

### Example Migration Flow

```bash
# 1. Start with a basic model
python -m scaffold_generator_v4.main add Product name:str price:float

# 2. Add priority column with smart migration
python -m scaffold_generator_v4.main smart-migration Product --changes add_column:priority:int:default=1

# 3. Add category and status columns
python -m scaffold_generator_v4.main smart-migration Product --changes \
  add_column:category:str:default=general \
  add_column:status:str:default=active

# 4. Remove deprecated field
python -m scaffold_generator_v4.main smart-migration Product --changes drop_column:deprecated_field

# 5. Add database performance optimizations
python -m scaffold_generator_v4.main smart-migration Product --changes \
  add_index:category,status:composite=true \
  add_index:created_at:btree=true
```

### Enterprise Features

#### Blue-Green Deployments

```bash
# Plan migration for blue-green deployment
python -m scaffold_generator_v4.main smart-migration Product --changes add_column:version:int --strategy=blue-green
```

#### Canary Releases

```bash
# Gradual rollout with canary strategy
python -m scaffold_generator_v4.main smart-migration Product --changes modify_column:price:decimal --strategy=canary --rollout=10%
```

#### Data Validation & Integrity

```bash
# Migration with extensive data validation
python -m scaffold_generator_v4.main smart-migration Product --changes add_column:checksum:str --validate-data --backup-first
```

---

## API Endpoints

- `GET /users` — List all users
- `POST /users` — Create a new user (JSON body: `{ "name": ..., "email": ... }`)

---

## Troubleshooting

- **DB Connection Errors:**
  - Ensure PostgreSQL is running and your `DATABASE_URL` is correct.
  - The URL must start with `postgresql+asyncpg://` for async support.
- **Port in use:**
  - Free the port (e.g., `killport 8000` or `lsof -i :8000`)
- **Dependencies:**
  - Always use `uv sync` after editing `pyproject.toml`.

## Create and Apply Migrations

You can run Alembic migrations in two ways:

### 1. **Manually (without .sh file)**

- Ensure your `.env` uses a sync driver (e.g., `postgresql://...`)
- Confirm `sqlalchemy.url` in `alembic.ini` is set to your sync database URL
- Create a migration:
  ```bash
  alembic revision --autogenerate -m "Describe your change"
  ```
- Apply migrations:
  ```bash
  alembic upgrade head
  ```

### 2. **With the provided migration script (`alembic_migrate.sh`)**

- This script reads your `.env`, dynamically patches `alembic.ini` with the correct sync URL (even if your `.env` uses async for FastAPI), and runs migrations automatically.
- To use:
  ```bash
  ./alembic_migrate.sh
  ```
- The script will:
  - Load `.env`
  - Convert any async driver to sync for Alembic
  - Patch `alembic.ini`'s `sqlalchemy.url`
  - Run `alembic upgrade head`

---

**Note:** For async FastAPI projects, always run migrations with the sync driver. The script ensures you never accidentally use the async driver for Alembic.

---

### 3. **Automated in setup.sh**

- If you run `setup.sh`, it will automatically run Alembic migrations (if the migration script is present) as part of the setup process.

---

## Boilerplate Usage

- Fork or copy this repo for your own projects.
- Add your own models, endpoints, or business logic as needed.

---

### Scaffold Model

- Use the `scaffold_model.py` script to add or remove models, endpoints, and related files.

#### Add a model

```bash
uv run scaffold_model.py add

uv run alembic revision --autogenerate -m "add tag model" && uv run alembic upgrade head
```

This will scaffold the model and update your database schema to include the new table.

#### Remove a model

```bash
uv run scaffold_model.py remove

uv run alembic revision --autogenerate -m "remove tag model" && uv run alembic upgrade head
```

This will remove the model and update your database schema to drop the corresponding table.

## Credits

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [uv](https://docs.astral.sh/uv/)
- [asyncpg](https://magicstack.github.io/asyncpg/)
- [python-dotenv](https://saurabh-kumar.com/python-dotenv/)
