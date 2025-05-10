# Error Log: Errors Encountered

This document lists all notable errors encountered during development, with relevant context and stack traces (if any).

---

## 1. `MissingGreenlet` Error with Alembic
- **Context:** Running Alembic migrations with async SQLAlchemy engine.
- **Stack Trace:**
    - `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here.`
- **When:** During `alembic revision --autogenerate` or `alembic upgrade head` with `DATABASE_URL=postgresql+asyncpg://...`

## 2. `NameError: name 'logging' is not defined`
- **Context:** Custom exception handler tried to use `logging.error()` without importing `logging`.
- **When:** Any API exception.

## 3. `TypeError: UserService.create_user() missing 1 required positional argument: 'password'`
- **Context:** Old endpoint signature didn't match updated service method.
- **When:** POST `/users` after updating service to require more arguments.

## 4. `You must set the config attribute from_attributes=True to use from_orm`
- **Context:** Pydantic v2+ requires `from_attributes=True` in schema `Config` for `from_orm()`.
- **When:** Returning models with `from_orm()` after DB save.

---

(Add more as you encounter them!)
