# Alembic Migration Errors and Fixes

This file documents common errors encountered during Alembic migrations in this project, along with their solutions and best practices for robust migration management.

---

## 1. `NoSuchTableError: users`
**Error:**
```
sqlalchemy.exc.NoSuchTableError: users
```
**Cause:** Attempting to inspect or drop indexes on a table that doesn't exist.
**Fix:**
- Always check if the table exists before trying to inspect or drop its indexes in migration scripts:
  ```python
  table_names = inspector.get_table_names()
  if 'users' in table_names:
      indexes = [ix['name'] for ix in inspector.get_indexes('users')]
      # ...
  ```

---

## 2. `ModuleNotFoundError: No module named 'psycopg2'`
**Error:**
```
ModuleNotFoundError: No module named 'psycopg2'
```
**Cause:** Alembic requires a sync PostgreSQL driver (psycopg2) for migrations.
**Fix:**
- Install it:
  ```sh
  uv pip install psycopg2-binary
  # or
  pip install psycopg2-binary
  ```

---

## 3. `ValidationError: Extra inputs are not permitted`
**Error:**
```
ValidationError: 1 validation error for Settings
database_url_without_async
  Extra inputs are not permitted
```
**Cause:** Your `.env` has variables not declared in your Pydantic `Settings` class.
**Fix:**
- Add the missing field to your `Settings` class:
  ```python
  class Settings(BaseSettings):
      database_url: str
      jwt_secret_token: str
      database_url_without_async: str
  ```

---

## 4. Alembic Autogenerate Not Detecting Models
**Symptom:** Alembic does not detect new tables/models during `alembic revision --autogenerate`.
**Cause:** Models are not imported into the Base metadata before Alembic runs.
**Fix:**
- In `app/db/base.py`, import all models so Alembic can see them:
  ```python
  from sqlalchemy.orm import declarative_base
  Base = declarative_base()
  from app.db.models.user import User
  ```

---

## 5. General Alembic + uv Workflow
- Always use `uv run alembic ...` to ensure the correct environment.
- Never use `Base.metadata.create_all()` in app startup for production. Use migrations only.

---

For more, see [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/) and [uv documentation](https://docs.astral.sh/uv/guides/projects/).
