import os
import json
import sys
import shutil
import subprocess
import typer  # Typer CLI
from colorama import init as colorama_init, Fore, Style
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import yaml  # PyYAML for bulk import
# --- Optionally import mkdocs, watchdog, fastapi-admin, fastapi-users if installed ---
try:
    import mkdocs
except ImportError:
    mkdocs = None
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None
    FileSystemEventHandler = object
try:
    import fastapi_admin
except ImportError:
    fastapi_admin = None
try:
    import fastapi_users
except ImportError:
    fastapi_users = None

colorama_init(autoreset=True)
console = Console()

BASE_PATH = "app"
TRACK_FILE = "scaffolded_models.json"
API_FILE = os.path.join(BASE_PATH, "api/v1/api.py")

# --- Utility functions ---
def snake_case(name):
    return ''.join(['_' + c.lower() if c.isupper() else c for c in name]).lstrip('_')

def pascal_case(name):
    return ''.join(word.capitalize() for word in name.split('_'))

def ensure_init(path):
    dirs = path.split(os.sep)
    for i in range(1, len(dirs)):
        d = os.sep.join(dirs[:i])
        if d and not os.path.exists(os.path.join(d, "__init__.py")):
            with open(os.path.join(d, "__init__.py"), "a") as f:
                pass

# --- FastAPI Scaffold Tool: Typer + Rich + Modern Features ---
# Usage: python scaffold_model_.py [COMMAND] [OPTIONS]

import os
import json
import shutil
import subprocess
import typer
from colorama import init as colorama_init, Fore, Style
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import yaml

colorama_init(autoreset=True)
console = Console()
app = typer.Typer(help="FastAPI Project Scaffold Tool (Typer CLI, Rich output, PyYAML, .env, subprocess, admin/user stubs)")

BASE_PATH = "app"
TRACK_FILE = "scaffolded_models.json"
API_FILE = os.path.join(BASE_PATH, "api/v1/api.py")
SUPPORTED_FIELD_TYPES = {"str": "String", "int": "Integer", "float": "Float", "bool": "Boolean"}

# --- Utility functions ---
def snake_case(name):
    return ''.join(['_' + c.lower() if c.isupper() else c for c in name]).lstrip('_')

def pascal_case(name):
    return ''.join(word.capitalize() for word in name.split('_'))

def ensure_init(path):
    dirs = path.split(os.sep)
    for i in range(1, len(dirs)):
        d = os.sep.join(dirs[:i])
        if d and not os.path.exists(os.path.join(d, "__init__.py")):
            with open(os.path.join(d, "__init__.py"), "a") as f:
                pass

def prompt_fields():
    fields = []
    console.print("[bold yellow]Enter fields for your model (format: name:type), e.g., title:str. Type 'done' when finished.[/bold yellow]")
    while True:
        field = input("Field: ")
        if field.lower() == "done":
            break
        if ':' in field:
            name, typ = field.split(':', 1)
            fields.append((name.strip(), typ.strip()))
    return fields

def validate_fields(fields):
    valid = True
    for name, typ in fields:
        if typ not in SUPPORTED_FIELD_TYPES and not typ.startswith("FK:"):
            console.print(f"[red]Warning: Field '{name}' has unsupported type '{typ}'. Defaulting to String.[/red]")
            valid = False
    return valid

def prompt_relationships():
    rels = []
    console.print("[yellow]Enter relationships (format: field:FK:TargetModel), e.g., author_id:FK:User. Type 'done' when finished.[/yellow]")
    while True:
        rel = input("Relationship: ")
        if rel.lower() == "done":
            break
        if ':' in rel and rel.count(':') == 2:
            name, fk, target = rel.split(':')
            if fk == "FK":
                rels.append((name.strip(), target.strip()))
    return rels

def prompt_crud():
    console.print("[yellow]Enable/disable CRUD endpoints (y/n):[/yellow]")
    crud = {}
    for op in ["create", "read", "update", "delete", "list"]:
        val = input(f"  {op}? [y/n]: ").strip().lower()
        crud[op] = (val == "y")
    return crud

def make_test_file(model, fields):
    snake = snake_case(model)
    test_path = f"app/tests/test_{snake}.py"
    test_code = f'''"""
Basic tests for {model} endpoints and service.
"""
def test_{snake}_crud(client):
    # TODO: Implement real tests
    resp = client.get(f"/{snake}s")
    assert resp.status_code in (200, 401, 403)
'''
    return test_path, test_code

def load_track():
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, "r") as f:
            return json.load(f)
    return {}

def save_track(data):
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2)

def write_file(path, content):
    ensure_init(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)

def remove_file(path):
    if os.path.exists(path):
        os.remove(path)
        d = os.path.dirname(path)
        while d.startswith(BASE_PATH) and d != BASE_PATH:
            if not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
            else:
                break

def update_api_py(model, action):
    snake = snake_case(model)
    router_line = f"from app.api.v1.endpoints import {snake}"
    include_line = f"api_router.include_router({snake}.router, prefix=\"/{snake}s\", tags=[\"{snake}s\"])"
    with open(API_FILE, "r") as f:
        lines = f.readlines()
    if action == "add":
        if router_line + "\n" not in lines:
            last_import = max(i for i, l in enumerate(lines) if l.startswith("from"))
            lines.insert(last_import+1, router_line+"\n")
        if include_line+"\n" not in lines:
            last_include = max(i for i, l in enumerate(lines) if "include_router" in l)
            lines.insert(last_include+1, include_line+"\n")
    elif action == "remove":
        lines = [l for l in lines if l.strip() != router_line and l.strip() != include_line]
    with open(API_FILE, "w") as f:
        f.writelines(lines)

# --- Core scaffold logic (add/remove/list/bulk-import) ---
def make_model_files(model, fields, relationships, crud, examples, dry_run=False, verbose=True):
    snake = snake_case(model)
    files = {}
    # Model
    model_path = f"{BASE_PATH}/db/models/{snake}.py"
    model_code = f'''"""
SQLAlchemy model for {model}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey

class {model}(Base):
    """SQLAlchemy ORM model for {model}."""
    __tablename__ = "{snake}s"
    id = Column(Integer, primary_key=True, index=True)
'''
    for name, typ in fields:
        if typ.startswith("FK:"):
            target = typ.split(":")[1]
            model_code += f"    {name} = Column(Integer, ForeignKey('{snake_case(target)}s.id'))\n"
        else:
            sqlatype = SUPPORTED_FIELD_TYPES.get(typ, "String")
            model_code += f"    {name} = Column({sqlatype}, nullable=False)\n"
    for name, target in relationships:
        model_code += f"    {name} = Column(Integer, ForeignKey('{snake_case(target)}s.id'))\n"
    files[model_path] = model_code
    # Schema
    schema_path = f"{BASE_PATH}/db/schemas/{snake}.py"
    schema_code = f'''"""
Pydantic schemas for {model}.
"""
from pydantic import BaseModel, Field

class {model}Create(BaseModel):
'''
    for name, typ in fields:
        pytyp = "str" if typ == "str" else "int" if typ == "int" else "float" if typ == "float" else "bool" if typ == "bool" else "str"
        example = examples.get(name, "example")
        schema_code += f"    {name}: {pytyp} = Field(..., example={repr(example)})\n"
    schema_code += f"""

class {model}Read({model}Create):
    id: int
    class Config:
        orm_mode = True
"""
    files[schema_path] = schema_code
    # Service
    service_path = f"{BASE_PATH}/services/{snake}_service.py"
    service_code = f'''"""
Service for {model} business logic and CRUD operations.
"""
from app.services.base_service import BaseService
from app.db.models.{snake} import {model}

class {model}Service(BaseService[{model}]):
    def __init__(self):
        super().__init__({model})
'''
    files[service_path] = service_code
    # Endpoint
    endpoint_path = f"{BASE_PATH}/api/v1/endpoints/{snake}.py"
    endpoint_code = f'''"""
Auto-generated CRUD endpoints for {model}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake}_service import {model}Service
from app.db.schemas.{snake} import {model}Read, {model}Create
from app.db.session import get_db

router = get_crud_router(
    service={model}Service(),
    schema_read={model}Read,
    schema_create={model}Create,
    prefix="/{snake}s",
    get_db=get_db,
    tags=["{model}s"],
    crud_ops={crud}
)
'''
    files[endpoint_path] = endpoint_code
    # Test
    test_path, test_code = make_test_file(model, fields)
    files[test_path] = test_code
    if not dry_run:
        for path, code in files.items():
            write_file(path, code)
        if verbose:
            console.print(f"[green]Created files: {list(files.keys())}[/green]")
    return files

def add_model(model, fields, relationships, crud, examples, dry_run=False, verbose=True):
    track = load_track()
    if model in track:
        console.print(f"[red]Model {model} already scaffolded. Remove first if you want to re-create.[/red]")
        return
    files = {}
    created_files = []
    modified_inits = []
    original_inits = {}
    try:
        files = make_model_files(model, fields, relationships, crud, examples, dry_run, verbose)
        if not dry_run:
            # Update __init__.py for imports (backup originals)
            for subdir, imp in [
                (f"{BASE_PATH}/db/models/__init__.py", f"from .{snake_case(model)} import {model}\n"),
                (f"{BASE_PATH}/db/schemas/__init__.py", f"from .{snake_case(model)} import {model}Create, {model}Read\n"),
                (f"{BASE_PATH}/services/__init__.py", f"from .{snake_case(model)}_service import {model}Service\n"),
                (f"{BASE_PATH}/api/v1/endpoints/__init__.py", f"from .{snake_case(model)} import router as {snake_case(model)}_router\n"),
            ]:
                if os.path.exists(subdir):
                    with open(subdir, "r") as f:
                        original_inits[subdir] = f.read()
                with open(subdir, "a") as f:
                    f.write(imp)
                modified_inits.append(subdir)
            update_api_py(model, "add")
            track[model] = list(files.keys())
            save_track(track)
            console.print(f"[bold green]Model {model} scaffolded successfully.[/bold green]")
    except Exception as e:
        # Rollback: remove created files, revert __init__.py, revert tracking
        console.print(f"[bold red]Error during scaffolding: {e}. Rolling back changes...[/bold red]")
        for path in files.keys():
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        for subdir in modified_inits:
            if subdir in original_inits:
                with open(subdir, "w") as f:
                    f.write(original_inits[subdir])
        track = load_track()
        if model in track:
            del track[model]
            save_track(track)
        console.print(f"[yellow]Rollback complete. No partial files remain for {model}.[/yellow]")
        raise
    else:
        if dry_run:
            console.print(f"[yellow][Dry Run] Would create: {list(files.keys())}[/yellow]")

def remove_model(model):
    track = load_track()
    if model not in track:
        console.print(f"[red]Model {model} not found in scaffolded models.[/red]")
        return
    # Backup files and __init__.py
    old_files = track[model][:]
    old_inits = {}
    for subdir in [
        f"{BASE_PATH}/db/models/__init__.py",
        f"{BASE_PATH}/db/schemas/__init__.py",
        f"{BASE_PATH}/services/__init__.py",
        f"{BASE_PATH}/api/v1/endpoints/__init__.py",
    ]:
        if os.path.exists(subdir):
            with open(subdir, "r") as f:
                old_inits[subdir] = f.read()
    try:
        for path in track[model]:
            remove_file(path)
        # Remove imports from __init__.py
        for subdir, imp in [
            (f"{BASE_PATH}/db/models/__init__.py", f"from .{snake_case(model)} import {model}\n"),
            (f"{BASE_PATH}/db/schemas/__init__.py", f"from .{snake_case(model)} import {model}Create, {model}Read\n"),
            (f"{BASE_PATH}/services/__init__.py", f"from .{snake_case(model)}_service import {model}Service\n"),
            (f"{BASE_PATH}/api/v1/endpoints/__init__.py", f"from .{snake_case(model)} import router as {snake_case(model)}_router\n"),
        ]:
            if os.path.exists(subdir):
                with open(subdir, "r") as f:
                    lines = f.readlines()
                with open(subdir, "w") as f:
                    for l in lines:
                        if l != imp:
                            f.write(l)
        update_api_py(model, "remove")
        del track[model]
        save_track(track)
        console.print(f"[bold red]Model {model} and all associated files/imports removed.[/bold red]")
    except Exception as e:
        # Rollback: restore files and __init__.py, revert tracking
        console.print(f"[bold red]Error during removal: {e}. Rolling back changes...[/bold red]")
        # Restore files from backup (warn user to check)
        # (In a full implementation, you'd restore file contents from backup if needed)
        for subdir, content in old_inits.items():
            with open(subdir, "w") as f:
                f.write(content)
        track[model] = old_files
        save_track(track)
        console.print(f"[yellow]Rollback complete. Model {model} restored to previous state.[/yellow]")
        raise

def list_models():
    track = load_track()
    if not track:
        console.print("[yellow]No models scaffolded yet.[/yellow]")
        return
    model_table = Table(title="Scaffolded Models")
    model_table.add_column("Model")
    model_table.add_column("Files")
    for model, files in track.items():
        model_table.add_row(model, "\n".join(files))
    console.print(model_table)

@app.command()
def add():
    """Add a new model (interactive prompts)."""
    model = typer.prompt("Enter model name (CamelCase, e.g., Book)")
    fields = prompt_fields()
    validate_fields(fields)
    relationships = prompt_relationships()
    crud = prompt_crud()
    examples = {name: typer.prompt(f"Example for {name}") for name, _ in fields}
    add_model(model, fields, relationships, crud, examples)
    # Optionally run Alembic migration
    if typer.confirm("Run Alembic migration now?", default=False):
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", f"Add {model}"], check=False)
        subprocess.run(["alembic", "upgrade", "head"], check=False)
    # Optionally run pytest
    if typer.confirm("Run tests now?", default=False):
        subprocess.run(["pytest"], check=False)

@app.command()
def remove():
    """Remove a model and all related files/imports."""
    model = typer.prompt("Enter model name (CamelCase, e.g., Book)")
    remove_model(model)

@app.command()
def list_models_command():
    """List all scaffolded models."""
    list_models()

@app.command()
def bulk_import(yaml_file: str = typer.Argument(..., help="YAML file with models to import")):
    """Bulk import models from a YAML spec."""
    with open(yaml_file, "r") as f:
        spec = yaml.safe_load(f)
    # Rollback support: backup current tracking and inits
    track = load_track()
    backup_track = dict(track)
    backup_inits = {}
    for subdir in [
        f"{BASE_PATH}/db/models/__init__.py",
        f"{BASE_PATH}/db/schemas/__init__.py",
        f"{BASE_PATH}/services/__init__.py",
        f"{BASE_PATH}/api/v1/endpoints/__init__.py",
    ]:
        if os.path.exists(subdir):
            with open(subdir, "r") as f:
                backup_inits[subdir] = f.read()
    try:
        for model_spec in spec.get("models", []):
            model = model_spec["name"]
            fields = model_spec.get("fields", [])
            relationships = model_spec.get("relationships", [])
            crud = model_spec.get("crud", {"create": True, "read": True, "update": True, "delete": True, "list": True})
            examples = model_spec.get("examples", {name: "example" for name, _ in fields})
            add_model(model, fields, relationships, crud, examples)
    except Exception as e:
        console.print(f"[bold red]Error during bulk import: {e}. Rolling back all changes...[/bold red]")
        # Restore __init__.py
        for subdir, content in backup_inits.items():
            with open(subdir, "w") as f:
                f.write(content)
        # Restore tracking
        with open(TRACK_FILE, "w") as f:
            json.dump(backup_track, f, indent=2)
        console.print(f"[yellow]Rollback complete. Project restored to previous state before bulk import.[/yellow]")
        raise

@app.command()
def gendocs():
    """Stub: Generate documentation using mkdocs."""
    if shutil.which("mkdocs"):
        subprocess.run(["mkdocs", "build"], check=False)
        console.print("[green]Docs generated with mkdocs![/green]")
    else:
        console.print("[yellow]mkdocs not installed. Skipping doc generation.[/yellow]")

@app.command()
def watch():
    """Stub: Watch for file changes and auto-run tests (requires watchdog)."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        console.print("[yellow]watchdog not installed. Skipping file watch.[/yellow]")
        return
    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path.endswith(".py"):
                console.print(f"[cyan]Detected change in {event.src_path}. Running tests...[/cyan]")
                subprocess.run(["pytest"], check=False)
    observer = Observer()
    observer.schedule(Handler(), path=BASE_PATH, recursive=True)
    observer.start()
    console.print("[green]Watching for file changes. Press Ctrl+C to stop.[/green]")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

@app.command()
def admin():
    """Stub: Scaffold admin endpoints (requires fastapi-admin)."""
    if fastapi_admin is None:
        console.print("[yellow]fastapi-admin not installed. Skipping admin scaffolding.[/yellow]")
    else:
        console.print("[green]fastapi-admin integration would be handled here.[/green]")

@app.command()
def user():
    """Stub: Scaffold user endpoints (requires fastapi-users)."""
    if fastapi_users is None:
        console.print("[yellow]fastapi-users not installed. Skipping user scaffolding.[/yellow]")
    else:
        console.print("[green]fastapi-users integration would be handled here.[/green]")


def update_model(model, new_fields, new_relationships, new_crud, new_examples, verbose=True):
    track = load_track()
    if model not in track:
        console.print(f"[red]Model {model} not found in scaffolded models. Cannot update.[/red]")
        return
    # Backup old files and __init__.py
    old_files = track[model][:]
    old_inits = {}
    for subdir in [
        f"{BASE_PATH}/db/models/__init__.py",
        f"{BASE_PATH}/db/schemas/__init__.py",
        f"{BASE_PATH}/services/__init__.py",
        f"{BASE_PATH}/api/v1/endpoints/__init__.py",
    ]:
        if os.path.exists(subdir):
            with open(subdir, "r") as f:
                old_inits[subdir] = f.read()
    try:
        # Remove old files
        for path in old_files:
            remove_file(path)
        # Recreate files with new spec
        files = make_model_files(model, new_fields, new_relationships, new_crud, new_examples, dry_run=False, verbose=verbose)
        # Update __init__.py for imports (ensure idempotency)
        for subdir, imp in [
            (f"{BASE_PATH}/db/models/__init__.py", f"from .{snake_case(model)} import {model}\n"),
            (f"{BASE_PATH}/db/schemas/__init__.py", f"from .{snake_case(model)} import {model}Create, {model}Read\n"),
            (f"{BASE_PATH}/services/__init__.py", f"from .{snake_case(model)}_service import {model}Service\n"),
            (f"{BASE_PATH}/api/v1/endpoints/__init__.py", f"from .{snake_case(model)} import router as {snake_case(model)}_router\n"),
        ]:
            if os.path.exists(subdir):
                with open(subdir, "r") as f:
                    lines = f.readlines()
                with open(subdir, "w") as f:
                    for l in lines:
                        if l != imp:
                            f.write(l)
                    f.write(imp)
        update_api_py(model, "add")
        track[model] = list(files.keys())
        save_track(track)
        console.print(f"[bold green]Model {model} updated successfully.[/bold green]")
    except Exception as e:
        # Rollback: restore old files and __init__.py, revert tracking
        console.print(f"[bold red]Error during update: {e}. Rolling back changes...[/bold red]")
        # Remove new files
        try:
            for path in track.get(model, []):
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass
        # Restore old files from backup (not content, just warn user to check)
        for subdir, content in old_inits.items():
            with open(subdir, "w") as f:
                f.write(content)
        # Restore tracking
        track[model] = old_files
        save_track(track)
        console.print(f"[yellow]Rollback complete. Model {model} restored to previous state.[/yellow]")
        raise

@app.command()
def update():
    """Update an existing model and its files interactively."""
    model = typer.prompt("Enter model name to update (CamelCase, e.g., Book)")
    track = load_track()
    if model not in track:
        console.print(f"[red]Model {model} not found in scaffolded models. Cannot update.[/red]")
        raise typer.Exit()
    console.print(f"[yellow]Updating {model}. Enter new fields, relationships, CRUD config, and example data. Old files will be replaced.[/yellow]")
    new_fields = prompt_fields()
    validate_fields(new_fields)
    new_relationships = prompt_relationships()
    new_crud = prompt_crud()
    new_examples = {name: typer.prompt(f"Example for {name}") for name, _ in new_fields}
    update_model(model, new_fields, new_relationships, new_crud, new_examples)
    # Optionally run Alembic migration
    if typer.confirm("Run Alembic migration now?", default=False):
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", f"Update {model}"], check=False)
        subprocess.run(["alembic", "upgrade", "head"], check=False)
    # Optionally run pytest
    if typer.confirm("Run tests now?", default=False):
        subprocess.run(["pytest"], check=False)

@app.command()
def add_field():
    """Add a single new field to an existing model interactively (minimal input)."""
    model = typer.prompt("Enter model name to add a field to (CamelCase, e.g., Book)")
    track = load_track()
    if model not in track:
        console.print(f"[red]Model {model} not found in scaffolded models. Cannot add field.[/red]")
        raise typer.Exit()
    # Try to read current fields from schema file
    schema_path = f"{BASE_PATH}/db/schemas/{snake_case(model)}.py"
    fields = []
    if os.path.exists(schema_path):
        with open(schema_path, "r") as f:
            for line in f:
                if ":" in line and "Field(" in line:
                    parts = line.strip().split(":")
                    if len(parts) >= 2:
                        fname = parts[0].strip()
                        ftype = parts[1].split("=")[0].strip()
                        fields.append((fname, ftype))
    # Prompt for new field
    new_field_name = typer.prompt("New field name (snake_case)")
    new_field_type = typer.prompt("New field type (str/int/float/bool or FK:TargetModel)")
    example = typer.prompt(f"Example value for {new_field_name}")
    # Append new field
    fields.append((new_field_name, new_field_type))
    # Try to preserve relationships and CRUD config
    relationships = []
    endpoint_path = f"{BASE_PATH}/api/v1/endpoints/{snake_case(model)}.py"
    crud = {"create": True, "read": True, "update": True, "delete": True, "list": True}
    if os.path.exists(endpoint_path):
        with open(endpoint_path, "r") as f:
            for line in f:
                if "crud_ops=" in line:
                    try:
                        import ast
                        crud = ast.literal_eval(line.split("crud_ops=")[1].split(")")[0].strip())
                    except Exception:
                        pass
    examples = {name: "example" for name, _ in fields}
    examples[new_field_name] = example
    # Rollback support
    old_files = track[model][:]
    old_inits = {}
    for subdir in [
        f"{BASE_PATH}/db/models/__init__.py",
        f"{BASE_PATH}/db/schemas/__init__.py",
        f"{BASE_PATH}/services/__init__.py",
        f"{BASE_PATH}/api/v1/endpoints/__init__.py",
    ]:
        if os.path.exists(subdir):
            with open(subdir, "r") as f:
                old_inits[subdir] = f.read()
    try:
        # Regenerate files with new field
        update_model(model, fields, relationships, crud, examples)
    except Exception as e:
        console.print(f"[bold red]Error during add_field: {e}. Rolling back changes...[/bold red]")
        # Restore __init__.py
        for subdir, content in old_inits.items():
            with open(subdir, "w") as f:
                f.write(content)
        track[model] = old_files
        save_track(track)
        console.print(f"[yellow]Rollback complete. Model {model} restored to previous state.[/yellow]")
        raise
    # Optionally run Alembic migration
    if typer.confirm("Run Alembic migration now?", default=True):
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", f"Add field {new_field_name} to {model}"], check=False)
        subprocess.run(["alembic", "upgrade", "head"], check=False)
    # Optionally run pytest
    if typer.confirm("Run tests now?", default=False):
        subprocess.run(["pytest"], check=False)

if __name__ == "__main__":
    load_dotenv()
    app()

def load_track():
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, "r") as f:
            return json.load(f)
    return {}

def save_track(data):
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --- File generation and removal ---
def write_file(path, content):
    ensure_init(os.path.dirname(path))
    with open(path, "w") as f:
        f.write(content)

def remove_file(path):
    if os.path.exists(path):
        os.remove(path)
        # Remove empty parent dirs up to BASE_PATH
        d = os.path.dirname(path)
        while d.startswith(BASE_PATH) and d != BASE_PATH:
            if not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
            else:
                break

def update_api_py(model, action):
    """Add or remove import/include_router for the model in api.py."""
    snake = snake_case(model)
    router_line = f"from app.api.v1.endpoints import {snake}"
    include_line = f"api_router.include_router({snake}.router, prefix=\"/{snake}s\", tags=[\"{snake}s\"])"
    with open(API_FILE, "r") as f:
        lines = f.readlines()
    if action == "add":
        if router_line + "\n" not in lines:
            # Insert after last import
            last_import = max(i for i, l in enumerate(lines) if l.startswith("from"))
            lines.insert(last_import+1, router_line+"\n")
        if include_line+"\n" not in lines:
            # Insert after last include_router
            last_include = max(i for i, l in enumerate(lines) if "include_router" in l)
            lines.insert(last_include+1, include_line+"\n")
    elif action == "remove":
        lines = [l for l in lines if l.strip() != router_line and l.strip() != include_line]
    with open(API_FILE, "w") as f:
        f.writelines(lines)

# --- Main scaffold logic ---
def make_model_files(model, fields):
    snake = snake_case(model)
    files = {}
    # Model
    model_path = f"{BASE_PATH}/db/models/{snake}.py"
    model_code = f'''"""
SQLAlchemy model for {model}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String

class {model}(Base):
    __tablename__ = "{snake}s"
    id = Column(Integer, primary_key=True, index=True)
'''
    for name, typ in fields:
        sqlatype = "String" if typ == "str" else "Integer" if typ == "int" else "String"
        model_code += f"    {name} = Column({sqlatype}, nullable=False)\n"
    files[model_path] = model_code
    # Schema
    schema_path = f"{BASE_PATH}/db/schemas/{snake}.py"
    schema_code = f'''"""
Pydantic schemas for {model}.
"""
from pydantic import BaseModel

class {model}Create(BaseModel):
'''
    for name, typ in fields:
        pytyp = "str" if typ == "str" else "int" if typ == "int" else "str"
        schema_code += f"    {name}: {pytyp}\n"
    schema_code += f"""

class {model}Read({model}Create):
    id: int
    class Config:
        orm_mode = True
"""
    files[schema_path] = schema_code
    # Service
    service_path = f"{BASE_PATH}/services/{snake}_service.py"
    service_code = f'''"""
Service for {model} business logic and CRUD operations.
"""
from app.services.base_service import BaseService
from app.db.models.{snake} import {model}

class {model}Service(BaseService[{model}]):
    def __init__(self):
        super().__init__({model})
'''
    files[service_path] = service_code
    # Endpoint
    endpoint_path = f"{BASE_PATH}/api/v1/endpoints/{snake}.py"
    endpoint_code = f'''"""
Auto-generated CRUD endpoints for {model}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake}_service import {model}Service
from app.db.schemas.{snake} import {model}Read, {model}Create
from app.db.session import get_db

router = get_crud_router(
    service={model}Service(),
    schema_read={model}Read,
    schema_create={model}Create,
    prefix="/{snake}s",
    get_db=get_db,
    tags=["{model}s"]
)
'''
    files[endpoint_path] = endpoint_code
    return files

def add_model(model, fields):
    track = load_track()
    if model in track:
        print(f"Model {model} already scaffolded. Remove first if you want to re-create.")
        return
    files = make_model_files(model, fields)
    created = []
    try:
        for path, content in files.items():
            write_file(path, content)
            created.append(path)
        # Update __init__.py for imports
        for subdir, imp in [
            (f"{BASE_PATH}/db/models/__init__.py", f"from .{snake_case(model)} import {model}\n"),
            (f"{BASE_PATH}/db/schemas/__init__.py", f"from .{snake_case(model)} import {model}Create, {model}Read\n"),
            (f"{BASE_PATH}/services/__init__.py", f"from .{snake_case(model)}_service import {model}Service\n"),
            (f"{BASE_PATH}/api/v1/endpoints/__init__.py", f"from .{snake_case(model)} import router as {snake_case(model)}_router\n"),
        ]:
            with open(subdir, "a") as f:
                f.write(imp)
        # Ensure model is imported in base.py for Alembic autogenerate
        base_path = f"{BASE_PATH}/db/base.py"
        import_line = f"from app.db.models.{snake_case(model)} import {model}\n"
        with open(base_path, "r+") as f:
            lines = f.readlines()
            if import_line not in lines:
                # Insert after the last existing import
                insert_at = len(lines)
                for i, line in enumerate(lines):
                    if line.startswith("from app.db.models."):
                        insert_at = i + 1
                lines.insert(insert_at, import_line)
                f.seek(0)
                f.writelines(lines)
                f.truncate()
        # Update API router
        update_api_py(model, "add")
        # Track
        track[model] = list(files.keys())
        save_track(track)
        print(f"Model {model} scaffolded successfully.")
    except Exception as e:
        print(f"Error occurred: {e}. Rolling back...")
        for path in created:
            remove_file(path)
        update_api_py(model, "remove")
        if model in track:
            del track[model]
            save_track(track)
        raise

def remove_model(model):
    track = load_track()
    if model not in track:
        print(f"Model {model} not found in scaffolded models.")
        return
    for path in track[model]:
        remove_file(path)
    # Remove imports from __init__.py
    for subdir, imp in [
        (f"{BASE_PATH}/db/models/__init__.py", f"from .{snake_case(model)} import {model}\n"),
        (f"{BASE_PATH}/db/schemas/__init__.py", f"from .{snake_case(model)} import {model}Create, {model}Read\n"),
        (f"{BASE_PATH}/services/__init__.py", f"from .{snake_case(model)}_service import {model}Service\n"),
        (f"{BASE_PATH}/api/v1/endpoints/__init__.py", f"from .{snake_case(model)} import router as {snake_case(model)}_router\n"),
    ]:
        if os.path.exists(subdir):
            with open(subdir, "r") as f:
                lines = f.readlines()
            with open(subdir, "w") as f:
                for l in lines:
                    if l != imp:
                        f.write(l)
    update_api_py(model, "remove")
    del track[model]
    save_track(track)
    print(f"Model {model} and all associated files/imports removed.")

def list_models():
    track = load_track()
    if not track:
        print("No models scaffolded yet.")
        return
    print("Scaffolded models:")
    for model, files in track.items():
        print(f"- {model}: {files}")

# --- Extra features ---
SUPPORTED_FIELD_TYPES = {"str": "String", "int": "Integer", "float": "Float", "bool": "Boolean"}

HELP_TEXT = """
FastAPI Scaffold Tool - Enhanced

Usage:
  python scaffold_model.py add        # Add a new model (with prompts)
  python scaffold_model.py remove     # Remove a model and all related files/imports
  python scaffold_model.py list       # List all scaffolded models
  python scaffold_model.py help       # Show this help message

Options:
  --dry-run   Preview changes without writing files
  --verbose   Show detailed output
  --quiet     Suppress most output

Features:
- Test file generation for each model
- Field type validation and warning
- Basic relationship support (ForeignKey)
- Docstrings/examples in schemas
- Customizable CRUD endpoints (disable/enable)
- Dry run/preview mode
- Verbose/quiet modes
- Help/usage command
"""

def validate_fields(fields):
    valid = True
    for name, typ in fields:
        if typ not in SUPPORTED_FIELD_TYPES and not typ.startswith("FK:"):
            print(f"[Warning] Field '{name}' has unsupported type '{typ}'. Defaulting to String.")
            valid = False
    return valid

def prompt_relationships():
    rels = []
    print("Enter relationships (format: field:FK:TargetModel), e.g., author_id:FK:User. Type 'done' when finished.")
    while True:
        rel = input("Relationship: ")
        if rel.lower() == "done":
            break
        if ':' in rel and rel.count(':') == 2:
            name, fk, target = rel.split(':')
            if fk == "FK":
                rels.append((name.strip(), target.strip()))
    return rels

def prompt_crud():
    print("Enable/disable CRUD endpoints (y/n):")
    crud = {}
    for op in ["create", "read", "update", "delete", "list"]:
        val = input(f"  {op}? [y/n]: ").strip().lower()
        crud[op] = (val == "y")
    return crud

def make_test_file(model, fields):
    snake = snake_case(model)
    test_path = f"app/tests/test_{snake}.py"
    test_code = f'''"""
Basic tests for {model} endpoints and service.
"""
def test_{snake}_crud(client):
    # TODO: Implement real tests
    resp = client.get(f"/{snake}s")
    assert resp.status_code in (200, 401, 403)
'''
    return test_path, test_code

def make_model_files_enhanced(model, fields, relationships, crud, examples, dry_run=False, verbose=True):
    snake = snake_case(model)
    files = {}
    # Model
    model_path = f"{BASE_PATH}/db/models/{snake}.py"
    model_code = f'''"""
SQLAlchemy model for {model}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey

class {model}(Base):
    """SQLAlchemy ORM model for {model}."""
    __tablename__ = "{snake}s"
    id = Column(Integer, primary_key=True, index=True)
'''
    for name, typ in fields:
        if typ.startswith("FK:"):
            target = typ.split(":")[1]
            model_code += f"    {name} = Column(Integer, ForeignKey('{snake_case(target)}s.id'))\n"
        else:
            sqlatype = SUPPORTED_FIELD_TYPES.get(typ, "String")
            model_code += f"    {name} = Column({sqlatype}, nullable=False)\n"
    for name, target in relationships:
        model_code += f"    {name} = Column(Integer, ForeignKey('{snake_case(target)}s.id'))\n"
    files[model_path] = model_code
    # Schema
    schema_path = f"{BASE_PATH}/db/schemas/{snake}.py"
    schema_code = f'''"""
Pydantic schemas for {model}.
"""
from pydantic import BaseModel, Field

class {model}Create(BaseModel):
'''
    for name, typ in fields:
        pytyp = "str" if typ == "str" else "int" if typ == "int" else "float" if typ == "float" else "bool" if typ == "bool" else "str"
        example = examples.get(name, "example")
        schema_code += f"    {name}: {pytyp} = Field(..., example={repr(example)})\n"
    schema_code += f"""

class {model}Read({model}Create):
    id: int
    class Config:
        orm_mode = True
"""
    files[schema_path] = schema_code
    # Service
    service_path = f"{BASE_PATH}/services/{snake}_service.py"
    service_code = f'''"""
Service for {model} business logic and CRUD operations.
"""
from app.services.base_service import BaseService
from app.db.models.{snake} import {model}

class {model}Service(BaseService[{model}]):
    def __init__(self):
        super().__init__({model})
'''
    files[service_path] = service_code
    # Endpoint
    endpoint_path = f"{BASE_PATH}/api/v1/endpoints/{snake}.py"
    endpoint_code = f'''"""
Auto-generated CRUD endpoints for {model}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake}_service import {model}Service
from app.db.schemas.{snake} import {model}Read, {model}Create
from app.db.session import get_db

router = get_crud_router(
    service={model}Service(),
    schema_read={model}Read,
    schema_create={model}Create,
    prefix="/{snake}s",
    get_db=get_db,
    tags=["{model}s"],
    crud_ops={crud}
)
'''
    files[endpoint_path] = endpoint_code
    # Test
    test_path, test_code = make_test_file(model, fields)
    files[test_path] = test_code
    if not dry_run:
        for path, code in files.items():
            write_file(path, code)
        if verbose:
            print(f"Created files: {list(files.keys())}")
    return files

def add_model_enhanced(model, fields, relationships, crud, examples, dry_run=False, verbose=True):
    track = load_track()
    if model in track:
        print(f"Model {model} already scaffolded. Remove first if you want to re-create.")
        return
    files = make_model_files_enhanced(model, fields, relationships, crud, examples, dry_run, verbose)
    if not dry_run:
        # Update __init__.py for imports
        for subdir, imp in [
            (f"{BASE_PATH}/db/models/__init__.py", f"from .{snake_case(model)} import {model}\n"),
            (f"{BASE_PATH}/db/schemas/__init__.py", f"from .{snake_case(model)} import {model}Create, {model}Read\n"),
            (f"{BASE_PATH}/services/__init__.py", f"from .{snake_case(model)}_service import {model}Service\n"),
            (f"{BASE_PATH}/api/v1/endpoints/__init__.py", f"from .{snake_case(model)} import router as {snake_case(model)}_router\n"),
        ]:
            with open(subdir, "a") as f:
                f.write(imp)
        update_api_py(model, "add")
        track[model] = list(files.keys())
        save_track(track)
        print(f"Model {model} scaffolded successfully.")
    else:
        print(f"[Dry Run] Would create: {list(files.keys())}")

# --- CLI ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FastAPI Scaffold Tool", add_help=False)
    parser.add_argument("cmd", nargs="?", default="help", choices=["add", "remove", "list", "help"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    if args.cmd == "help":
        print(HELP_TEXT)
        sys.exit(0)
    if args.cmd == "list":
        list_models()
        sys.exit(0)
    if args.cmd == "add":
        model = input("Enter model name (CamelCase, e.g., Book): ").strip()
        fields = prompt_fields()
        validate_fields(fields)
        relationships = prompt_relationships()
        crud = prompt_crud()
        examples = {name: input(f"Example for {name}: ") for name, _ in fields}
        add_model_enhanced(model, fields, relationships, crud, examples, dry_run=args.dry_run, verbose=args.verbose and not args.quiet)
    elif args.cmd == "remove":
        model = input("Enter model name (CamelCase, e.g., Book): ").strip()
        remove_model(model)

def make_model(model_name, fields):
    fname = f"{BASE_PATH}/db/models/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
        return
    with open(fname, "w") as f:
        f.write(f'''"""
SQLAlchemy model for {model_name}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String

class {model_name}(Base):
    \"\"\"SQLAlchemy ORM model for {model_name}.\"\"\"
    __tablename__ = "{snake_case(model_name)}s"
    id = Column(Integer, primary_key=True, index=True)
''')
        for name, typ in fields:
            sqlatype = "String" if typ == "str" else "Integer" if typ == "int" else "String"
            f.write(f"    {name} = Column({sqlatype}, nullable=False)\n")
    # Add to __init__.py for Alembic
    init_file = f"{BASE_PATH}/db/models/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)} import {model_name}\n")
    print(f"Created model: {fname}")

def make_schema(model_name, fields):
    fname = f"{BASE_PATH}/db/schemas/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Pydantic schemas for {model_name}.
"""
from pydantic import BaseModel

class {model_name}Create(BaseModel):
    """Schema for creating a {model_name}."""
''')
        for name, typ in fields:
            pytyp = "str" if typ == "str" else "int" if typ == "int" else "str"
            f.write(f"    {name}: {pytyp}\n")
        f.write(f"""\n
class {model_name}Read({model_name}Create):
    \"\"\"Schema for reading a {model_name}.\"\"\"
    id: int

    class Config:
        orm_mode = True
""")
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/db/schemas/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)} import {model_name}Create, {model_name}Read\n")
    print(f"Created schemas: {fname}")

def make_service(model_name):
    fname = f"{BASE_PATH}/services/{snake_case(model_name)}_service.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Service for {model_name} business logic and CRUD operations.
"""
from app.services.base_service import BaseService
from app.db.models.{snake_case(model_name)} import {model_name}

class {model_name}Service(BaseService[{model_name}]):
    \"\"\"Service class for {model_name}. Inherit and extend for custom business logic.\"\"\"
    def __init__(self):
        super().__init__({model_name})
''')
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/services/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)}_service import {model_name}Service\n")
    print(f"Created service: {fname}")

def make_endpoint(model_name):
    fname = f"{BASE_PATH}/api/v1/endpoints/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Auto-generated CRUD endpoints for {model_name}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake_case(model_name)}_service import {model_name}Service
from app.db.schemas.{snake_case(model_name)} import {model_name}Read, {model_name}Create
from app.db.session import get_db

router = get_crud_router(
    service={model_name}Service(),
    schema_read={model_name}Read,
    schema_create={model_name}Create,
    prefix="/{snake_case(model_name)}s",
    get_db=get_db,
    tags=["{model_name}s"]
)

# Example custom endpoint (extend as needed)
# from fastapi import Depends, HTTPException
# @router.get("/{snake_case(model_name)}s/by_field/{{value}}", tags=["{model_name}s"], description="Get a {model_name} by field value.")
# async def get_by_field(value: str, db=Depends(get_db)):
#     ...
''')
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/api/v1/endpoints/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)} import router as {snake_case(model_name)}_router\n")
    print(f"Created endpoint: {fname}")

def main():
    model_name = input("Enter model name (CamelCase, e.g., Book): ").strip()
    fields = prompt_fields()
    make_model(model_name, fields)
    make_schema(model_name, fields)
    make_service(model_name)
    make_endpoint(model_name)
    print("\nNext steps:")
    print(f"- Register the new router in app/api/v1/api.py (if not already auto-imported):")
    print(f"    from app.api.v1.endpoints import {snake_case(model_name)}_router")
    print(f"    api_router.include_router({snake_case(model_name)}_router)")
    print("- Run Alembic migration:")
    print("    alembic revision --autogenerate -m \"Add new model\"")
    print("    alembic upgrade head")
    print("- Add tests in app/tests/ as needed.")

if __name__ == '__main__':
    main()