# Error Log: Solutions & Fixes

This document describes how each error in `error_encounter.md` was solved. Each entry should reference the error number for clarity.

---

## 1. `MissingGreenlet` Error with Alembic
**Solution:**
- Refactored `app/db/session.py` to only import async SQLAlchemy engine if `DATABASE_URL` starts with `postgresql+asyncpg`. Alembic always uses sync driver (`postgresql://`).
- Updated `.env` and `alembic.ini` handling. Added migration script to patch `alembic.ini` dynamically.

## 2. `NameError: name 'logging' is not defined`
**Solution:**
- Added `import logging` to `app/core/exception_handlers.py`.

## 3. `TypeError: UserService.create_user() missing 1 required positional argument: 'password'`
**Solution:**
- Updated all endpoints to pass all required arguments to `UserService.create_user`.

## 4. `You must set the config attribute from_attributes=True to use from_orm`
**Solution:**
- Added `from_attributes = True` to the `Config` class of all Pydantic schemas using `from_orm`.

---

(Add more as you solve them!)
