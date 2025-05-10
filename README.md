# FastAPI + PostgreSQL Async Boilerplate

A minimal, production-ready FastAPI boilerplate using async SQLAlchemy, PostgreSQL, and uv for fast dependency management. Designed for simplicity, portability, and quick project spin-up.

---

## Features

- Async SQLAlchemy ORM with PostgreSQL
- FastAPI app structure
- Environment variable support via `.env`
- Ready for Docker or local dev
- One-command setup and run using [uv](https://docs.astral.sh/uv/)

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
└── app/                 # App code (models, schemas, crud, etc.)
```

- Do not manually activate the venv; always use `uv run`.
- Do not use `pip install` directly; use `uv sync` to manage dependencies.
- The `uv.lock` file ensures everyone gets the same dependency versions.

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


